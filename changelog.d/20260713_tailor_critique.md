### Added

- `tailor-offer` workflow: an optional draft→critique→revise loop over the tailored CV and cover
  letter (`args.critique`, off by default; `args.critiqueRounds` sets the pass count). It trims
  low-relevance, duplicated, unsupported, or keyword-stuffed lines against the evidence library —
  never inventing experience and never hiding an honest gap (#272).
- `persist-offer` now writes an optional `cv-stuffing-check.md` when the tailored CV trips a new
  deterministic keyword-stuffing check (`ajoa_kit.stuffing`) — a non-blocking review aid alongside
  `cv-ats-check.md` (#272).
