// Stage-3 tailor pass: turn ONE shortlisted job offer into a per-offer application pack
// (match -> tailored CV + cover letter -> gap report) grounded in the evidence library.
//
// EXECUTION MODEL: a Claude Code Workflow-tool script (not node/make). Run Stage-1 + Stage-2
// first (evidence-library, ingest, chunk, relevance, then persist — see CONTRIBUTING.md §Commands —
// so results/<lane>/shortlist.json exists), pick one offer id from a shortlist, then run:
//
//   Workflow({ scriptPath: '.claude/workflows/cc-workflow-tailor-offer.js', args: {
//     rootDir: '.',              // repo root holding results/ (override for an alt workspace)
//     lane:    'engineering',    // REQUIRED — which results/<lane>/shortlist.json to read
//     offerId: 'ashby:acme:101', // REQUIRED — the shortlist entry id to tailor
//     style:   { cv, coverLetter }, // optional — writing-style directives (#16); generate with
//                                // `ajoa-kit style --json` (reads config/style.json). Omit = neutral.
//     fields:  '<markdown>',      // optional — application-field checklist for the prefill pack (#50);
//                                // generate with `ajoa-kit prefill-fields ...`. Omit = generic fields.
//     critique: true,            // optional (#272) — run a draft→critique→revise loop over the CV +
//                                // cover letter before prefill. Default off. Trims low-relevance /
//                                // duplicated / unsupported / keyword-stuffed lines; never invents
//                                // experience, never hides an honest gap. Costs extra LLM calls.
//     critiqueRounds: 1,         // optional — how many critique+revise passes (default 1). Ignored
//                                // unless critique is true.
//   }})
// (now under .claude/workflows/, it can also be invoked by name: Workflow({ name: 'tailor-offer' }).)
// ⚠️ TOKEN USAGE: LLM subagents (Match → Tailor → [Critique] → Prefill) per offer — measured ≈300–600k tokens per offer with critique (~420k avg, 2026-07); tailor only offers you actually intend to pursue.
//
// Persist the returned pack with `ajoa-kit persist-offer` — see CONTRIBUTING.md §Commands
// (writes results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md — human reviews + submits).
//
// SCOPE: pre-fill + human submit only, NO auto-apply (verified safe in research.md §Delivery, #8).
// The prefill pack is assembled for a human to review and submit. The CV is generated ATS-clean by
// construction (the Tailor prompt enforces ats-check's parse-safety rules, #75); `persist_offer` then
// auto-runs the deterministic `ats-check` (#9) as a backstop, writing `cv-ats-check.md` if it still
// flags anything (non-blocking — `ajoa-kit ats-check <cv.md>` can also be run manually).
//
// Hooks: agent(), parallel(), phase(), log(). agent(prompt,{schema}) returns the
// schema-validated object. The script has no filesystem access, but its agents do (they Read
// the shortlist, the JD corpus, and the evidence library themselves).

export const meta = {
  name: 'tailor-offer',
  description:
    'LLM tailor pass: turn one shortlisted offer into a per-offer application pack (match, tailored CV, cover letter, gap report, prefill pack) grounded in the evidence library. Pre-fill + human submit, no auto-apply.',
  phases: [
    { title: 'Match', detail: 'assess real requirement overlap of the offer vs the evidence library' },
    { title: 'Tailor', detail: 'draft tailored CV, cover letter, and honest gap report from the match' },
    { title: 'Critique', detail: 'optional (args.critique): critique the drafts vs the evidence and revise flagged lines' },
    { title: 'Prefill', detail: 'assemble a human-review prefill pack (no auto-submit) from the CV + fields' },
  ],
}

// --- config (override via args) -------------------------------------------------------
const cfg = typeof args === 'string' ? JSON.parse(args) : (args && typeof args === 'object' ? args : {})
const rootDir = cfg.rootDir || '.'
const lane = cfg.lane
const offerId = cfg.offerId
// Optional writing-style directives, keyed { cv, coverLetter } (from `ajoa-kit style --json`, #16).
const STYLE = cfg.style && typeof cfg.style === 'object' ? cfg.style : {}
// Optional application-field checklist for the prefill pack (from `ajoa-kit prefill-fields`, #50).
const FIELDS = typeof cfg.fields === 'string' ? cfg.fields : ''
// Optional draft→critique→revise loop over the CV + cover letter before prefill (#272). Off by
// default; critiqueRounds is how many critique+revise passes to run (>=1) when it is on.
const CRITIQUE = cfg.critique === true
const CRITIQUE_ROUNDS =
  Number.isInteger(cfg.critiqueRounds) && cfg.critiqueRounds > 0 ? cfg.critiqueRounds : 1

