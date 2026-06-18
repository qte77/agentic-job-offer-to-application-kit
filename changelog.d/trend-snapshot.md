### Added

- `ajoa-kit trend-snapshot` — derives an aggregate, **keyword-only** per-ISO-week frequency record
  from `results/jobs-raw.json` into `results/trends.ndjson` (document frequency over the
  config-driven keyword vocabulary; no JD text/company/title/url/per-posting rows). Keyword-only by
  construction, so it clears the ADR-0001 PII gate. Foundation for the trends dashboard (#11) and the
  run-with-keywords workflow (#79).
