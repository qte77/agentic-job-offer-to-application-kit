// Stage-2 relevance pass: screen ingested job descriptions (JDs) against the candidate's
// evidence library + the target lanes, and shortlist with per-lane fit scores.
//
// EXECUTION MODEL: a Claude Code Workflow-tool script (not node/make). Ingest + chunk first
// (see CONTRIBUTING.md §Commands), read the batch count from
// results/batches/manifest.json, then run:
//
//   Workflow({ scriptPath: '.claude/workflows/cc-workflow-relevance.js', args: {
//     rootDir:     '.',     // repo root holding results/batches/ + results/evidence-library.json
//     batchCount:  N,       // REQUIRED — results/batches/manifest.json .batch_count
//     limitBatches: K,      // optional — sample the first K batches (dry run)
//     // libraryPath / library — optional overrides; by default each agent reads
//     //   results/evidence-library.json (the Stage-1 output) for the candidate brief
//   }})
// (now under .claude/workflows/, it can also be invoked by name: Workflow({ name: 'relevance' }).)
// ⚠️ TOKEN USAGE: fans out ONE subagent per batch — cost scales with batchCount (e.g. 106 batches ≈ 106 LLM calls; measured ≈100k tokens per 40-JD batch, 2026-07). Use limitBatches:K for a cheap dry run before a full pass.
// ⚠️ RESUME: Workflow resumeFromRunId replays completed agents from cache SAME-SESSION only — and a
// re-run of `ingest --merge` / `chunk --new` recomputes the delta, so the batch files a paused run
// references may silently change; after any re-chunk, start a fresh run instead of resuming.
//
// Persist the returned shortlist with `ajoa-kit persist` — see CONTRIBUTING.md §Commands.
//
// Hooks: agent(), parallel(), phase(), log(). agent(prompt,{schema}) returns the
// schema-validated object. The Workflow script has no filesystem access, but its agents do
// (they Read the batch files and the evidence library themselves).

export const meta = {
  name: 'relevance',
  description:
    'LLM relevance pass: screen ingested JDs against the candidate evidence library + the target lanes, shortlist with per-lane fit scores. Replaces a crude keyword filter that over-matched.',
  phases: [
    { title: 'Screen', detail: 'one agent per batch reads ~40 JDs and judges lane fit, dropping non-fits' },
  ],
}

// --- config (override via args) -------------------------------------------------------
const cfg = typeof args === 'string' ? JSON.parse(args) : (args && typeof args === 'object' ? args : {})
const rootDir = cfg.rootDir || '.'
const dir = cfg.batchDir || `${rootDir}/results/batches`
const batchCount = cfg.batchCount // REQUIRED: read results/batches/manifest.json before invoking
const count = cfg.limitBatches ? Math.min(cfg.limitBatches, batchCount) : batchCount

// Candidate brief: by default each gate agent READS the Stage-1 evidence library itself.
// Pass `library` (parsed evidence-library.json or a compact brief) to inline it instead.
const LIBRARY_PATH = cfg.libraryPath || `${rootDir}/results/evidence-library.json`
const LIBRARY_INLINE = cfg.library || null

// Candidate location policy — ADVISORY: it annotates deal_breaker, and never drops or rescores a
// JD. CANONICAL definition lives in config/location.json (untracked: it describes a person, so the
// no-PII rule keeps it out of git); emit it with `ajoa-kit location --json` and pass as
// args.location. Omitted or without authorizedIn it is inert and the screen ignores location
// exactly as before.
const LOCATION = cfg.location || null
const LOCATION_ACTIVE = !!(LOCATION && LOCATION.authorizedIn && LOCATION.authorizedIn.length)

// Mirrors LOCATION exactly (arc-010 item 8): unconfigured or longestTenureYears <= 0, it is inert
// and the screen ignores tenure exactly as before.
const TENURE = cfg.tenure || null
const TENURE_ACTIVE = !!(TENURE && TENURE.longestTenureYears > 0)

// Honor cfg.lanes (the runtime SSOT) by deriving the keys from it — so overriding lanes in one place
// can't desync the two workflows. CANONICAL lane defs live in config/lanes.json (#195); emit them
// with `ajoa-kit lanes --json` and pass as args.lanes. The hardcoded list below is only the no-config
// fallback (keep in sync with config/lanes.json — see docs/architecture.md §Position lanes).
const LANES = (cfg.lanes && cfg.lanes.length)
  ? cfg.lanes.map((l) => l.key)
  : ['cxo', 'founding', 'engineering', 'ml', 'fde', 'cloud', 'architect']

function pad(n) {
  return String(n).padStart(3, '0')
}

const RESULT = {
  type: 'object',
  properties: {
    relevant: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          company: { type: 'string' },
          best_lane: { type: 'string', enum: LANES },
          score: { type: 'integer' },
          verdict: { type: 'string', enum: ['shortlist', 'maybe'] },
          rationale: { type: 'string' },
          url: { type: 'string' },
          deadline: { type: 'string' },
          deal_breaker: { type: 'string' },
        },
        required: ['id', 'best_lane', 'score', 'verdict', 'rationale'],
      },
    },
    dropped_count: { type: 'integer' },
    dropped_reason_sample: { type: 'string' },
    // How many KEPT JDs carry a location/authorization constraint the candidate does not meet.
    // Advisory: these stay in `relevant` at their earned score — this is a "look at these" tally,
    // never a count of exclusions.
    location_flagged_count: { type: 'integer' },
    // Same shape, for a JD's stated tenure requirement the candidate's longest single-employer
    // tenure does not meet. Advisory: never a count of exclusions.
    tenure_flagged_count: { type: 'integer' },
  },
  required: ['relevant', 'dropped_count'],
}

