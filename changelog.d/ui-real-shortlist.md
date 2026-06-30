### Added

- The local dashboard now shows your **real** shortlist: `make preview` aggregates the per-lane
  `results/<lane>/shortlist.json` (via `scripts/build_ui_shortlist.py`) into the throwaway serve dir,
  and `ui/src/app.js` (`loadRealShortlist`) loads it **same-origin only** over the synthetic demo set.
  PII by construction — never committed, and `gh-pages.yaml` still bundles no shortlist, so the
  published demo stays synthetic.
