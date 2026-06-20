### Fixed

- `ingest.html_to_text`: a `>` inside a quoted HTML attribute value no longer truncates the tag
  mid-match — the greedy `<[^>]+>` is now quote-aware. (#98)
- `trend_snapshot.upsert_week`: read the NDJSON log with `split("\n")` instead of `str.splitlines()`,
  which also split on Unicode line separators (NEL/LS/PS) that `json.dumps` leaves unescaped —
  corrupting a record when a week/keyword contained one. Surfaced by the new property test. (#98)

### Added

- Property-based tests (`hypothesis`, added to dev deps in #55) pinning invariants across
  `safe_slug` (path confinement), `canonical_url` (idempotent, strips `utm_`, ingest/persist_scored
  copies stay in lockstep), `build_patterns`, `extract_counts`, `upsert_week`, `html_to_text`,
  `parse_safety_warnings` (monotone), `dedupe`, `render_fields`, and `style.directive`. (#98)
