// Stage-1 dynamic workflow: build a verified, lane-tagged job-application
// evidence library from a candidate's project portfolio.
//
// This is the Claude Code REFERENCE IMPLEMENTATION; the phased pipeline is also
// described agent-agnostically in docs/architecture.md, so other coding agents
// can implement it with their own subagent/loop primitives.
//
// EXECUTION MODEL: a Claude Code Workflow-tool script (not node/make). Run it
// from a Claude Code session, passing inputs via `args`:
//
//   Workflow({ scriptPath: '.claude/workflows/cc-workflow-evidence-library.js', args: {
//     workspaceRoot: '/path/to/workspace', // dir holding the candidate's repos
//     account:       'the candidate',      // owner/account name, for tone framing
//     profileRepo:   '',                   // optional: path to a profile repo (README = self-presentation)
//     leanAwayFrom:  '',                   // optional: a domain to de-emphasize
//     maxProjects:   22,
//     lanes:         []                    // optional: override the default lanes (see below)
//   }})
// (now under .claude/workflows/, it can also be invoked by name: Workflow({ name: 'evidence-library' }).)
// ⚠️ TOKEN USAGE: deep-mines the whole portfolio (one subagent per project + adversarial verify) — the heaviest one-off pass. Run once per profile; resume via { resumeFromRunId } to skip re-mining.
//
// Persist the returned object as results/evidence-library.json (write the Workflow tool's return
// value to that path) before running Stage 2 — mirrors the "persist the returned X" step in the
// relevance/tailor headers; there is no `ajoa-kit` CLI for this Stage-1 save.
//
// Resumable / cached by run id: edit the assemble phase and re-invoke with
// { scriptPath, resumeFromRunId } to re-assemble without re-mining.
//
// Hooks: agent(), parallel(), pipeline(), phase(), log(). agent(prompt,{schema})
// returns the schema-validated object.

export const meta = {
  name: 'evidence-library',
  description: 'Build a verified, reusable, lane-tagged job-application evidence library from a candidate project portfolio, framed in the account tone',
  phases: [
    { title: 'Tone & Inventory', detail: 'extract account voice + list projects' },
    { title: 'Mine & verify', detail: 'deep-mine accomplishment bullets, adversarially verify each' },
    { title: 'Assemble', detail: 'assemble the evidence library in the account tone' },
  ],
}

// --- config (from args, with generic defaults) ---
const cfg = typeof args === 'string' ? JSON.parse(args) : (args && typeof args === 'object' ? args : {})
const WORKSPACE = cfg.workspaceRoot || '/path/to/workspace'
const ACCOUNT = cfg.account || 'the candidate'
const PROFILE_REPO = cfg.profileRepo || ''
const LEAN_AWAY = cfg.leanAwayFrom || ''
const MAX_PROJECTS = cfg.maxProjects || 22
const LANES = (cfg.lanes && cfg.lanes.length) ? cfg.lanes : [
  { key: 'cxo', label: '(fractional) CxO — fractional CTO / Chief AI Officer / technical advisor', focus: 'early-stage leadership; reframe breadth as a product/systems-level asset', gapHint: 'no evidence of leading people / teams' },
  { key: 'founding', label: 'founding engineer / first technical hire', focus: '0->1 startup; breadth, autonomy, ship end-to-end solo, set up practice from zero', gapHint: 'scaling / team-leadership experience' },
  { key: 'engineering', label: 'software engineer (senior IC)', focus: 'backend / platform / systems; production-grade engineering (typing, testing, systems design)', gapHint: 'solo / no-team, no production-at-scale ops' },
  { key: 'cloud', label: 'cloud / DevOps / platform engineer', focus: 'CI/CD, supply-chain security, reusable CI actions, containerization', gapHint: 'thin on cloud-provider infra at scale, IaC, production ops / observability' },
  { key: 'architect', label: 'software / systems architect', focus: 'ADR/MADR culture, system design, multi-repo governance, doc hierarchies, contract-driven design', gapHint: 'architecture is solo / greenfield, not enterprise-scale or cross-team' },
]

