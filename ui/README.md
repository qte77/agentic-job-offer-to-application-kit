# ui/ — dashboard shell (demo)

A static, **no-build** dashboard that visualizes the kit's output: a tailored
**shortlist** and **job-market keyword trends**. Vanilla HTML/CSS/JS + vendored
[Chart.js](vendor/README.md); same playbook as the `qte77/analyze-stock-kpi`
dashboard.

This is a **shell**: it renders [`data/demo.json`](data/demo.json) — **synthetic
data only** (fictional companies, no PII). It's the skeleton for the live
job-market trends dashboard ([issue #11][i11]), which will fetch *pseudonymized*
data from a separate `data` branch at runtime — gated on the PII helper
([issue #52][i52]) per [ADR-0001](../docs/decisions/0001-backend-cli-ui-separation.md).

## Run locally

```bash
# from the repo root — fetch() + ES modules need a real HTTP origin (not file://)
uv run python -m http.server 8000 --directory ui
# open http://localhost:8000/
```

## Design

- **Brand:** EyeRest tokens from `qte77/qte77/brand/DESIGN.md` — warm amber,
  **zero-blue**, as CSS custom properties in [`style.css`](style.css).
- **Theme:** an `auto` / `light` / `dark` **cycle button** (mirrors the canonical
  `qte77/qte77.github.io` toggle) — applied as `data-theme` on `<html>`, persisted to
  `localStorage`, with an inline `<head>` script preventing a flash of the wrong theme.
  The chart re-reads the tokens on each flip (via a `themechange` event).
- **Fonts:** Inter (400/700) vendored as TTF under `vendor/fonts/` (SIL OFL 1.1)
  with system fallbacks — offline-first, no CDN. Same fonts as the `paperverse` UI.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Shell markup: header + theme toggle, two view tabs (Shortlist table / Market-trends charts) |
| `style.css` | EyeRest tokens (light/dark/auto via `data-theme`) + components + tabs |
| `app.js` | Shortlist render + filter, tab switching, Chart.js line + bar trends (rebuilt on `themechange`) |
| `theme.js` | `auto`/`light`/`dark` cycle toggle → `data-theme` on `<html>` (+ anti-flash) |
| `data/demo.json` | Synthetic demo data — shortlist (Tab A) + trends as `{week,counts}[]` records (Tab B) |
| `favicon.svg` | qte77 brand mark (adaptive light/dark) — same as `paperverse` |
| `vendor/` | Vendored Chart.js + Inter font TTFs (see [vendor/README.md](vendor/README.md)) |

[i11]: https://github.com/qte77/agentic-job-offer-to-application-kit/issues/11
[i52]: https://github.com/qte77/agentic-job-offer-to-application-kit/issues/52