if (!lane) throw new Error('args.lane required (which results/<lane>/shortlist.json to read)')
if (!offerId) throw new Error('args.offerId required (the shortlist entry id to tailor)')

const SHORTLIST_PATH = `${rootDir}/results/${lane}/shortlist.json`
const JOBS_PATH = `${rootDir}/results/jobs-raw.json`
const LIBRARY_PATH = `${rootDir}/results/evidence-library.json`

// Where every agent finds its inputs (each reads with the Read tool; the script passes paths).
const SOURCES = `INPUTS (read each with the Read tool):
- OFFER: in ${SHORTLIST_PATH}, the entry whose id === "${offerId}" (best_lane, score, rationale).
- FULL JD: in ${JOBS_PATH}, the record whose id === "${offerId}" (title, company, url, description).
- CANDIDATE: ${LIBRARY_PATH} — use headline, positioningSummary, the ${lane}Angle paragraph,
  skillClusters, masterCvBullets, perProject, and gapNarrative as the candidate's genuine
  OFFERS and honest MISSING. Tailor only to evidence that exists; never invent experience.`

const strField = (name, desc) => ({
  type: 'object',
  properties: { [name]: { type: 'string', description: desc } },
  required: [name],
})

// Match schema: the prose assessment PLUS a structured must_haves array (one object per JD
// must-have). strField() only builds single-string schemas, so this is hand-written. must_haves
// is OPTIONAL (not in `required`) so a refusal or older run still validates on `match` alone.
const matchSchema = {
  type: 'object',
  properties: {
    match: { type: 'string', description: 'markdown match assessment' },
    must_haves: {
      type: 'array',
      description: "the JD's must-have requirements and whether the candidate covers each",
      items: {
        type: 'object',
        properties: {
          requirement: { type: 'string', description: 'one must-have requirement from the JD' },
          covered: { type: 'boolean', description: 'true if the candidate genuinely covers it' },
          evidence: {
            type: ['string', 'null'],
            description: 'short citation from the evidence library / CV, or null if a gap',
          },
          resources: {
            type: 'array',
            items: { type: 'string' },
            description:
              'for an UNCOVERED must-have only: 1-2 generic, non-fabricated upskilling pointers (a topic, course, or doc area) the candidate could learn to close the gap; omit or [] when covered (#274)',
          },
          mitigation: {
            type: ['string', 'null'],
            description:
              "for an UNCOVERED must-have only: an honest reframe grounded in the evidence library's gapNarrative — quote or closely paraphrase it, never state a fact gapNarrative does not; null when covered or when gapNarrative offers nothing relevant to this specific gap. PRIVATE — lands in gap_report, never in cv/cover_letter/match.",
          },
          suggestion: {
            type: ['string', 'null'],
            description:
              'for an UNCOVERED must-have only: the single smallest concrete real action that would start closing this specific gap; null when covered. PRIVATE — lands in gap_report, never in cv/cover_letter/match.',
          },
        },
        required: ['requirement', 'covered'],
      },
    },
  },
  required: ['match'],
}

// Writing-style directive for an artifact (blank unless `style` was passed). #16.
const styleLine = (k) =>
  STYLE[k] ? `\n\nSTYLE — write in the candidate's configured voice:\n${STYLE[k]}` : ''

// Voice guidance for the three OUTWARD artifacts (match/cv/cover_letter, arc-011 Slice A).
// A value proposition and a synergy framing; never a weakness. Where gapNarrative surfaces
// relevant context, it is reframed as a deliberate choice that built real strength, not an
// apology — the honest gap itself stays out of these three and lives only in gap_report.
const VOICE = `VOICE: name the candidate's core value proposition plainly, early. Frame fit as
synergy — how what the candidate has already built compounds with what this role needs — not a
checklist match. If gapNarrative is relevant context here, frame it as a deliberate choice that
built real strength (e.g. "working solo forced X, which is why Y ships fast and clean"), never as
an apology or a listed weakness. This is an OUTWARD document: state only what is true and
evidenced, and never list a weakness, gap, or missing skill directly.`

