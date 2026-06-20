### Added

- Per-adapter error/edge tests for the ingest adapters (#53): value-add offline cases for
  greenhouse / ashby / lever / recruitee / workable pinning each adapter's real normalization
  (multi-department joins, location/url fallbacks, `isRemote`/`workplaceType`/`telecommuting` →
  `remote` mapping, Lever's non-list-payload guard, shortcode-vs-id) plus missing/null-field
  tolerance, and a `collect()` warn-and-continue resilience case (one failing source is recorded
  and never aborts the run). The adapters were already tolerant, so no hardening was needed.

### Changed

- Coverage floor (`pyproject.toml` `fail_under`) raised 41 → 58 to lock in the gain from the new
  value-add tests (#33/#53).
