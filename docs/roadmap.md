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
  cover letter + gap report + human-review prefill pack (`results/offers/<slug>/`). `ajoa-kit ats-check`
  résumé parse-safety (#9); style/tone from `config/style.json` (#16); cited ToU/CFAA/GDPR delivery
  safety note (`research.md` §Delivery, #8).
- Repo hardening: coverage gate (#33), docs-only CI `paths-ignore` (#34), `CONTRIBUTING.md` (#35),
  qte77 badge set (#22), structured board catalog (#10), docs structural-integrity pass (#57), and the
  org reusable `lint-md-links` workflow.
- Keyword-trend pipeline: runtime-configurable pre-filter keywords (`config/keywords.json`, #31);
  `ajoa-kit trend-snapshot` → keyword-only `results/trends.ndjson` (#11 PR-A); reusable
  `run-with-keywords` workflow (#79).

## Next

- Locale-aware document conventions (#12).
- JD must-have coverage in the tailor pass (#55); prefill-pack reach beyond Greenhouse (#56).

## Later — hardening & reach

- Per-adapter error/edge handling + error-branch test coverage (#53).
- Trends dashboard UI (#11 PR-B / #71, keyword-only); `pseudonymize-text` (#52, belt-and-suspenders).
- Full L1 org-settings apply: branch protection, broader SHA allowlist (#54).
- ats-check: wire into the tailor pass (#75); re-evaluate the parse-safety regexes (#77).
