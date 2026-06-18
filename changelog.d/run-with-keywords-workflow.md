### Added

- `run-with-keywords` GitHub workflow (reusable `workflow_call` + `workflow_dispatch`) that runs the
  keyword-trend pipeline with a **consumer-supplied** keyword set and emits the keyword-only
  `trends.ndjson` as an artifact. The demo path uses the committed synthetic example corpus (no
  network); output is keyword-only by construction. Lets consumers (gh-pages demo; `ai-agents-research`
  triage) drive the vocabulary per run (#79).
