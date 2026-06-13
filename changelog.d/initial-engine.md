### Added

- `src/ajoa_kit/` engine: feed/API-first job-description (JD) ingestion with no-auth
  adapters (Greenhouse, Ashby, Recruitee, Lever, Workable, Personio, RSS), a deterministic
  word-boundary pre-filter, batching, ATS slug discovery, and per-lane shortlist persistence.
- `docs/workflows/cc-workflow-relevance.js`: LLM lane-fit relevance screen over batched JDs;
  reads the evidence library and JD batches at run time.
- Config-driven sources: `config/seed.example.json`, `config/seed-candidates.example.json`
  (real config and all generated data are git-ignored to keep PII out of the repo).
- Baseline conformance: ruff config, a value-add `pytest` suite, CodeQL + Dependabot + CI
  workflows (SHA-pinned), and markdownlint.
- Governance: `LICENSE`, `AGENTS.md`, `CODEOWNERS`.
- A synthetic worked example under `examples/`.

### Changed

- Renamed the Stage-1 workflow to `docs/workflows/cc-workflow-evidence-library.js`
  (the `cc-workflow-*.js` naming convention for Workflow-tool scripts).
