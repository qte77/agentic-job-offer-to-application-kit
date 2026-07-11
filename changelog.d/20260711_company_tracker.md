### Added

- Local-only company-hiring tracker (#284): a `make preview`-only dashboard tab shows who's hiring
  by location × field with per-company active-role counts and an optional heating/cooling momentum
  tag (dormant until the corpus history spans ~4+ weeks). Aggregation + lossless location parsing
  live in the new tested `ajoa_kit.companies` module; `scripts/build_ui_companies.py` builds the
  view from `results/corpus.json`. Business data stays local — never written to source `ui/`, never
  on the `data` branch — so the tab stays hidden on the published site.