// CV/cover_letter both receive the match assessment as context, and that assessment legitimately
// discusses gaps (it is its own document with its own job). Without an explicit instruction not
// to, a model carries that gap language straight through into the outward doc it's asked to write
// — observed directly: a first version of this prompt produced CV/cover text that opened a
// sentence with "Honest gap:" and "I have no experience with...", copied near-verbatim from the
// match assessment's own "Bottom line". This is the fix, used only where that risk exists.
const NO_GAP_ECHO = `The match assessment above may itself discuss gaps — that is its job, not
yours. Do NOT carry that language into what you write here, not even paraphrased. If you notice
yourself writing a sentence like "the honest gap is...", "I have no experience with...", "does not
cover...", or "no evidence of..." — delete it and say only what the candidate IS and DOES instead.`

phase('Match')
log(`Tailoring ${offerId} (lane: ${lane}) from ${SHORTLIST_PATH}`)

const match = await agent(
  `${SOURCES}

${VOICE}

Assess this ONE offer against the candidate. Write a concise markdown "match assessment": the
JD's real must-haves and nice-to-haves, which the candidate genuinely covers (cite evidence),
and which they do not. Be strict and honest — no overstatement. Return the prose as "match".

Also return "must_haves": an array with one object per JD must-have requirement. For EVERY entry
return "requirement" (verbatim or tightly paraphrased) and "covered" (true/false — NEVER mark a gap
"covered" to be kind, and NEVER invent evidence that does not exist) and "evidence" (a short
citation from the evidence library / CV, or null if it is a gap).

For every entry where covered is false, you MUST ALSO fill these three fields — do not leave them
out or return them empty:
- "resources": 1-2 concrete-but-generic learning pointers (a topic, course, or documentation area
  — never a fabricated URL, never a claim the candidate already has it).
- "mitigation": an honest reframe of this specific gap, grounded in the candidate's own
  gapNarrative — quote or closely paraphrase gapNarrative, never state a fact it does not. Use null
  ONLY if gapNarrative truly offers nothing relevant to this particular gap.
- "suggestion": the single smallest concrete action that would start closing this specific gap.

When covered is true, omit resources/mitigation/suggestion or leave them empty/null — they apply
to gaps only. mitigation and suggestion are PRIVATE: they inform gap_report only and must never
appear in match, cv, or cover_letter.`,
  { schema: matchSchema, phase: 'Match', label: 'match' },
)

phase('Tailor')
const [cv, cover, gap] = await parallel([
  // The CV prompt enforces ats_check.parse_safety_warnings' five categories up front, so the CV is
  // ATS-clean by construction; persist_offer's cv-ats-check.md stays the deterministic backstop.
  () =>
    agent(
      `${SOURCES}

MATCH ASSESSMENT (already produced):
${match.match}

${VOICE}

${NO_GAP_ECHO}

Draft a tailored, ATS-safe CV in markdown for THIS offer. PARSE-SAFETY (mirrors the deterministic
ats-check so the CV passes by construction): single-column with NO tables; NO images/graphics; NO
raw HTML tags and NO HTML comments (no hidden text / keyword-stuffing — dishonest and detectable);
and use standard, recognizable section headings (Summary, Experience, Education, Skills, Projects).
Reorder and select from masterCvBullets/perProject to lead with what this JD weighs most. Use only
evidenced bullets.${styleLine('cv')} Return it as "cv".`,
      { schema: strField('cv', 'markdown tailored CV'), phase: 'Tailor', label: 'cv' },
    ),
  () =>
    agent(
      `${SOURCES}

MATCH ASSESSMENT (already produced):
${match.match}

${VOICE}

${NO_GAP_ECHO}

Draft a short, specific cover letter in markdown for THIS offer (company + role named): why this
role, and what the candidate brings (evidenced). No filler, no claims beyond the evidence.${styleLine('coverLetter')} Return it as "cover_letter".`,
      { schema: strField('cover_letter', 'markdown cover letter'), phase: 'Tailor', label: 'cover-letter' },
    ),
  () => {
    const uncovered = (match.must_haves || []).filter((m) => m.covered === false)
    const uncoveredBlock = uncovered.length
      ? uncovered
          .map(
            (m) =>
              `- ${m.requirement}\n  mitigation: ${m.mitigation ?? '(none — gapNarrative offers nothing relevant)'}\n  suggestion: ${m.suggestion ?? '(none)'}`,
          )
          .join('\n')
      : '(none — no uncovered must-haves from the match pass)'
    return agent(
      `${SOURCES}

MATCH ASSESSMENT (already produced):
${match.match}

PER-GAP MITIGATION + SUGGESTION (already produced, from the must_haves pass):
${uncoveredBlock}

Write an honest gap report in markdown: each must-have the candidate does NOT clearly meet, how
big the gap is, any genuine adjacent/transferable evidence to mention (or to leave out), and — for
each — the mitigation and suggestion above, woven into prose rather than pasted verbatim.

You MUST end the report with a section headed "## Top-3 prep actions" — a numbered list of the 3
highest-priority suggestions across all gaps (fewer than 3 if there are fewer than 3 gaps), ranked
by how much each would move this specific offer. Do not skip this section even if it feels
repetitive with the body above.

This is for the candidate's eyes, not the employer — never soften or omit an honest gap. Return it
as "gap_report".`,
      { schema: strField('gap_report', 'markdown gap report'), phase: 'Tailor', label: 'gap-report' },
    )
  },
])

