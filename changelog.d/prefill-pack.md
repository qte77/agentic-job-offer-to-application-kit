### Added

- Stage-3 `prefill-pack` artifact (#50), completing the per-offer pack. The tailor workflow assembles a
  human-review prefill pack (field → grounded value, `[NEEDS HUMAN INPUT]` where it can't be evidenced)
  written to `results/offers/<slug>/prefill-pack.md`. `src/ajoa_kit/prefill.py` + `ajoa-kit
  prefill-fields` resolve the application-field schema — Greenhouse's public no-auth `?questions=true`
  (the one ATS that exposes it; see research.md §Delivery) or a generic fallback set. Read-only,
  human-submit only — no automated submission, ever.

### Changed

- Docs synced to shipped Stage-3: `roadmap.md` (tailoring moved to Shipped), `architecture.md` (pipeline
  + built-vs-designed), and `userstory.md` (US4/US5 no longer "next").
