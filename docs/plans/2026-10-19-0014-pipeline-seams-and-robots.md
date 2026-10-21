# Plan 014: pipeline seams, offloading and robots.txt

## Status (read this first)

- **Arc goal:** close the manual seams the 2026-10-19 offer refresh exposed (#365, #346, #342,
  #344), run long relevance screens outside the interactive session, cut their cost with a cheap
  decision-model pre-filter, and close the robots.txt / crawl-delay gap ADR-0002 names as out of
  scope (#454).
- **Shipped:** #458 (`startBatch` slices for the relevance workflow); #459 (PR-A, #365); #460
  (PR-B, #346); #461 (PR-D, #454); #462 (PR-E shadow tool); the Jev decision gate
  (`chunk --decision-gate`) in the PR that strikes its row.
- **Next:** PR-C (#342 + #344, with headless offload). Never re-run `chunk` while a relevance
  screen is running. Use `chunk --new --decision-gate` for the next re-screen.
- **Loop per PR:** topic branch from main, red test first, `make check` last, changelog fragment,
  docs audit, push, squash-merge only when that PR's own checks are green, delete
  the branch, strike the row below in the same PR.
- **Owner gates:** none open. The owner chose (2026-10-21) to switch Jev on at 0.25 rather than
  wait for per-lane questions. Keys are in `.env`: `TYPESAFE_API_KEY`, `CLOUDFLARE_API_TOKEN`,
  `CLOUDFLARE_ACCOUNT_ID`.
- **Watch-outs:**
  - A workflow resume only works inside the Claude Code session that started it.
  - Each workflow run caps concurrent agents (2 on this 2-CPU devcontainer). Raise it with
    `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` (1-256), set before the session or process starts.
  - Each workflow agent carries roughly 50k tokens of fixed context, so fewer, larger batches cost
    less.

## Source map

| Area | Location | Notes |
| --- | --- | --- |
| Offer pack writer | `src/ajoa_kit/persist_offer.py` `write_pack`, `render`, `_load_offer_index` | `result.json` + `OfferMeta` (PR-A) |
| Offer meta model | `src/ajoa_kit/models.py` `OfferMeta` | `tailored_against` (PR-B) |
| Pull date | `src/ajoa_kit/pull.py` `write_pull_date`, `pull_date`; `results/last-pull.json` | written by `ingest.main` (PR-B) |
| Corpus digest | `src/ajoa_kit/ingest.py` `_update_corpus` | refresh hint (PR-B) |
| Shortlist row model | `src/ajoa_kit/models.py` `ScoredItem` (`extra="allow"`) | `scored_against` (PR-B) |
| Relevance persist | `src/ajoa_kit/persist_scored.py` `load_result`, `parse_relevant`, `_normalize`, `main` | PR-C adds `--from-batches` |
| Batch manifest | `src/ajoa_kit/chunk.py` manifest write | PR-C adds `batch_set_id`, `new`; `tests/test_e2e_pipeline.py` pins the manifest dict |
| Relevance workflow | `.claude/workflows/cc-workflow-relevance.js` | PR-C: optional `batchSetId`, per-batch files |
| Headless pattern | `claude-code-plugins` `plugins/docs-generator/Makefile` `writeup_generate` | `timeout` + `--output-format stream-json` to a log file; exit 124 = timeout |
| Fetch call sites | `sources.py` `get_json`/`get_bytes`, `slug_probe.py` `fetch_status`/`_count`, `prefill.py`, `startups_gallery.py` | PR-D routes all through one helper |
| ToS policy | `docs/decisions/0002-source-tos-tiers.md` "Out of scope" | PR-D marks robots implemented |
| Upstream | polyfetch-scrape `throttle.py` `Throttle`; polyfetch #147 (planned robots helper) | no polyfetch change in this arc |
| Shared decision action | qte77/.github `actions/decide/` (PR qte77/.github#45, open) | PR-E switches to it once merged |

## Approach

- **PR-B #346 (shipped):** `ingest` writes its pull date to `results/last-pull.json`. `persist`
  stamps it on newly scored rows as `scored_against` (a merge re-stamps only re-scored rows);
  `persist-offer` writes it to `meta.json` as `tailored_against`. `ingest --merge` prints
  `N delisted -- run: ajoa-kit refresh`. A small sidecar instead of `max(last_seen)` over the
  118 MB `corpus.json`.
- **PR-C #342 + #344:** `chunk` stamps a `batch_set_id` into the manifest. With `batchSetId` set,
  each relevance agent also writes its result to `results/relevance/<id>/batch-NNN.json`.
  `persist --from-batches` reads the current id's files through `parse_relevant`, always merges,
  and prints missing batches as `startBatch`/`limitBatches` ranges; files for an older id are
  ignored with a warning. `make relevance` prints the ready Workflow call.
  `make relevance_headless` runs slices as `claude -p` processes, following the docs-generator
  pattern (`timeout`, `--output-format stream-json` to a log) plus the flags verified on
  2026-10-19: `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS=<n>`,
  `--allowedTools "Workflow" "Edit(results/**)" "Read"`, `--permission-mode acceptEdits`. A
  4-agent smoke test confirmed that headless workflows run to completion, write under `results/`
  and honour the concurrency setting. The tailor -> `persist-offer` hand-off stays manual.
- **PR-E decision-model pre-filter, shadow tool (shipped):** `ajoa-kit decision-prefilter`
  (`src/ajoa_kit/decision_prefilter.py`) sends each JD plus the evidence library's headline and positioning
  summary to a decision model with ONE question ("a plausible fit in any lane?"). Backends: Jev
  (`POST https://api.typesafe.ai/v1/systemone`, `jev-1.13.0`) and Clef-flash (Workers AI
  `@cf/cloudflare/clef-flash`, reply wrapped in `result`). Any failure returns `None`, so the JD
  goes on to the LLM screen. Stdlib HTTP; our own small client (the shared `decide()` is unmerged
  and has no Clef backend). Shadow result 2026-10-21, 500 JDs from the 2026-10-19 screen (250 kept
  incl. 118 score 4+ and 18 score 5, 250 dropped), no errors on either backend:

  | | Jev | Clef-flash |
  | --- | --- | --- |
  | AUC (kept vs dropped) | 0.880 | 0.859 |
  | Gate keeping all 118 score-4+ offers | 0.25, about 30% of JDs dropped | 0.10, about 20% dropped |
  | Gate at 0.30 | 98.3% of score-4+ kept, 37.5% dropped | 93.2% kept, 50.4% dropped |

  Neither meets the 98% recall / 50% drop bar with one question. The labels are the LLM screen's
  verdicts, so this measures agreement with it, not ground truth.
- **PR-D #454 (shipped):** `polite_fetch` in `src/ajoa_kit/polite.py`, used by all six fetch
  call sites; per-origin `urllib.robotparser` cache checked with `User-agent: *` (polyfetch rotates
  browser UAs); per-host spacing max(1 s, crawl-delay); robots 4xx = no rules (including 4xx that
  polyfetch raises as typed errors such as `AuthRequired`), 5xx/network error = skip with a reason
  (inconclusive in `refresh`/`verify-sources`); skips show in ingest's `sources ok / failed`
  summary. Live check 2026-10-19: a full ingest kept 331 ok / 18 failed (the same dead boards as
  before), with no robots skips. The per-source `_robots_override` key was dropped: no shipped
  source needs it.

## Remaining work

| Item | Gate | Done when |
| --- | --- | --- |
| ~~PR-A #365: packs keep `result.json`; `generated_from` frontmatter; `OfferMeta`~~ | agent | shipped in #459 |
| ~~Persist the 4 in-flight relevance slices, re-run `pack-plan` at score 4 and 5, report~~ | agent | done 2026-10-20: score 5 = 121 live (25 packed), score 4+ = 956 live (44 packed) |
| ~~PR-B #346: refresh hint; `last-pull.json`; `scored_against` / `tailored_against`~~ | agent | shipped in #460 |
| PR-C #342 + #344: `batch_set_id`; per-batch files; `persist --from-batches`; `make relevance`; `make relevance_headless` | agent | merged; a headless one-batch run is picked up by `persist --from-batches` |
| ~~PR-E: `decision-prefilter` subcommand with Jev and Clef backends; shadow-mode report on the 2026-10-19 screen~~ | agent | shipped in this PR (results above) |
| ~~Pre-filter next step: switch Jev on at a zero-loss threshold, or add per-lane questions and re-run the shadow test~~ | owner | shipped in this PR: `chunk --decision-gate` (Jev below 0.25 skipped). Live check on one 40-JD batch: 26 skipped, none of Claude's 5 kept JDs among them |
| Per-lane decision questions (7 nouls per call) to push the skip share past 50% at the same recall | agent | deferred: only if the 30% saving proves too small; needs its own shadow run first |
| ~~PR-D step 1: robots audit over every configured source~~ | agent | done: the live ingest found no source blocked by robots.txt |
| ~~PR-D #454: `polite_fetch` with robots + crawl-delay~~ | agent | shipped in #461 |
