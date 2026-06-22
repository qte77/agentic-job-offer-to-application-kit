### Changed

- Docs: documented the dashboard's runtime trends source switch — `?base=<raw-url>` takes a branch-
  bearing raw base (no separate `?branch=`; the branch lives in the `?base=` value) — and added the
  previously-undocumented CLI flags (`chunk --batch-size`, `persist-offer --slug`, `prefill-fields
  --ats/--slug/--job-id`) to the README; added `trend-snapshot` to the ADR-0001 subcommand list.
