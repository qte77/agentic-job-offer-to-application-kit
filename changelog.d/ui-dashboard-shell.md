### Added

- Static, no-build dashboard shell under `ui/` (vanilla HTML/CSS/JS + vendored Chart.js v4.5.1):
  a tailored-shortlist table with filter and a job-market keyword-trends chart, rendering synthetic
  demo data only (no PII). EyeRest brand tokens (zero-blue) with a three-state system/light/dark
  theme. The skeleton for the live trends dashboard (#11); live data-branch wiring stays gated on
  the PII helper (#52) per ADR-0001.
- `make preview` — serve the `ui/` dashboard locally (`PORT` defaults to 8000).
- GitHub Pages deploy workflow (`.github/workflows/gh-pages.yaml`) publishing `ui/` on changes to
  `main` (synthetic data only).
