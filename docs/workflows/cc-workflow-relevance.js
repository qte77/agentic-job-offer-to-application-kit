// Stage-2 relevance pass: screen ingested job descriptions (JDs) against the candidate's
// evidence library + the five target lanes, and shortlist with per-lane fit scores.
//
// EXECUTION MODEL: a Claude Code Workflow-tool script (not node/make). Ingest + chunk first
// (`scripts/ingest.sh` then `python -m ajoa_kit.chunk`), read the batch count from
// results/batches/manifest.json, then run:
//
//   Workflow({ scriptPath: 'docs/workflows/cc-workflow-relevance.js', args: {
//     rootDir:     '.',     // repo root holding results/batches/ + results/evidence-library.json
//     batchCount:  N,       // REQUIRED — results/batches/manifest.json .batch_count
//     limitBatches: K,      // optional — sample the first K batches (dry run)
//     // libraryPath / library — optional overrides; by default each agent reads
//     //   results/evidence-library.json (the Stage-1 output) for the candidate brief
//   }})
//
// Persist the returned shortlist with: uv run ajoa-kit persist <output.json>  (or: make persist FILE=…)
//
// Hooks: agent(), parallel(), phase(), log(). agent(prompt,{schema}) returns the
// schema-validated object. The Workflow script has no filesystem access, but its agents do
// (they Read the batch files and the evidence library themselves).

export const meta = {
  name: 'relevance',
  description:
    'LLM relevance pass: screen ingested JDs against the candidate evidence library + 5 lanes, shortlist with per-lane fit scores. Replaces a crude keyword filter that over-matched.',
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

const LANES = ['cxo', 'founding', 'engineering', 'cloud', 'architect']

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
        },
        required: ['id', 'best_lane', 'score', 'verdict', 'rationale'],
      },
    },
    dropped_count: { type: 'integer' },
    dropped_reason_sample: { type: 'string' },
  },
  required: ['relevant', 'dropped_count'],
}

function gatePrompt(path) {
  const brief = LIBRARY_INLINE
    ? `CANDIDATE BRIEF (provided inline):\n${JSON.stringify(LIBRARY_INLINE)}`
    : `CANDIDATE: read the evidence library at ${LIBRARY_PATH} with the Read tool — use its headline, positioningSummary, per-lane *Angle paragraphs, skillClusters, and gapNarrative as the candidate's genuine OFFERS and honest MISSING per lane.`
  return `You are screening job descriptions for ONE candidate against five target lanes (${LANES.join(', ')}). Read the JSON file at ${path} with the Read tool — it is an array of ~40 job descriptions, each {id, title, company, location, url, description, ...}.

${brief}

Judge on REAL requirement overlap, NOT keyword presence; be strict and honest about gaps.

DROP (do not return) any JD that: is a non-engineering function (sales, marketing, recruiting, legal, finance, support, people/HR, pure visual design); is junior/intern; hard-requires years of people-management or large-team leadership; hard-requires deep cloud-infra-at-scale (AWS/GCP/Azure/Kubernetes/Terraform) or production-at-scale ops as a must-have; or has no genuine overlap with any lane.

For each KEPT JD return: id, title, company, url, best_lane (single best fit), score 0-5 (5 = strong fit, 3 = plausible stretch, <3 = drop), verdict ("shortlist" for score>=4, "maybe" for 3), and a one-line rationale naming the fit AND the main gap. Only return JDs scoring >=3. Also return dropped_count (how many you dropped) and dropped_reason_sample (one short phrase of why the bulk were dropped).`
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
