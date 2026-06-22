### Fixed

- ui: the live dashboard now renders the **real** market trends reliably. It previously depended on
  a cross-origin runtime fetch to `raw.githubusercontent.com`, which some networks / browser
  extensions block (`CORS request did not succeed`) — silently dropping the charts to the synthetic
  fallback. `gh-pages.yaml` now bundles the PII-free aggregate trends (`{week,counts}`) from the
  `data` branch into the published site at deploy time, and `app.js` loads them **same-origin**
  first (the `data` branch / `?base=` remain fallbacks; synthetic is the last resort). The
  bundled copy is deploy-only — gitignored, never committed into `ui/`.
