### Added

- `ats-check` (#9): a deterministic résumé parse-safety pass — `src/ajoa_kit/ats_check.py` and the
  `ajoa-kit ats-check <cv.md>` subcommand flag ATS-hostile markdown (tables, raw HTML, images,
  hidden HTML comments, missing section headings) and exit non-zero when any is found. Run it over
  a tailored pack's `cv.md`. Parse-safety only; JD must-have *coverage* (semantic) stays with the
  tailor workflow.
