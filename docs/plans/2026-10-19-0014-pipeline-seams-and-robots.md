# Plan 014: pipeline seams and robots.txt

## Status (read this first)

- **Arc goal:** close the manual seams the 2026-10-19 offer refresh exposed (#365, #346, #342,
  #344) and the robots.txt / crawl-delay gap ADR-0002 names as out of scope (#454).
- **Shipped:** #458 (`startBatch` slices for the relevance workflow); PR-A (#365).
- **Next, in order:** PR-B (#346), then PR-C (#342 + #344), then PR-D (#454). PR-C waits until
  any in-flight relevance screen has finished and been persisted: never re-run `chunk` while a
  screen is running.
- **Loop per PR:** topic branch from main, red test first, `make check` last, changelog fragment,
  docs audit, push, squash-merge with `--admin` only when that PR's own checks are green, delete
  the branch, strike the row below in the same PR.
- **Owner gate:** PR-D step 1 (robots audit). If an ATS API host disallows `User-agent: *`, the
  owner decides before any enforcement code is written.
- **Watch-outs:** a workflow resume only works inside the Claude Code session that started it;
  the per-run agent cap is min(16, CPUs - 2), so 2 on the 2-CPU devcontainer.

## Source map

| Area | Location | Notes |
| --- | --- | --- |
| Offer pack writer | `src/ajoa_kit/persist_offer.py` `write_pack`, `render`, `_load_offer_index` | `result.json` + `OfferMeta` (PR-A) |
| Offer meta model | `src/ajoa_kit/models.py` `OfferMeta` | PR-B adds `tailored_against` |
| Corpus digest | `src/ajoa_kit/ingest.py` `_update_corpus` | delisted count already in `summary` |
| Snapshot date | `max(last_seen)` in `refresh.py`, `companies.py`, `chunk.py` | one helper in PR-B |
| Shortlist row model | `src/ajoa_kit/models.py` `ScoredItem` (`extra="allow"`) | PR-B adds `scored_against` |
| Relevance persist | `src/ajoa_kit/persist_scored.py` `load_result`, `parse_relevant`, `main` | PR-C adds `--from-batches` |
| Batch manifest | `src/ajoa_kit/chunk.py` manifest write | PR-C adds `batch_set_id`, `new`; `tests/test_e2e_pipeline.py` pins the manifest dict |
| Relevance workflow | `.claude/workflows/cc-workflow-relevance.js` | PR-C: optional `batchSetId`, per-batch files |
| Fetch call sites | `sources.py` `get_json`/`get_bytes`, `slug_probe.py` `fetch_status`/`_count`, `prefill.py`, `startups_gallery.py` | PR-D routes all through one helper |
| ToS policy | `docs/decisions/0002-source-tos-tiers.md` "Out of scope" | PR-D marks robots implemented |
| Upstream | polyfetch-scrape `throttle.py` `Throttle`; polyfetch #147 (planned robots helper) | no polyfetch change in this arc |

## Approach

- **PR-B #346:** print `N delisted -- run: ajoa-kit refresh` after the ingest digest; one
  `corpus_snapshot()` helper (max `last_seen`) reused by its three current call sites; stamp
  `scored_against` on new shortlist rows and `tailored_against` in `meta.json`. The stamp equals
  the pull date only when ingest ran with `--merge`.
- **PR-C #342 + #344:** `chunk` stamps a `batch_set_id` into the manifest. With `batchSetId` set,
  each relevance agent also writes its result to `results/relevance/<id>/batch-NNN.json`.
  `persist --from-batches` reads the current id's files through `parse_relevant`, always merges,
  and prints missing batches as `startBatch`/`limitBatches` ranges; files for an older id are
  ignored with a warning. `make relevance` prints the ready Workflow call. Verify live first that
  a workflow agent can write under `results/`. Then evaluate headless `claude -p` slices writing
  to the same files (unverified whether a headless session may call the Workflow tool). The
  tailor -> `persist-offer` hand-off stays manual.
- **PR-D #454:** one `polite_fetch` in `sources.py` used by all fetch call sites; per-origin
  `urllib.robotparser` cache checked with `User-agent: *` (polyfetch rotates browser UAs);
  per-host spacing max(1 s, crawl-delay); robots 4xx = allow, 5xx/network error = skip with a
  logged reason (inconclusive in `refresh`/`verify-sources`); skips show in ingest's
  `sources ok / failed` summary; per-source `_robots_override` with a reason.

## Remaining work

| Item | Gate | Done when |
| --- | --- | --- |
| ~~PR-A #365: packs keep `result.json`; `generated_from` frontmatter; `OfferMeta`~~ | agent | shipped in this PR |
| Persist the 4 in-flight relevance slices, re-run `pack-plan` at score 4 and 5, report | agent | shortlists merged; pack numbers reported to the owner |
| PR-B #346: delisted hint; `corpus_snapshot`; `scored_against` / `tailored_against` | agent | merged; `ingest --merge` prints the hint; new rows carry the stamp |
| PR-C #342 + #344: `batch_set_id`; per-batch files; `persist --from-batches`; `make relevance` | agent | merged; a live one-batch run is picked up by `persist --from-batches` |
| PR-C follow-up: headless `claude -p` slices writing per-batch files | agent | a headless slice run lands its files, or the limit is documented |
| PR-D step 1: robots audit over every `config/default-seed.json` host | owner (if any ATS API host disallows) | audit report posted on #454 |
| PR-D #454: `polite_fetch` with robots + crawl-delay | agent | merged; one live ingest pass with no unexpected skips |
