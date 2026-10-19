# Plan 014: pipeline seams, offloading and robots.txt

## Status (read this first)

- **Arc goal:** close the manual seams the 2026-10-19 offer refresh exposed (#365, #346, #342,
  #344), run long relevance screens outside the interactive session, cut their cost with a cheap
  decision-model pre-filter, and close the robots.txt / crawl-delay gap ADR-0002 names as out of
  scope (#454).
- **Shipped:** #458 (`startBatch` slices for the relevance workflow); #459 (PR-A, #365); #460
  (PR-B, #346); PR-D (#454) in the PR that strikes its row.
- **Next, in order:** PR-C (#342 + #344, with headless offload), then PR-E (decision-model
  pre-filter; keys are in the git-ignored `.env`). PR-C waits until any in-flight relevance screen has finished and been persisted:
  never re-run `chunk` while a screen is running.
- **Loop per PR:** topic branch from main, red test first, `make check` last, changelog fragment,
  docs audit, push, squash-merge with `--admin` only when that PR's own checks are green, delete
  the branch, strike the row below in the same PR.
- **Owner gates:** none open. `TYPESAFE_API_KEY` and `CLOUDFLARE_API_TOKEN` are in `.env`; the
  Cloudflare account id for Clef is looked up with the token (or set `CLOUDFLARE_ACCOUNT_ID`).
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
- **PR-E decision-model pre-filter (owner: both backends, shadow mode first):** a `prefilter`
  subcommand sends each JD plus a short candidate summary from the evidence library to a decision
  model, one yes/no fit question per lane in a single call, and records the probabilities. Two
  backends: Jev (`POST https://api.typesafe.ai/v1/systemone`, model `jev-1.13.0`) and Clef-flash
  (Workers AI `@cf/cloudflare/clef-flash`). Shadow mode: score the 2026-10-19 screen, whose
  kept/dropped verdicts and scores are the labels, and pick a backend and threshold from that
  before the pre-filter gates anything. A 403, an error or a missing confidence escalates to the
  LLM screen, never a verdict. Stdlib HTTP only; switch to the shared `decide()` action once it
  merges.
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
| Persist the 4 in-flight relevance slices, re-run `pack-plan` at score 4 and 5, report | agent | shortlists merged; pack numbers reported to the owner |
| ~~PR-B #346: refresh hint; `last-pull.json`; `scored_against` / `tailored_against`~~ | agent | shipped in this PR |
| PR-C #342 + #344: `batch_set_id`; per-batch files; `persist --from-batches`; `make relevance`; `make relevance_headless` | agent | merged; a headless one-batch run is picked up by `persist --from-batches` |
| PR-E: `prefilter` subcommand with Jev and Clef backends; shadow-mode report on the 2026-10-19 screen | agent | merged; report shows per-backend recall of kept offers and the drop rate at the chosen threshold |
| ~~PR-D step 1: robots audit over every configured source~~ | agent | done: the live ingest found no source blocked by robots.txt |
| ~~PR-D #454: `polite_fetch` with robots + crawl-delay~~ | agent | shipped in this PR |
