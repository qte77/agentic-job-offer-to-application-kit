### Added

- Pre-filter keywords are now runtime-configurable: `config/keywords.json`
  (`{"interest": [...], "title_roles": [...]}`) overrides the hardcoded defaults, so a caller or
  consumer can drive the ingest vocabulary per run without code changes. Absent the file, the existing
  defaults apply (#31).
