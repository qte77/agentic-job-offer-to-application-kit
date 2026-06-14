# Roadmap

## Shipped — first end-to-end (e2e) happy path

- Evidence-library workflow (`cc-workflow-evidence-library.js`).
- Ingest → chunk → relevance, generic + config-driven (`src/ajoa_kit/`, `cc-workflow-relevance.js`).
- `AppSettings` (pydantic-settings) config + `ajoa-kit` CLI: env-overridable `config/` + `results/`
  paths (no hardcoded `ROOT`), `ingest`/`chunk`/`persist`/`probe` subcommands (ADR-0001 L1/L2).
- Baseline gates: ruff, pyright, complexipy, a value-add `pytest` suite, CodeQL + Dependabot + CI
  (SHA-pinned), and markdownlint + lychee (local `make docs-lint` + a `lint-md-links` CI workflow).
- Release tooling: scriv changelog fragments under `changelog.d/`.
- Governance, docs, and a synthetic worked example (`examples/alexis-doe/`).
- Stage 3 tailoring (`cc-workflow-tailor-offer.js` + `persist_offer`): per-offer pack — match → CV +
  cover letter + gap report + human-review prefill pack (`results/offers/<slug>/`). `ajoa-kit ats-check`
  résumé parse-safety (#9); style/tone from `config/style.json` (#16); cited ToU/CFAA/GDPR delivery
  safety note (`research.md` §Delivery, #8).

## Next

- Prefill-pack reach: application-field schemas beyond Greenhouse's public `?questions=true`, and JD
  must-have coverage in the tailor pass.
- Structured job-sources board catalog (#10); locale-aware document conventions (#12).

## Later — hardening & reach

- Per-adapter error/edge handling + full per-adapter and error-branch test coverage.
- Adopt `pseudonymize-text` for shared / trends-dashboard corpora; trends dashboard (#11).
- Full L1 org-settings apply (branch protection, broader SHA allowlist).
- i18n pre-filter keywords (#31); coverage gate (#33); CI `paths-ignore` (#34); `CONTRIBUTING.md` (#35).