// --- schemas ---
const TONE = {
  type: 'object',
  properties: {
    overallTone: { type: 'string' },
    foregroundedThemes: { type: 'array', items: { type: 'string' } },
    voiceNotes: { type: 'string' },
    leanAwayFrom: { type: 'string' },
  },
  required: ['overallTone', 'foregroundedThemes', 'voiceNotes', 'leanAwayFrom'],
}

const INVENTORY = {
  type: 'object',
  properties: {
    projects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          path: { type: 'string' },
          oneLiner: { type: 'string' },
          primaryTech: { type: 'string' },
        },
        required: ['name', 'path', 'oneLiner', 'primaryTech'],
      },
    },
  },
  required: ['projects'],
}

const BULLETS = {
  type: 'object',
  properties: {
    project: { type: 'string' },
    bullets: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          skillTags: { type: 'array', items: { type: 'string' } },
          metric: { type: 'string' },
          artifact: { type: 'string' },
        },
        required: ['claim', 'skillTags', 'metric', 'artifact'],
      },
    },
  },
  required: ['project', 'bullets'],
}

const VERIFIED = {
  type: 'object',
  properties: {
    project: { type: 'string' },
    bullets: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          skillTags: { type: 'array', items: { type: 'string' } },
          metric: { type: 'string' },
          artifact: { type: 'string' },
          verdict: { type: 'string', enum: ['keep', 'downgrade', 'drop'] },
          note: { type: 'string' },
        },
        required: ['claim', 'skillTags', 'metric', 'artifact', 'verdict', 'note'],
      },
    },
  },
  required: ['project', 'bullets'],
}

// lane-angle fields derive from the configured lanes (DRY: add a lane = add a config entry)
const laneAngleProps = {}
const laneAngleRequired = []
for (const ln of LANES) {
  laneAngleProps[ln.key + 'Angle'] = { type: 'string' }
  laneAngleRequired.push(ln.key + 'Angle')
}

const LIB = {
  type: 'object',
  properties: {
    headline: { type: 'string' },
    positioningSummary: { type: 'string' },
    skillClusters: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          cluster: { type: 'string' },
          bullets: { type: 'array', items: { type: 'string' } },
        },
        required: ['cluster', 'bullets'],
      },
    },
    masterCvBullets: { type: 'array', items: { type: 'string' } },
    perProject: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          project: { type: 'string' },
          bullets: { type: 'array', items: { type: 'string' } },
        },
        required: ['project', 'bullets'],
      },
    },
    ...laneAngleProps,
    gapNarrative: { type: 'string' },
    toneApplied: { type: 'string' },
  },
  required: ['headline', 'positioningSummary', 'skillClusters', 'masterCvBullets', 'perProject', ...laneAngleRequired, 'gapNarrative', 'toneApplied'],
}

