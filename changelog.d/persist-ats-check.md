### Added

- `ajoa-kit persist-offer` now auto-runs the ATS parse-safety check on the tailored CV (#75): when the
  CV trips a warning, `persist_offer` writes a non-blocking `cv-ats-check.md` into the offer pack for
  human review (a clean CV adds no file). Closes the gap where a parse-unsafe CV could ship silently;
  the deterministic check stays in L1 (`ats_check`), so the tailor workflow no longer needs a manual step.
