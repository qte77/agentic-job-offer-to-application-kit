### Added

- `verify-sources` now re-probes the seed's `aggregators` and `discovery` entries as well, so
  every source can have its `_date_verified` refreshed (144 covered, up from 141 — `feeds` + `ats`
  only). `discovery` entries are probed by their `url` like a feed; `aggregators` carry none, so
  each one's fixed endpoint moved into `sources.AGGREGATOR_ENDPOINTS` — a single constant shared by
  the adapter and the probe. Their multi-line entries are re-stamped surgically (only the
  `_date_verified` value is substituted), so the long `_tos` prose blocks stay byte-identical, and
  the parse-back guard that refuses to write a corrupt seed now covers all four sections.

### Fixed

- `verify-sources` never moves a `_date_verified` backwards: a sweep dated 2026-07-28 no longer
  overwrites entries an automated probe had already confirmed on 2026-08-01. ISO `YYYY-MM-DD` is
  fixed-width, so the guard is a plain string comparison.
