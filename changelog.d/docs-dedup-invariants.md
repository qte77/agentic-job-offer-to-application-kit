### Changed

- Deduplicate the shared invariants to single sources of truth: the git-ignored path list lives
  only in `docs/architecture.md §Data layout` (completed with `library/`/`input/`), the safe/unsafe
  submission boundary only in `docs/research.md §Delivery`, and the default lanes only in the
  `cc-workflow-evidence-library.js` `LANES` array. AGENTS.md, README.md, and SECURITY.md now state
  each rule once and link to its source instead of restating the detail (#57).
