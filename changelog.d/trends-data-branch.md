### Changed

- The live dashboard's real **market-trends** data now lives on a dedicated orphan **`data`** branch
  (never in `ui/` or `main`) and is fetched at **runtime** from `raw.githubusercontent.com` —
  mirroring `qte77/analyze-stock-kpi`. `ui/src/app.js` auto-derives the base from the GitHub Pages
  origin (`<owner>.github.io/<repo>` → that repo's `data` branch), so any fork self-hosts its own
  trends; `?base=` overrides for local, with the synthetic `demo.json` fallback on any miss. Replaces
  the `make trends-ui` copy-into-`ui/public/data/` flow with `make trends-data` (push to the `data`
  branch). (#128)
