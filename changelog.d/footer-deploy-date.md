### Changed

- `ui/` dashboard footer: the "Generated" date is now stamped with the **real gh-pages deploy date**
  (`.github/workflows/gh-pages.yaml` seds it into the published copy at deploy time; the committed
  `#gen-date` value is just the local-preview default). Dropped the "EyeRest brand" and "no PII"
  labels (the synthetic-data note already covers the privacy framing).
