### Added

- `ajoa-kit verify-sources [--dry-run]` re-probes every `config/default-seed.json` `feeds`/`ats`
  source read-only (no auth) and stamps `_date_verified` on the live ones, reporting the rest for
  manual triage (`#217`). Feeds are confirmed by a 2xx/3xx GET, ats boards by a live role count via
  the existing `slug_probe.PROBES`; an inconclusive probe never re-dates a source. A one-pass
  backfill (2026-07-04) dated all 142 seed sources, and the writer touches only the changed
  `feeds`/`ats` lines (the multi-line `aggregators`/`_deferred` doc blocks stay byte-identical).

### Fixed

- `ScoredItem` now uses `extra="allow"` so a field the relevance workflow emits beyond the known set
  round-trips into `jobs-scored.json` and the per-lane shortlists instead of being silently dropped
  on re-write (`#197`).
