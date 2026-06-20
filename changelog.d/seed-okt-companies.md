### Added

- `config/default-seed.json`: added 11 reachability-probed OK-tier company boards (2026-06-20) —
  Greenhouse: Arize AI, Isomorphic Labs, Recursion; Ashby: Aleph Alpha, Braintrust, Composio, Corti,
  Cursor, Langfuse, Chroma; Lever: Zilliz (#96). Each carries a `_date_verified` stamp.

### Changed

- `config/default-seed.json`: recorded CrewAI + LatticeFlow under `_blocked` — both resolve only on
  Workable, which stays blocked per ADR-0002. sourcegraph / dagger / qdrant probed but resolved on no
  no-auth ATS endpoint, so they were dropped (not added).
