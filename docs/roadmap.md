# Roadmap

## Shipped — first end-to-end (e2e) happy path

- Evidence-library workflow (`cc-workflow-evidence-library.js`).
- Ingest → chunk → relevance, generic + config-driven (`src/ajoa_kit/`, `cc-workflow-relevance.js`).
- `AppSettings` (pydantic-settings) config + `ajoa-kit` CLI: env-overridable `config/` + `results/`
  paths (no hardcoded `ROOT`); the subcommand set is in `src/ajoa_kit/__main__.py` (ADR-0001 L1/L2).
- Baseline gates: ruff, pyright, complexipy, a value-add `pytest` suite, CodeQL + Dependabot + CI
  (SHA-pinned), and markdownlint + lychee (local `make docs-lint` + a `lint-md-links` CI workflow).
- Release tooling: scriv changelog fragments under `changelog.d/`; bump-my-version → tag-release →
  publish-release pipeline (v0.2.0 cut; SHA-pinned, unsigned tags).
- Governance, docs, and a synthetic worked example (`examples/alexis-doe/`).
- Stage 3 tailoring (`cc-workflow-tailor-offer.js` + `persist_offer`): per-offer pack — match → CV +
  cover letter + gap report + human-review prefill pack + optional JD must-have coverage report (#55)
  (`results/offers/<slug>/`). `ajoa-kit ats-check`
  résumé parse-safety (#9); style/tone from `config/style.json` (#16); cited ToU/CFAA/GDPR delivery
  safety note (`research.md` §Delivery, #8).
- Repo hardening: coverage gate (#33), docs-only CI `paths-ignore` (#34), `CONTRIBUTING.md` (#35),
  qte77 badge set (#22), structured board catalog (#10), docs structural-integrity pass (#57), and the
  org reusable `lint-md-links` workflow.
- Ingest test coverage (#53): per-adapter error/edge tests for every feed/ATS/aggregator adapter
  (normalization, missing/null tolerance, Lever's non-list-payload guard) plus a `collect()`
  warn-and-continue case — the adapters were already tolerant, so no hardening was needed — and
  offline `get_json`/`get_bytes` network-helper tests (non-200 → `FetchError`, 200 → parse).
- Keyword-trend pipeline: runtime-configurable pre-filter keywords (`config/keywords.json`, #31);
  `ajoa-kit trend-snapshot` → keyword-only `public-data/trends.ndjson` (#11 PR-A); reusable
  `run-with-keywords` workflow (#79).
- Two-tab trends dashboard (#11 PR-B): static no-build gh-pages page — Tab A synthetic shortlist,
  Tab B real aggregate `{week,counts}` keyword timeline (line + bar, vendored Chart.js); `WeekCounts`
  pydantic contract.
- Source ToS/ToU tiers: ADR-0002 classifies ingest sources OK/CAUTION/BLOCKED with per-source
  verified findings + `_date_verified` stamps in `config/default-seed.json` (#95).
- Broad/recall ingest lane: arbeitnow + The Muse JSON-aggregator adapters under the loaded
  `aggregators` key (#94, ToS-tiered in ADR-0002; jobicy/himalayas/remotive stay `_deferred`,
  keyed Adzuna/Reed/Jooble are #109 outlook); +11 re-probed OK-tier company boards (#96) and +21
  FR/UK/IT/US company boards for geographic breadth, plus +6 AI/eng boards (Zoox, Cerebras, xAI,
  Perplexity, Scale AI, Runway — reachability-probed 2026-06-22) in `config/default-seed.json`.
- Dashboard UX + reliability: trends bundled **same-origin** into the published site at deploy (Pages
  re-deploys on `data`-branch pushes — no fragile cross-origin fetch); expandable shortlist rows that
  reveal the tailored CV + cover letter (demo `cv`/`cover_letter` in `demo.json`); a market-trends
  time-frame picker (All…1w); header Repo/Issues links; `make preview` serves a throwaway copy that
  keeps real data out of the source `ui/` **and shows your real local shortlist** (#209 — aggregated
  same-origin from `results/<lane>/shortlist.json`, never published); expanding a tailored offer's row
  now reveals its CV + cover letter, joined from `results/offers/<slug>/` by JD id.
- AI issue-triage CI (`.github/workflows/issue-triage.yaml`): `qte77/gha-issue-triage` (SHA-pinned,
  GitHub Models, zero-secret) auto-labels newly opened issues.
- Data-contract ADR (ADR-0003, #158): maps the typed vs untyped layer boundaries and sets the
  pydantic + JSON-Schema direction with a prioritized hardening backlog (decision only, no code).
- Position-lane SSOT (#195): a tracked `config/lanes.json` (the canonical 7 lanes) loaded Python-side
  by `ingest.load_lanes()` (pydantic `Lane`) and emitted via `ajoa-kit lanes --json` to pass the
  relevance/evidence workflows as `cfg.lanes`; the two JS fallbacks now mirror it. The
  `persist_scored` lane-membership check now ships (a hallucinated `best_lane` → `unsorted/`);
  `JobRecord` typing (the rest of ADR-0003) stays backlog.
- Shortlist liveness (#214): `ajoa-kit refresh [--lane <name>] [--delete] [--dry-run]` reconciles each
  `results/<lane>/shortlist.json` against the corpus `delisted` state + a read-only URL re-probe,
  flagging dead offers `stale` (dashboard-hidden) or removing them; an inconclusive probe never expires
  a live entry.
- Incremental new-offer delta-screen (#226): `ajoa-kit chunk --new` batches only the latest-pull corpus
  delta (offers whose `first_seen == max(last_seen)`) and `ajoa-kit persist --merge` unions the scored
  delta by `id` into the existing per-lane shortlists + `jobs-scored.json` (a re-scored offer wins)
  instead of overwriting — completing the incremental refresh cycle (the "scan new" complement to
  #214's "check still valid"). Extended by #235 to also re-screen `changed` records (not just
  first-seen-new), via a `last_changed` corpus stamp.
- PII-free trends relocation (#210): the publishable keyword-only trends moved out of the PII dir
  `results/` into a dedicated git-ignored `public-data/` (`AJOA_PUBLIC_DATA_DIR`), so `results/` is now
  **exclusively PII**. `make trends-data` builds the `data`-branch tree from `public-data/` and a
  **tree-allowlist guard** aborts the push if anything other than `public-data/trends{,-daily}.ndjson`
  slipped in — the publish boundary is now structural + enforced, not just conventional.
- UI theming converged on the qte77 brand (#112/#117): EyeRest tokens, `qte77-theme` storage key,
  system/light/dark cycle, `.sr-only` clip-path; Inter now served as WOFF2 (TTF fallback).
- Governance safe-subset settled (#54, closed): selected-actions allowlist + full SHA-pinning
  enforced and the branch ruleset reverted to permit the solo `--admin` / unsigned-release flow;
  strict signed-tag (03) and required-review (06) rulesets intentionally excluded.
- Offline e2e pipeline smoke test (#165): pins the deterministic `chunk → persist_scored →
  persist_offer → ats_check` chain with canned synthetic Workflow outputs (the LLM relevance/tailor
  steps can't run in CI), guarding the cross-stage seams under `make check`.
- Daily incremental ingest (#164): scheduled cron (`.github/workflows/ingest-daily.yaml`, 06:00 UTC +
  `workflow_dispatch`) that dedup-merges each pull into a running `results/corpus.json` via the
  4-state `merge_corpus()` (new/changed/unchanged/delisted; first_seen/last_seen/content_hash; CLI
  `ajoa-kit ingest --merge`), buckets trends by `first_seen`, and pushes the aggregate keyword-only
  trends to the `data` branch — corpus kept as a private cross-run artifact (no PII on any branch),
  polyfetch borrowed via a public-repo checkout. Dispatch-verified end-to-end (4248 JDs; trends
  preserved).
- Daily offer digest (#175): a local-only "what changed today" report over the corpus
  (`corpus.summarize_changes` + `render_daily_summary` → `results/daily-summary.md`), emitted from
  `ingest --merge`. It names companies/titles, so it stays local-only (git-ignored `results/`, never a
  CI artifact or branch); the daily cron still publishes only the aggregate keyword trends.
- Source freshness re-probe (#217): `ajoa-kit verify-sources [--dry-run]` re-probes every
  `config/default-seed.json` `feeds`/`ats` source read-only and stamps `_date_verified` on the live
  ones (feeds by a 2xx/3xx GET, ats boards by a live role count via `slug_probe.PROBES`), reporting the
  rest for manual triage. A one-pass backfill dated all 142 seed sources (2026-07-04); `_date_verified`
  is now expected on new `feeds`/`ats` entries too (ADR-0002). A scheduled re-probe is **deferred**
  (low-stakes — `ingest` already lists dead sources); the verb is run by hand for now.
- Forward-compat scored fields (#197): `ScoredItem` now uses `extra="allow"`, so a relevance-result
  field beyond the known set round-trips into `jobs-scored.json` + the per-lane shortlists instead of
  being dropped on the persist re-write.
- Daily trend granularity — data layer (#187/#188): `trend-snapshot` now also writes
  `public-data/trends-daily.ndjson` (`{date, counts}`), and **weekly is rolled up from the daily buckets**
  (`weekly_from_daily`) so the two series can't disagree; both publish to the `data` branch (aggregate
  keyword-only). The dashboard Week/Day toggle is deferred to #187 (the daily chart needs accrued
  history first).
- Monthly trend granularity — data layer (#188): `monthly_from_daily` rolls the same daily buckets up
  into `public-data/trends-monthly.ndjson` (`{month, counts}`, ~12 records/yr), published alongside
  weekly/daily (the `make trends-data` allowlist is now the single `TRENDS_PUBLISH` variable,
  fail-closed). The dashboard `Monthly` dropdown + same-origin bundle ride with #187 (Wave 3).
- Internal refactor epic (#249): models consolidated into `models.py`; a `defaults.py` + tracked
  `config/keywords.json` single source of truth; `ingest.py` split into `sources.py` / `normalize.py`;
  a fail-closed `TRENDS_PUBLISH` allowlist + trends shrink guard; `app.js` split into an orchestrator
  plus three ES modules — no behaviour change, all gates green.
- Deploy reliability (#251/#252): dropping the `paths:` filter (defeated by the parentless
  `make trends-data` force-push) lets `main` and local `data` pushes redeploy the live same-origin
  trends directly, while the nightly cron **dispatches** the deploy after its push (a `GITHUB_TOKEN`
  push can't self-trigger one) — ending the silent staling (#251); the cron heal (#252) restored the
  scheduled snapshot.
- Relevance fit rubric (#271): the relevance pass now emits an explainable per-offer rationale plus
  `deadline` / `deal_breaker` fields, and `ScoredItem` is typed end-to-end — through persist + the
  merge/refresh re-reads — closing the relevance boundary of ADR-0003.
- Company-hiring trend series (plan 006): `ajoa-kit companies-snapshot` builds a hiring timeline from
  the corpus by `first_seen` — a publishable **geo-by-field** series (`public-data/hiring-*.ndjson`,
  aggregate `{week,counts}`, no company names, on the `data` branch like the keyword trends) plus a
  **local per-company** series (`results/hiring-companies.ndjson`, never published), wired into the
  ingest cron. The local Companies tab also gained a snapshot "as of" date + click-to-sort columns,
  and the dashboard renders both series (geo-by-field top-10 in Market-trends, per-company top-10 in
  the Companies tab) — verified end-to-end by a new `make ui_e2e` (local + remote) harness.
- Location noise-folding (#309): `parse_geo` strips trailing org suffixes (`Office`/`HQ`/`Hub`) and
  maps placeholder junk (`LOCATION`/`N/A`) to `Unknown`, so same-place variants stop splitting the
  Companies-tab ranking and the geo-by-field hiring keys.

## Next

- Daily + monthly granularity in the trends dashboard (#187/#188 UI half: dropdown + same-origin
  bundles; the data layers are shipped).

## Later — hardening & reach

- #71 Vite not adopted — the dashboard stays no-build.
- Data-contract typing (per ADR-0003): a `JobRecord` model + parse-on-read at the JD / tailor
  boundaries, and config-entry models (the `config/lanes.json` lane source and its
  `persist_scored` membership check both shipped, #195). Backlog ranked in the ADR.
- ats-check: wire into the tailor pass (#75); re-evaluate the parse-safety regexes (#77).
- Broaden ingest reach: more JSON aggregators as their robots/ToS clear (jobicy/himalayas/remotive
  — #94 deferred follow-ups). Outlook (#109): slug-discovery from public board directories, and
  keyed aggregators (e.g. Jooble) — both outside the current no-auth/no-key model.
- Trends file growth: aggregated trends are the durable store (on the `data` branch); the JD corpus
  stays git-ignored / ephemeral **by design** (#191, accepted limitation — **closed**; recorded in
  architecture.md §Data layout). The two trend files grow linearly (~23 KB/yr
  weekly, ~130 KB/yr daily) — fine for years (cheap O(n) upsert + whole-file dashboard fetch). If they
  ever get too large, split by month/year (e.g. `trends-YYYY.ndjson`) and have the dashboard fetch the
  needed range.