function gatePrompt(path) {
  const brief = LIBRARY_INLINE
    ? `CANDIDATE BRIEF (provided inline):\n${JSON.stringify(LIBRARY_INLINE)}`
    : `CANDIDATE: read the evidence library at ${LIBRARY_PATH} with the Read tool — use its headline, positioningSummary, per-lane *Angle paragraphs, skillClusters, and gapNarrative as the candidate's genuine OFFERS and honest MISSING per lane.`
  // Inert unless config/location.json declares authorizedIn — see LOCATION_ACTIVE above.
  const location = LOCATION_ACTIVE
    ? `
LOCATION AND WORK AUTHORIZATION — ADVISORY ONLY. Surface it, never act on it:
- Based in: ${LOCATION.basedIn || '(unstated)'}
- Authorized to work in (no sponsorship needed): ${LOCATION.authorizedIn.join(', ')}
- Remote roles outside those regions acceptable: ${LOCATION.remoteOk ? 'yes' : 'no'}
- Would relocate to: ${(LOCATION.relocateTo && LOCATION.relocateTo.length) ? LOCATION.relocateTo.join(', ') : '(nowhere)'}
${LOCATION.notes ? `- Notes: ${LOCATION.notes}` : ''}

This NEVER drops a JD and NEVER changes a score. Score purely on requirement overlap as you would
without this section; the human weighs location themselves, because sponsorship, remote exceptions
and relocation are all negotiable in ways a screen cannot judge.

What it DOES change: when a JD states a location or authorization requirement the candidate does
not currently satisfy, put that constraint verbatim in deal_breaker (e.g. "US citizen/visa only",
"must reside in Argentina", "on-site San Francisco") and name it in the rationale. Count those JDs
in location_flagged_count.

When the JD states no location or authorization requirement, leave deal_breaker for other concerns
and do not mention location — never infer a constraint from the company's headquarters alone.
`
    : ''
  // Inert unless config/tenure.json declares a longestTenureYears > 0 — see TENURE_ACTIVE above.
  const tenure = TENURE_ACTIVE
    ? `
EMPLOYMENT TENURE — ADVISORY ONLY. Surface it, never act on it:
- Candidate's longest continuous tenure at a single employer: ${TENURE.longestTenureYears} years
${TENURE.notes ? `- Notes: ${TENURE.notes}` : ''}

This NEVER drops a JD and NEVER changes a score. Score purely on requirement overlap as you would
without this section; the human weighs a short tenure themselves, because an acquisition, a layoff
or a fixed-term contract are all context a screen cannot judge.

What it DOES change: when a JD states a minimum tenure or "linear career progression at one
company" requirement the candidate's longest tenure does not meet, put that constraint verbatim in
deal_breaker (e.g. "requires 3+ years in a single role") and name it in the rationale. Count those
JDs in tenure_flagged_count.

When the JD states no tenure requirement, leave deal_breaker for other concerns and do not mention
tenure.
`
    : ''
  return `You are screening job descriptions for ONE candidate against the target lanes (${LANES.join(', ')}). Read the JSON file at ${path} with the Read tool — it is an array of ~40 job descriptions, each {id, title, company, location, url, description, ...}.

${brief}
${location}
${tenure}
Judge on REAL requirement overlap, NOT keyword presence; be strict and honest about gaps.

DROP (do not return) any JD that: is a non-engineering function (sales, marketing, recruiting, legal, finance, support, people/HR, pure visual design); is junior/intern; hard-requires years of people-management or large-team leadership; hard-requires deep cloud-infra-at-scale (AWS/GCP/Azure/Kubernetes/Terraform) or production-at-scale ops as a must-have; or has no genuine overlap with any lane.

For each KEPT JD return: id, title, company, url, best_lane (single best fit), score 0-5 (5 = strong fit, 3 = plausible stretch, <3 = drop), verdict ("shortlist" for score>=4, "maybe" for 3), and a one-line rationale that names, in prose, the fit across skill, experience, culture/location, career progression, and motivation AND the main gap. Also set deadline to the JD's stated application deadline verbatim if one is given (else ""), and deal_breaker to one short phrase for a hard concern the human must weigh — e.g. on-site-only location, security clearance, mandated stack (else ""). Only return JDs scoring >=3. Also return dropped_count (how many you dropped) and dropped_reason_sample (one short phrase of why the bulk were dropped)${LOCATION_ACTIVE ? ', plus location_flagged_count (how many KEPT JDs you flagged with a location/authorization constraint — report 0 if none; these are never dropped)' : ''}${TENURE_ACTIVE ? ', plus tenure_flagged_count (how many KEPT JDs you flagged with a tenure constraint — report 0 if none; these are never dropped)' : ''}.`
}

phase('Screen')
if (!batchCount) throw new Error('args.batchCount required (read results/batches/manifest.json .batch_count)')
log(`Screening ${count} of ${batchCount} batches from ${dir}`)

const batches = Array.from({ length: count }, (_, i) => i)
const results = (
  await parallel(
    batches.map((i) => () =>
      agent(gatePrompt(`${dir}/batch-${pad(i)}.json`), {
        schema: RESULT,
        phase: 'Screen',
        label: `batch-${pad(i)}`,
      })
    )
  )
).filter(Boolean)

const relevant = results.flatMap((r) => r.relevant || [])
const dropped = results.reduce((a, r) => a + (r.dropped_count || 0), 0)
relevant.sort((a, b) => b.score - a.score)
const byLane = {}
for (const j of relevant) byLane[j.best_lane] = (byLane[j.best_lane] || 0) + 1

log(`Kept ${relevant.length}, dropped ${dropped} across ${results.length} batches`)
return { kept: relevant.length, dropped, byLane, batchesProcessed: results.length, relevant }
