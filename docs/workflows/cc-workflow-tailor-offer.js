// Stage-3 tailor pass: turn ONE shortlisted job offer into a per-offer application pack
// (match -> tailored CV + cover letter -> gap report) grounded in the evidence library.
//
// EXECUTION MODEL: a Claude Code Workflow-tool script (not node/make). Run Stage-1 + Stage-2
// first (evidence-library, ingest, chunk, relevance, then `python -m ajoa_kit.persist_scored <output.json>`
// so results/<lane>/shortlist.json exists), pick one offer id from a shortlist, then run:
//
//   Workflow({ scriptPath: 'docs/workflows/cc-workflow-tailor-offer.js', args: {
//     rootDir: '.',              // repo root holding results/ (override for an alt workspace)
//     lane:    'engineering',    // REQUIRED — which results/<lane>/shortlist.json to read
//     offerId: 'ashby:acme:101', // REQUIRED — the shortlist entry id to tailor
//     style:   { cv, coverLetter }, // optional — writing-style directives (#16); generate with
//                                // `ajoa-kit style --json` (reads config/style.json). Omit = neutral.
//     fields:  '<markdown>',      // optional — application-field checklist for the prefill pack (#50);
//                                // generate with `ajoa-kit prefill-fields ...`. Omit = generic fields.
//   }})
//
// Persist the returned pack with: python -m ajoa_kit.persist_offer <output.json>
// (writes results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md — human reviews + submits).
//
// SCOPE: pre-fill + human submit only, NO auto-apply (verified safe in research.md §Delivery, #8).
// The prefill pack is assembled for a human to review and submit; `persist_offer` auto-runs the
// `ats-check` parse-safety pass (#9, #75) on the CV and writes `cv-ats-check.md` if it flags anything
// (non-blocking review aid — `ajoa-kit ats-check <cv.md>` can still be run manually).
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
    { title: 'Prefill', detail: 'assemble a human-review prefill pack (no auto-submit) from the CV + fields' },
  ],
}

// --- config (override via args) -------------------------------------------------------
const cfg = typeof args === 'object' && args ? args : {}
const rootDir = cfg.rootDir || '.'
const lane = cfg.lane
const offerId = cfg.offerId
// Optional writing-style directives, keyed { cv, coverLetter } (from `ajoa-kit style --json`, #16).
const STYLE = cfg.style && typeof cfg.style === 'object' ? cfg.style : {}
// Optional application-field checklist for the prefill pack (from `ajoa-kit prefill-fields`, #50).
const FIELDS = typeof cfg.fields === 'string' ? cfg.fields : ''

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

phase('Match')
log(`Tailoring ${offerId} (lane: ${lane}) from ${SHORTLIST_PATH}`)

const match = await agent(
  `${SOURCES}

Assess this ONE offer against the candidate. Write a concise markdown "match assessment": the
JD's real must-haves and nice-to-haves, which the candidate genuinely covers (cite evidence),
and which they do not. Be strict and honest — no overstatement. Return the prose as "match".

Also return "must_haves": an array with one object per JD must-have requirement —
{ requirement: the must-have (verbatim or tightly paraphrased), covered: true/false for whether the
candidate genuinely meets it, evidence: a short citation from the evidence library / CV, or null if
it is a gap }.`,
  { schema: matchSchema, phase: 'Match', label: 'match' },
)

phase('Tailor')
const [cv, cover, gap] = await parallel([
  () =>
    agent(
      `${SOURCES}

MATCH ASSESSMENT (already produced):
${match.match}

Draft a tailored, ATS-safe CV in markdown for THIS offer: clean single-column, standard headings,
no tables/graphics. Reorder and select from masterCvBullets/perProject to lead with what this JD
weighs most. Use only evidenced bullets.${styleLine('cv')} Return it as "cv".`,
      { schema: strField('cv', 'markdown tailored CV'), phase: 'Tailor', label: 'cv' },
    ),
  () =>
    agent(
      `${SOURCES}

MATCH ASSESSMENT (already produced):
${match.match}

Draft a short, specific cover letter in markdown for THIS offer (company + role named): why this
role, what the candidate brings (evidenced), and an honest framing of context using gapNarrative.
No filler, no claims beyond the evidence.${styleLine('coverLetter')} Return it as "cover_letter".`,
      { schema: strField('cover_letter', 'markdown cover letter'), phase: 'Tailor', label: 'cover-letter' },
    ),
  () =>
    agent(
      `${SOURCES}

MATCH ASSESSMENT (already produced):
${match.match}

Write an honest gap report in markdown: each must-have the candidate does NOT clearly meet, how
big the gap is, and any genuine adjacent/transferable evidence to mention (or to leave out).
This is for the candidate's eyes, not the employer. Return it as "gap_report".`,
      { schema: strField('gap_report', 'markdown gap report'), phase: 'Tailor', label: 'gap-report' },
    ),
])

phase('Prefill')
const fieldsBlock = FIELDS
  ? `Fill EXACTLY these application fields (from the live job form):\n${FIELDS}`
  : `Use a standard application field set: first/last name, email, phone, resume, cover letter,
LinkedIn, website, plus typical screening questions (work authorization, relocation, notice period).`
const prefill = await agent(
  `${SOURCES}

TAILORED CV (already produced):
${cv.cv}

COVER LETTER (already produced):
${cover.cover_letter}

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
  cv: cv.cv,
  cover_letter: cover.cover_letter,
  gap_report: gap.gap_report,
  prefill_pack: prefill.prefill_pack,
}