// --- optional critique loop (#272) ----------------------------------------------------
// draft (above) → critique (grounded in SOURCES) → revise, gated by args.critique. Trims
// low-relevance / duplicated / unsupported / cover-letter-dependent lines and grounds anything
// weakly supported — but NEVER invents experience and NEVER hides an honest gap. When off,
// cvText/coverText are the untouched drafts, so the default path is byte-for-byte unchanged.
let cvText = cv.cv
let coverText = cover.cover_letter
if (CRITIQUE) {
  phase('Critique')
  for (let round = 1; round <= CRITIQUE_ROUNDS; round++) {
    const critique = await agent(
      `${SOURCES}

DRAFT CV (revision ${round}):
${cvText}

DRAFT COVER LETTER (revision ${round}):
${coverText}

Critique these drafts against the candidate's real evidence. For each CV bullet and cover-letter
sentence, judge: (a) RELEVANCE to this offer's must-haves, (b) UNIQUENESS (redundant with another
line?), (c) GROUNDING (truly supported by the evidence, or an unsupported claim / keyword-stuffing?),
and (d) for cover-letter lines, whether they merely restate the CV. List concrete, minimal edits:
which specific lines to trim, merge, or ground better. HARD RULES: never suggest inventing experience
the evidence does not support, and never suggest removing or softening an honest gap the candidate
genuinely has. Return the critique as "critique".`,
      { schema: strField('critique', 'markdown line-level critique'), phase: 'Critique', label: `critique-${round}` },
    )
    const revised = await agent(
      `${SOURCES}

CURRENT CV:
${cvText}

CURRENT COVER LETTER:
${coverText}

CRITIQUE TO APPLY:
${critique.critique}

Apply ONLY the edits the critique names: trim, merge, or better-ground the flagged lines and leave
every unflagged line untouched. Keep the CV ATS-safe (single column, no tables/HTML, standard
headings) and keep every honest gap visible. NEVER invent experience beyond the evidence. Return the
revised CV as "cv" and the revised cover letter as "cover_letter".`,
      {
        schema: {
          type: 'object',
          properties: {
            cv: { type: 'string', description: 'revised markdown CV' },
            cover_letter: { type: 'string', description: 'revised markdown cover letter' },
          },
          required: ['cv', 'cover_letter'],
        },
        phase: 'Critique',
        label: `revise-${round}`,
      },
    )
    cvText = revised.cv
    coverText = revised.cover_letter
  }
}

phase('Prefill')
const fieldsBlock = FIELDS
  ? `Fill EXACTLY these application fields (from the live job form):\n${FIELDS}`
  : `Use a standard application field set: first/last name, email, phone, resume, cover letter,
LinkedIn, website, plus typical screening questions (work authorization, relocation, notice period).`
const prefill = await agent(
  `${SOURCES}

TAILORED CV (already produced):
${cvText}

COVER LETTER (already produced):
${coverText}

Assemble a prefill pack in markdown: for each application field, give the value the candidate would
enter, drawn ONLY from the evidence library / tailored CV. ${fieldsBlock}

For anything you cannot ground in the evidence (salary expectation, work authorization, exact dates,
demographic questions), write "[NEEDS HUMAN INPUT]" — do not guess.

HARD RULE: this pack is for the candidate to REVIEW and SUBMIT MANUALLY. It is NOT an automated
submission, contains no scripts/links to auto-apply, and must never instruct bypassing a form or
CAPTCHA. Return it as "prefill_pack".`,
  { schema: strField('prefill_pack', 'markdown prefill pack'), phase: 'Prefill', label: 'prefill-pack' },
)

log(`Pack ready for ${offerId}`)
return {
  slug: offerId,
  lane,
  offer_id: offerId,
  match: match.match,
  must_haves: match.must_haves,
  cv: cvText,
  cover_letter: coverText,
  gap_report: gap.gap_report,
  prefill_pack: prefill.prefill_pack,
}
