# Roadmap

> Sequenced execution plan for the open backlog: [docs/plans/backlog.md](plans/backlog.md).

## Shipped — first end-to-end (e2e) happy path

- Evidence-library workflow (`cc-workflow-evidence-library.js`).
- Ingest → chunk → relevance, generic + config-driven (`src/ajoa_kit/`, `cc-workflow-relevance.js`).
- `AppSettings` (pydantic-settings) config + `ajoa-kit` CLI: env-overridable `config/` + `results/`
  paths (no hardcoded `ROOT`), and the full `ajoa-kit` subcommand set
  (`ingest`/`chunk`/`persist`/`persist-offer`/`ats-check`/`style`/`prefill-fields`/`probe`) (ADR-0001 L1/L2).
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

## Next

- Locale axis: i18n pre-filter keywords (#31) + locale-aware document conventions (#12).
- JD must-have coverage in the tailor pass (#55); prefill-pack reach beyond Greenhouse (#56).

## Later — hardening & reach

- Per-adapter error/edge handling + error-branch test coverage (#53).
- Adopt `pseudonymize-text` (#52) for shared / trends-dashboard corpora; trends dashboard (#11).
- Full L1 org-settings apply: branch protection, broader SHA allowlist (#54).
