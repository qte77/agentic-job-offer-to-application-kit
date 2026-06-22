### Changed

- docs: synced the docs with this iteration's shipped features. Corrected the README's stale
  "trends fetched at runtime / never bundled into `ui/`" wording (now: bundled **same-origin** at
  deploy + the Pages deploy re-runs on `data`-branch pushes), and reflected the dashboard UX
  (expandable CV/cover-letter rows, market-trends time-frame picker, Repo/Issues header links,
  throwaway-copy `make preview`) and the issue-triage CI across `README.md`, `docs/architecture.md`,
  `docs/roadmap.md`, and `ui/README.md`; noted #54's attempted-then-reverted rulesets in the roadmap.