phase('Tone & Inventory')
const both = await parallel([
  () => agent(
    `Characterize the OVERALL tone of ${ACCOUNT}'s project portfolio for a job-application framing. Read-only.
     ${PROFILE_REPO ? `Read the profile repo at ${PROFILE_REPO} (its README is the account's self-presentation). ` : ''}Skim the names + README first-lines of the project repos under ${WORKSPACE}/ to find the account's through-lines.
     ${LEAN_AWAY ? `Do NOT over-index on: ${LEAN_AWAY} (treat it as one domain among several). ` : ''}Return: overallTone (what the account is fundamentally about); foregroundedThemes (the defining through-lines); voiceNotes (style / how it presents itself); leanAwayFrom (what to de-emphasize).`,
    { schema: TONE, agentType: 'Explore', phase: 'Tone & Inventory', label: 'tone' }
  ),
  () => agent(
    `Inventory the candidate's project repos for an evidence library. Read-only (Glob/Read).
     Scan ${WORKSPACE}/. A project is a code repo (README.md / pyproject.toml / package.json / its own .git). EXCLUDE hidden/system dirs, node_modules, .venv, .git internals, and config dirs. For each: name, absolute path, one-line purpose, primary tech. Cap at the ${MAX_PROJECTS} most substantial.`,
    { schema: INVENTORY, agentType: 'Explore', phase: 'Tone & Inventory', label: 'inventory' }
  ),
])
const tone = both[0]
const projects = (both[1] && both[1].projects ? both[1].projects : []).slice(0, MAX_PROJECTS)
log(`Tone captured; ${projects.length} projects to mine`)

phase('Mine & verify')
const verified = (await pipeline(
  projects,
  (p) => agent(
    `Deep-mine project "${p.name}" at ${p.path} for a job-application evidence library. Read README, structure, key source, tests, CI, docs/ADRs. Produce 5-12 concrete accomplishment bullets. Each: claim (what was built/achieved, STAR-ish and specific); skillTags (retrievable skills — include leadership/architecture/strategy tags where the work shows it, e.g. "system design", "governance", "ADR culture", "competitive analysis", "product thinking"); metric (a real number/scale from the repo, or "" if none); artifact (file path / doc / feature that proves it). FACTUAL only — only what the repo demonstrates.`,
    { schema: BULLETS, agentType: 'Explore', phase: 'Mine & verify', label: `mine:${p.name}` }
  ),
  (mined, p) => agent(
    `Adversarially verify these portfolio bullets for "${p.name}" as a skeptical hiring manager / interviewer. For each, set verdict: keep (defensible, specific, would survive scrutiny), downgrade (real but overstated — note how to soften), or drop (inflated, vague, or unverifiable). Be strict: a CV must not overclaim. Return the same bullets with verdict + note. Bullets: ${JSON.stringify(mined && mined.bullets ? mined.bullets : [])}`,
    { schema: VERIFIED, phase: 'Mine & verify', label: `verify:${p.name}` }
  ),
)).filter(Boolean)
log(`Verified ${verified.length} project bullet-sets`)

phase('Assemble')
const laneEnum = LANES.map((ln, i) => `(${String.fromCharCode(97 + i)}) ${ln.label} — ${ln.focus}`).join('; ')
const laneClusters = LANES.map((ln) => `"${ln.label}"`).join(', ')
const laneReturns = LANES.map((ln) => `- ${ln.key}Angle: a focused paragraph positioning for ${ln.label}; cite specific evidence; honestly note what's missing (e.g. ${ln.gapHint}).`).join('\n')

const lib = await agent(
  `You are assembling a reusable job-application EVIDENCE LIBRARY (a master "brag document") from verified portfolio bullets. Frame everything in the candidate's account tone.

ACCOUNT TONE (apply this voice + weighting):
${JSON.stringify(tone)}

VERIFIED BULLETS (use only keep + softened-downgrade; discard drop):
${JSON.stringify(verified)}

The library must support these target lanes: ${laneEnum}. For senior / leadership lanes, reframe the portfolio's BREADTH as an asset (architectural range applying one pattern across domains, not "jack of all trades"). Be HONEST per lane about what is missing.

Return:
- headline: a one-line positioning in the account's voice.
- positioningSummary: 3-4 sentences, lane-agnostic but weighted to the account's real center of gravity.
- skillClusters: group the strongest evidence by skill cluster so per-offer tailoring can retrieve by requirement; include a cluster per target lane (${laneClusters}) plus general technical clusters. Each cluster = name + 3-8 concrete, quantified bullets.
- masterCvBullets: the ~15 single strongest bullets for a default CV.
- perProject: per project, its keep-worthy bullets (1-line each).
${laneReturns}
- gapNarrative: one honest paragraph framing the candidate's context (e.g. solo / open-source / no-formal-employment if applicable), reusable in cover letters.
- toneApplied: one sentence on how you applied the account tone and what you de-emphasized.

Keep bullets quantified, specific, and defensible (these survived adversarial verification). No overclaiming.`,
  { schema: LIB, phase: 'Assemble', label: 'assemble' }
)

return lib
