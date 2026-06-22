### Changed

- ci: the Pages deploy now also re-runs on **`data`-branch pushes** (matching `results/trends.ndjson`),
  so `make trends-data` automatically refreshes the live dashboard's trends — no manual redeploy. It
  always checks out the default branch's `ui/`, regardless of which branch triggered it.
