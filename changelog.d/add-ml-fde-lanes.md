### Added

- Two position lanes — `ml` (AI / ML engineer — applied AI, LLM apps, agentic systems) and `fde`
  (forward-deployed / solutions engineer) — bringing the default set to seven.

### Changed

- `cc-workflow-relevance.js` now derives its lane keys from `cfg.lanes` (the runtime single source of
  truth, shared with `cc-workflow-evidence-library.js`) instead of a separate hardcoded list, so
  overriding lanes in one place can no longer silently desync the two workflows.
