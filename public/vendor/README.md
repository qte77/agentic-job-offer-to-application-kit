# Vendored libraries

Third-party assets are vendored (committed, no CDN) so the dashboard works
offline and on GitHub Pages with no build step.

| File | Library | Version | License |
| --- | --- | --- | --- |
| `chart.umd.min.js` | [Chart.js](https://www.chartjs.org) | v4.5.1 | MIT |
| `marked.esm.min.js` | [marked](https://github.com/markedjs/marked) | v18.0.5 | MIT |
| `fonts/Inter-*.woff2` (+ `.ttf` fallback) | [Inter](https://github.com/rsms/inter) | — | SIL OFL 1.1 |

To update: download the UMD build from the Chart.js release and replace the file
(keep the version table above in sync). `marked.esm.min.js` is the unmodified `lib/marked.esm.js`
distribution build from the matching marked release (`marked@<version>`, e.g. via
`npm pack marked@<version>`), vendored under the `.min.js` name like `chart.umd.min.js`; `app.js`
imports its `marked` named export and sanitizes the output before assigning to the DOM.

Fonts: the `.woff2` files are generated from the vendored `.ttf` via `fonttools`
(`TTFont(path).flavor = "woff2"`); both are committed — modern browsers load the smaller WOFF2
(`format("woff2")` first in the `@font-face` `src`), the TTF is a legacy fallback. `OFL.txt` carries
the SIL OFL 1.1 license + notices.
