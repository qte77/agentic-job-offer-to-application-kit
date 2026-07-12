### Added

- Application-outcome tracker (#273): a new `ajoa-kit status <slug>` verb records how far each
  application has progressed — `stage` (applied → responded → interview → offer/rejected), `date`,
  `notes` — in a local `results/offers/<slug>/status.json`, set and read by hand. Local-only PII
  (git-ignored `results/`), never published; closes the apply→outcome loop the offer packs left open.
