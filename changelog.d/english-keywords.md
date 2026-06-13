### Changed

- Pre-filter keyword lists (`INTEREST` / `TITLE_ROLES` in `ingest.py`) are now English-only —
  the German terms were dropped (their English equivalents already match the same roles).
  Locale-aware / i18n keyword support is tracked in #31.
