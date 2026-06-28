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
  `ajoa-kit trend-snapshot` → keyword-only `results/trends.ndjson` (#11 PR-A); reusable
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
  keeps real data out of the source `ui/`.
- AI issue-triage CI (`.github/workflows/issue-triage.yaml`): `qte77/gha-issue-triage` (SHA-pinned,
  GitHub Models, zero-secret) auto-labels newly opened issues.
- Data-contract ADR (ADR-0003, #158): maps the typed vs untyped layer boundaries and sets the
  pydantic + JSON-Schema direction with a prioritized hardening backlog (decision only, no code).
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
- Daily trend granularity — data layer (#187/#188): `trend-snapshot` now also writes
  `results/trends-daily.ndjson` (`{date, counts}`), and **weekly is rolled up from the daily buckets**
  (`weekly_from_daily`) so the two series can't disagree; both publish to the `data` branch (aggregate
  keyword-only). The dashboard Week/Day toggle is deferred to #187 (the daily chart needs accrued
  history first), monthly granularity to #188.

## Next

- Locale-aware document conventions (#12).
- Prefill-pack reach beyond Greenhouse (#56).
- Daily granularity in the trends dashboard (#187); monthly trend granularity (#188).

## Later — hardening & reach

- `pseudonymize-text` (#52, belt-and-suspenders) for the live dashboard data feed. #71 Vite not
  adopted — the dashboard stays no-build.
- Data-contract typing (per ADR-0003): a `JobRecord` model + parse-on-read at the JD / relevance /
  tailor boundaries, config-entry models, and a single `config/lanes.json` lane source (backlog
  ranked in the ADR).
- ats-check: wire into the tailor pass (#75); re-evaluate the parse-safety regexes (#77).
- Broaden ingest reach: more JSON aggregators as their robots/ToS clear (jobicy/himalayas/remotive
  — #94 deferred follow-ups). Outlook (#109): slug-discovery from public board directories, and
  keyed aggregators (e.g. Jooble) — both outside the current no-auth/no-key model.
- Trends file growth: aggregated trends are the durable store (on the `data` branch); the JD corpus
  stays git-ignored / ephemeral **by design** (#191). The two trend files grow linearly (~23 KB/yr
  weekly, ~130 KB/yr daily) — fine for years (cheap O(n) upsert + whole-file dashboard fetch). If they
  ever get too large, split by month/year (e.g. `trends-YYYY.ndjson`) and have the dashboard fetch the
  needed range.
