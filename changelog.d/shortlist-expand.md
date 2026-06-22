### Added

- ui: shortlist rows are now expandable — click (or focus + Enter/Space) a row to reveal the
  tailored **CV** and **cover letter** for that offer in a detail panel. Demo uses synthetic
  `cv`/`cover_letter` strings (the canonical tailor-pack keys); real packs stay local
  (`results/offers/<slug>/`, gated on #52). Rendered as plain `<pre>` (esc'd, no new deps); a
  follow-up issue tracks an optional lightweight markdown renderer.
