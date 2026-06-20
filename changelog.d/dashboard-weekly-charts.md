### Changed

- `ui/`: Tab B now shows three weekly views of the `{week,counts}` log — line (keyword frequency over
  weeks) + **vertical stacked weekly bars** (volume + keyword composition per week) + **weekly
  bubbles** (keyword × week, radius ∝ √count). Replaces the previous "top keywords, latest week"
  horizontal bar.
- `ui/index.html`: simplified the footer — dropped the arbeitnow link and the demo-driven `Generated`
  span; the date is now the static site-creation date. Corrected the synthetic-data note to reflect
  that the live page publishes only aggregate `{week,counts}` facts (no pseudonymized per-posting
  data / no #52 gate).
- `config/default-seed.json` + `docs/decisions/0002-source-tos-tiers.md`: arbeitnow attribution is
  recorded in config/ADR for provenance — the published dashboard emits only non-copyrightable
  aggregate facts (Feist), not arbeitnow listings, so no on-page backlink is required.
