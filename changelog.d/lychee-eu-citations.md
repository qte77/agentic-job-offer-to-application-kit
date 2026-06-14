### Changed

- Exclude the EU legal/regulatory citation URLs in `research.md` (eur-lex, EDPB) from the
  lychee link check — they return 403 to CI-runner IPs (bot protection) while resolving for
  humans, which was failing the `links` CI job.
