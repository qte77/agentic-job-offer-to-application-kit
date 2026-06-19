### Changed

- `ui/`: vendored the Inter font (Regular/Bold TTF, SIL OFL 1.1) under `ui/vendor/fonts/` with
  `@font-face` (offline, no CDN) and switched the body stack to `"Inter", system-ui, …` — the same
  fonts as the `paperverse` UI; replaced the favicon with the shared qte77 brand mark (from
  `paperverse`); and constrained the header and footer to the same `max-width` as the content column.
  `NOTICE` now reproduces the Inter OFL (also shipped at `ui/vendor/fonts/OFL.txt`).
