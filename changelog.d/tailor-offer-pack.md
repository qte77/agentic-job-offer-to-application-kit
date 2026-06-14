### Added

- Stage-3 tailor pass (first vertical slice): `docs/workflows/cc-workflow-tailor-offer.js`
  turns one shortlisted offer into a per-offer application pack (match → tailored CV → cover
  letter → gap report), grounded in the evidence library. The companion `persist_offer` module
  (and `ajoa-kit persist-offer` subcommand) validates the returned pack and writes
  `results/offers/<slug>/{match,cv,cover-letter,gap-report}.md`, with the offer slug sanitized
  to a confined path segment. Pre-fill + human submit only — no auto-apply; the `ats-check`
  (#9) and `prefill-pack` (gated on the ToU/CFAA/GDPR verification, #8) artifacts are deferred.
