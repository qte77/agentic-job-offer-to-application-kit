### Added

- `src/ajoa_kit/ingest.py`: `from_arbeitnow` adapter + an `AGGREGATORS` dispatch dict for the broad
  no-auth arbeitnow job-board API (the recall lane alongside the curated per-company ATS sources).
  Job `tags` populate the `department` field so the existing word-boundary pre-filter applies with no
  change. Promoted arbeitnow from `_deferred` into a new loaded `aggregators` key in
  `config/default-seed.json`; the ToS §11 backlink is rendered in the dashboard footer (#94, ADR-0002).

### Changed

- `ingest.load_sources` now returns `(feeds, ats, aggregators)` — a third source type per ADR-0001.
