### Added

- `config/default-seed.json`: added the WeWorkRemotely RSS feed to the shipped defaults (ToS: explicit
  aggregated-data clause + attribution; handled by the existing RSS adapter), and a test guarding that
  the shipped default parses and every entry has the required keys.

### Changed

- `config/default-seed.json`: recorded every ToS/ToU-vetted exclusion under `_blocked` (Recruitee,
  Workable, RemoteOK, LinkedIn, Indeed, StepStone, jobs.ch — no public API and/or automation barred) and
  added a `_deferred` registry for public JSON aggregators (arbeitnow, jobicy, himalayas, remotive) that
  need a JSON-feed adapter plus per-source attribution/permission. The loader still reads only `feeds` + `ats`.
