# ui/ — dashboard shell (demo)

A static, **no-build** dashboard that visualizes the kit's output: a tailored
**shortlist** and **job-market keyword trends**. Vanilla HTML/CSS/JS + vendored
[Chart.js](public/vendor/README.md); same playbook as the `qte77/analyze-stock-kpi`
dashboard.

By default it renders the **synthetic** shortlist from [`public/data/demo.json`](public/data/demo.json)
(fictional companies, no PII). Run **`make preview`** and it shows your **real** shortlist instead,
*locally only*: the per-lane `results/<lane>/shortlist.json` are aggregated into a throwaway,
same-origin `public/data/shortlist.json` that `app.js` (`loadRealShortlist`) loads over the demo set.
That real shortlist is **never committed and never published** — `gh-pages.yaml` bundles none, so the
deployed demo stays synthetic. The **market-trends** chart shows the *real* aggregate series
(`{week, counts}`, non-PII): the published site serves it **same-origin** from
`public/data/trends.ndjson`, which `gh-pages.yaml` bundles from the `data` branch at deploy time
(**never committed into the source `ui/`**). It falls back to fetching this deployment's own `data`
branch at runtime (`raw.githubusercontent.com/<owner>/<repo>/data/public-data/trends.ndjson`,
auto-derived from the Pages origin so every fork self-hosts; `?base=` overrides), then to the
synthetic trends on any miss. The *published* shortlist feed (pseudonymized) stays gated on the PII
helper ([issue #52][i52], [issue #11][i11]) per
[ADR-0001](../docs/decisions/0001-backend-cli-ui-separation.md).

## Layout

A [`paperverse`](https://github.com/qte77/paperverse)-style folder split, kept **no-build** (no
Vite/npm) so the files are served verbatim:

- `index.html` — app shell at the served root
- `src/` — source: `app.js`, `theme.js`, `style.css`
- `public/` — static assets served as-is: `favicon.svg`, `data/demo.json` (synthetic), `vendor/` (Chart.js + fonts)
- `tests/` — folder-parity placeholder; no JS test runner (this repo tests Python modules only)

## Run locally

```bash
# from the repo root — fetch() + ES modules need a real HTTP origin (not file://)
uv run python -m http.server 8000 --directory ui   # or: make preview
# open http://localhost:8000/
```

**Real trends** live on the repo's `data` branch (never in `ui/`). `gh-pages.yaml` bundles them into
the published site at deploy time so the live charts load them **same-origin** (no fragile
cross-origin runtime fetch). Refresh them by generating locally and pushing to that branch:

```bash
uv run ajoa-kit trend-snapshot   # results/jobs-raw.json -> public-data/trends.ndjson (by posted week)
make trends_data                 # push public-data/trends.ndjson -> the `data` branch
```

`make preview` serves a **throwaway copy** of `ui/` with the real trends injected into it (mirroring
the deploy) — so the **local** dashboard shows real data same-origin while the source `ui/` stays
**data-free**. Offline-first: it prefers a local `public-data/trends.ndjson` or `data`-branch ref and only
fetches as a last resort. `?base=<raw-url>` still forces a specific cross-origin source.

`?base=` takes a **raw base URL** — e.g. `https://raw.githubusercontent.com/<owner>/<repo>/<branch>`,
to which `/public-data/trends.ndjson` is appended. To point the dashboard at a different branch or fork,
set the branch segment in that URL (there is no separate `?branch=` switch — the branch lives in the
`?base=` value).

## Design

- **Brand:** EyeRest tokens from `qte77/qte77/brand/DESIGN.md` — warm amber,
  **zero-blue**, as CSS custom properties in [`src/style.css`](src/style.css).
- **Theme:** an `auto` / `light` / `dark` **cycle button** (mirrors the canonical
  `qte77/qte77.github.io` toggle) — applied as `data-theme` on `<html>`, persisted to
  `localStorage`, with an inline `<head>` script preventing a flash of the wrong theme.
  The chart re-reads the tokens on each flip (via a `themechange` event).
- **Fonts:** Inter (400/700) vendored as WOFF2 (with a TTF fallback) under `public/vendor/fonts/`
  (SIL OFL 1.1) with system fallbacks — offline-first, no CDN. Same fonts as the `paperverse` UI.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Shell markup: header (theme toggle + Repo/Issues links), two view tabs (Shortlist table / Market-trends charts) + a trends time-frame picker |
| `src/style.css` | EyeRest tokens (light/dark/auto via `data-theme`) + components + tabs |
| `src/app.js` | Orchestrator (sole `<script type="module">` entry): loads demo/real data, owns UI state (range/lane labels), wires listeners + WAI-ARIA tabs; composes the sibling modules below |
| `src/dom-utils.js` | Shared helpers: `esc`/`safeUrl`/`cssVar`, the `sanitizeHtml` allowlist (the one sanctioned markdown→HTML path), score classing |
| `src/shortlist.js` | Shortlist render + filter + expandable rows (tailored CV + cover letter), copy-to-clipboard packs, vendored-`marked` loader, local real-shortlist fetch |
| `src/trends.js` | Chart.js line + stacked bars with the time-frame window, same-origin→data-branch trends loading, theme-flip invalidation (owns the chart instances) |
| `src/theme.js` | `auto`/`light`/`dark` cycle toggle → `data-theme` on `<html>` (+ anti-flash) |
| `public/data/demo.json` | Synthetic demo data — shortlist (Tab A) + fallback trends as `{week,counts}[]` records (Tab B) |
| *(real trends)* | Not in `ui/` — fetched at runtime from the repo's `data` branch (`public-data/trends.ndjson`); refresh via `make trends_data` |
| `public/favicon.svg` | qte77 brand mark (adaptive light/dark) — same as `paperverse` |
| `public/vendor/` | Vendored Chart.js + Inter font TTFs (see [public/vendor/README.md](public/vendor/README.md)) |
| `tests/` | Folder-parity placeholder (`.gitkeep`); no JS test runner — Python modules are the tested surface |

[i11]: https://github.com/qte77/agentic-job-offer-to-application-kit/issues/11
[i52]: https://github.com/qte77/agentic-job-offer-to-application-kit/issues/52
