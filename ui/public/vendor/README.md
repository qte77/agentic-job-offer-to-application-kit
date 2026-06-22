# Vendored libraries

Third-party assets are vendored (committed, no CDN) so the dashboard works
offline and on GitHub Pages with no build step.

| File | Library | Version | License |
| --- | --- | --- | --- |
| `chart.umd.min.js` | [Chart.js](https://www.chartjs.org) | v4.5.1 | MIT |
| `marked.esm.js` | [marked](https://github.com/markedjs/marked) | v18.0.5 | MIT |
| `fonts/Inter-*.ttf` | [Inter](https://github.com/rsms/inter) | — | SIL OFL 1.1 |

To update: download the UMD build from the Chart.js release and replace the file
(keep the version table above in sync). `marked.esm.js` is the unmodified ESM build from the
matching marked release (`marked@<version>/lib/marked.esm.js`, e.g. via `npm pack marked@<version>`);
`app.js` imports its `marked` named export and sanitizes the output before assigning to the DOM.
