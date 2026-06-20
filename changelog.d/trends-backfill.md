### Changed

- `ajoa-kit trend-snapshot` now buckets each JD by the ISO week of its `posted_at` (epoch
  seconds/milliseconds, ISO-8601, RFC-822) instead of stamping the run week — so a single scrape
  **backfills** a real multi-week `{week, counts}` timeline into `results/trends.ndjson` (JDs with
  no parseable date are skipped and counted). Output stays keyword-only (ADR-0001 PII gate).
  Backfill is survivorship-biased: live boards only expose currently-open postings, so older weeks
  thin out.

### Added

- Dashboard market-trends tab renders the **real** backfilled series from `ui/data/trends.ndjson`
  when present (sorted by ISO week), falling back to the synthetic `demo.json` trends; the
  shortlist stays synthetic. `make trends-ui` copies `results/trends.ndjson` into `ui/data/` for
  local preview (gitignored — live Pages publishing stays on the #11/#52 data-branch track).
