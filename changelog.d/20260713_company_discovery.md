### Added

- `ajoa-kit discover` — a curated startup-discovery layer (#292). Reads one OK-tier public source (the
  yc-oss mirror of YC's directory), extracts company names, and derives an emerging / who's-hiring
  signal joined to the local JD corpus → `results/emerging-companies.json`. Aggregate-only and
  **local-only** (business data, never published); phase-1 single source, ToS-tiered per ADR-0004.
  Feeds the company-hiring tracker (for #284).
