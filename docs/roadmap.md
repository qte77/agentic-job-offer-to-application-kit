# Roadmap

## Shipped — first end-to-end (e2e) happy path

- Evidence-library workflow (`cc-workflow-evidence-library.js`).
- Ingest → chunk → relevance, generic + config-driven (`src/ajoa_kit/`, `cc-workflow-relevance.js`).
- `AppSettings` (pydantic-settings) config + `ajoa-kit` CLI: env-overridable `config/` + `results/`
  paths (no hardcoded `ROOT`), `ingest`/`chunk`/`persist`/`probe` subcommands (ADR-0001 L1/L2).
- Baseline gates: ruff, a value-add `pytest` suite, CodeQL + Dependabot + CI (SHA-pinned),
  markdownlint + lychee.
- Governance, docs, and a synthetic worked example (`examples/alexis-doe/`).

## Next — Stage 3 tailoring

- `cc-workflow-tailor-offer.js`: match → CV + cover letter → ats-check → gap report (strict TDD).
- ats-check: résumé parse-safety + job-description (JD) must-have coverage (#9).
- Delivery: a human-submit prefill pack + a cited ToU/CFAA/GDPR safety note (#8).
- Tailor in the user's own writing style or a set tone, from user CV + cover-letter config inputs (#16).

## Later — hardening & reach

- Per-adapter error/edge handling + full per-adapter and error-branch test coverage.
- Adopt `pseudonymize-text` for shared / trends-dashboard corpora.
- Locale-aware templates (#12); trends dashboard (#11); structured sources catalog (#10).
- Full L1 org-settings apply (branch protection, broader SHA allowlist).
