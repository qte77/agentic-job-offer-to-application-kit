### Changed

- Replace the inlined `lint-md-links` jobs with a call to the org reusable workflow
  `qte77/.github/.github/workflows/lint-md-links.yml` (SHA-pinned), matching `qte77/qte77` — a single
  source of truth instead of a hand-synced mirror. Also git-ignore the `.coverage` data file.
