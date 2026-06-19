### Added

- `config/default-seed.json` — a tracked, ToS-vetted default source list (49 reachability-probed
  company boards across Greenhouse/Ashby/Lever/Personio + the swissdevjobs RSS feed) so `ajoa-kit
  ingest` works out of the box. `ingest.load_sources` now falls back to it when the git-ignored
  `config/seed.json` is absent; copy + trim the default into `config/seed.json` for your own runs.
  ToS/ToU-blocked platforms (Recruitee, Workable, LinkedIn) are recorded under `_blocked` and never
  loaded. Productizes the job-research `DEFAULT_SEED` model anticipated in ADR-0001 (#10).
