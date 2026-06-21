### Changed

- `ui/`: reorganized into a `paperverse`-style folder layout (`src/`, `public/`, `tests/`) while
  staying **no-build** — `app.js`/`theme.js`/`style.css` moved to `src/`; `favicon.svg`, `data/`, and
  the vendored `vendor/` (Chart.js + Inter fonts) to `public/`; an empty `tests/` placeholder
  (`.gitkeep`) for parity (no JS test runner — Python modules are the tested surface). `index.html`
  stays at the served root and `gh-pages.yaml` (verbatim `cp -r ui/.`) / `make preview` are unchanged;
  asset paths in `index.html`/`src/*`, the `make trends-ui` target, `.gitignore`, and `NOTICE` were
  repointed accordingly.
