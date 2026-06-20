### Added

- ADR-0002 (`docs/decisions/0002-source-tos-tiers.md`): explicit OK/CAUTION/BLOCKED ToS/ToU tiers for
  ingest sources, the Feist/hiQ/Van Buren legal backbone, and the 2026-06-20 polyfetch-verified
  per-source findings (arbeitnow cleanest; jobicy/himalayas/remotive gated; RemoteOK/Google for Jobs
  blocked). Roadmap notes the aggregator broad lane (#94) and the slug-discovery / keyed-source
  (Jooble) outlook. (#95)

### Changed

- `config/default-seed.json`: block Google for Jobs, correct the RemoteOK `_reason` to match the
  2026-06-20 probe (API returns 200 + attribution notice; AI-crawlers blocked — not a blanket 403),
  point `_comment` at ADR-0002, add a `_date_verified` stamp to every `_blocked`/`_deferred` entry,
  and refresh the `_deferred` `_tos` notes to the verified findings. (#95)
