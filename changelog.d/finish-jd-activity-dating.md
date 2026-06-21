### Changed

- Greenhouse adapter dates JDs by their true publish date: `posted_at` = `first_published` (falling
  back to `updated_at`), and records now also carry `last_modified` (= `updated_at`).
  `trend_snapshot.bucket_by_week` gains a `date_of` selector (default `posted_at`) enabling
  activity-dating (`last_modified` ∨ `posted_at`).

### Fixed

- ats-check monotonicity property test now newline-joins its inputs — the table/HTML detectors are
  line-anchored (`^…$`), so bare concatenation could merge two lines and erase a match (flaky test).
