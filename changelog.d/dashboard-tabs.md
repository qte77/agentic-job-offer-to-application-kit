### Added

- `ui/`: two-tab dashboard (#11 PR-B) — **Shortlist** tab (synthetic offers) + **Market trends** tab
  rendering the real aggregate `{week, counts}` keyword timeline as a line chart (per-keyword over
  weeks) and a horizontal bar chart (top keywords, latest week). WAI-ARIA tabs (roving tabindex +
  arrow keys); charts rebuild on theme flip. Vendored Chart.js only — no CDN.
- `src/ajoa_kit/trend_snapshot.py`: `WeekCounts` pydantic model as the single typed contract for the
  publishable `{week, counts}` shape; `upsert_week` now writes through it.

### Changed

- `ui/data/demo.json`: `trends` reshaped from the pivoted `{weeks, series}` to an array of
  `{week, counts}` records (the WeekCounts shape); the JS derives the line/bar shapes at render time.
