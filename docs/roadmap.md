# Roadmap

## Shipped — first end-to-end (e2e) happy path

- Evidence-library workflow (`cc-workflow-evidence-library.js`).
- Ingest → chunk → relevance, generic + config-driven (`src/ajoa_kit/`, `cc-workflow-relevance.js`).
- `AppSettings` (pydantic-settings) config + `ajoa-kit` CLI: env-overridable `config/` + `results/`
  paths (no hardcoded `ROOT`); the subcommand set is in `src/ajoa_kit/__main__.py` (ADR-0001 L1/L2).
- Baseline gates: ruff, pyright, complexipy, a value-add `pytest` suite, CodeQL + Dependabot + CI
  (SHA-pinned), and markdownlint + lychee (local `make docs-lint` + a `lint-md-links` CI workflow).
- Release tooling: scriv changelog fragments under `changelog.d/`.
- Governance, docs, and a synthetic worked example (`examples/alexis-doe/`).
- Stage 3 tailoring (`cc-workflow-tailor-offer.js` + `persist_offer`): per-offer pack — match → CV +
  cover letter + gap report + human-review prefill pack + optional JD must-have coverage report (#55)
  (`results/offers/<slug>/`). `ajoa-kit ats-check`
  résumé parse-safety (#9); style/tone from `config/style.json` (#16); cited ToU/CFAA/GDPR delivery
  safety note (`research.md` §Delivery, #8).
- Repo hardening: coverage gate (#33), docs-only CI `paths-ignore` (#34), `CONTRIBUTING.md` (#35),
  qte77 badge set (#22), structured board catalog (#10), docs structural-integrity pass (#57), and the
  org reusable `lint-md-links` workflow.
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
  FR/UK/IT/US company boards for geographic breadth in `config/default-seed.json`.

## Next

- Locale-aware document conventions (#12).
- Prefill-pack reach beyond Greenhouse (#56).

## Later — hardening & reach

- Per-adapter error/edge handling + error-branch test coverage (#53).
- `pseudonymize-text` (#52, belt-and-suspenders) for the live dashboard data feed. #71 Vite not
  adopted — the dashboard stays no-build.
- Full L1 org-settings apply: branch protection, broader SHA allowlist (#54).
- ats-check: wire into the tailor pass (#75); re-evaluate the parse-safety regexes (#77).
- Broaden ingest reach: more JSON aggregators as their robots/ToS clear (jobicy/himalayas/remotive
  — #94 deferred follow-ups). Outlook (#109): slug-discovery from public board directories, and
  keyed aggregators (e.g. Jooble) — both outside the current no-auth/no-key model.
