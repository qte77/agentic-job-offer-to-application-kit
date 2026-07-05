### Changed

- Refactor epic slice C (`#249`): `ingest.py` split into `sources.py` (fetch helpers, the 10
  explicit per-API adapters, `ATS`/`AGGREGATORS`, `load_sources`) and `normalize.py` (record shape,
  HTML/URL normalization, keyword pre-filter), leaving `ingest.py` a slim orchestrator. Zero
  behavior change; `persist_scored`'s deliberate `canonical_url` duplicate now imports the single
  `normalize` source.

### Added

- `make trends-data` **shrink guard** (`#249` slice D): the push aborts when an outgoing trend
  series has fewer buckets than (or is locally absent while present on) the `data` branch — a
  silently-failed restore can no longer wipe accumulated history on the force-push.
  `TRENDS_FORCE=1` overrides for an intentional prune.
