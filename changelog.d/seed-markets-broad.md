### Added

- `src/ajoa_kit/ingest.py`: `from_themuse` adapter — The Muse public job-board API as a second
  broad-lane aggregator (robots-allowed, no-auth 200 with full JD + nested metadata; page-1 + an
  eng-relevant `category` filter). Wired into `AGGREGATORS` + the `aggregators` key in
  `config/default-seed.json`; value-add normalization test (nested `company`/`locations`/`refs`
  flattening + missing-field tolerance).

### Changed

- Market broad-lane ToS research (ADR-0002 + `docs/research.md` + roadmap): The Muse tiered **OK**
  (robots allows `/api/public`); keyed aggregators **Adzuna / Reed / Jooble** stay outside the
  no-auth/no-key model (#109 outlook), and SPA boards (Welcome to the Jungle) are paste-only. No
  clean generic market RSS feed surfaced this round (e.g. jobs.ac.uk `?format=rss` is not RSS).
