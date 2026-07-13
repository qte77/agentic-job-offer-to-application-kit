### Added

- `ajoa-kit discover` now prints the actionable slice — the top emerging/hiring companies **not yet in
  your corpus**, most-recent batch first — instead of just counts (#292).

### Changed

- `discover` company-name normalization no longer strips brand-meaningful suffixes (`Co` / `Company` /
  `Holdings`), so genuinely distinct companies stop merging onto one key (#292).
- The gap `coverage-report.md` renders upskilling resources only on **uncovered** must-haves; a covered
  must-have shows none, even if the match pass emitted some (#274).
