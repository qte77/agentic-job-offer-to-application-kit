### Added

- JD must-have coverage in the tailor pass (#55): the Stage-3 Match agent
  (`cc-workflow-tailor-offer.js`) now returns an optional structured `must_haves` array
  (`{requirement, covered, evidence}`), and `persist_offer` writes a `coverage-report.md`
  (a `Must-have | covered/gap | Evidence` table) into the offer pack when the pack carries it —
  outside the all-or-nothing artifact set, so existing packs are unaffected. New pure
  `ajoa_kit.coverage.coverage_summary` renders the table defensively (escapes pipes, collapses
  newlines, tolerates missing/`None` keys). Adds `hypothesis` (dev) for property-based tests.
