# User stories

## US1 — Build evidence once

As a job seeker, I want my portfolio mined into a verified evidence library, so tailoring reuses
proven, honest bullets instead of re-deriving them per application.

Accept: `results/evidence-library.json` with skill clusters, per-project bullets, per-lane angles, and
an honest gap narrative.

## US2 — Find relevant roles without scraping

As a candidate, I want job descriptions (JDs) pulled from public applicant tracking systems (ATS) and
feeds and screened against my target lanes, so I get a ranked shortlist instead of reading hundreds of
postings.

Accept: `scripts/ingest.sh` → scored `results/<lane>/shortlist.md`, each with a lane, a 0–5 score, and a
one-line rationale.

## US3 — Keep my data private

As a candidate, I want my evidence, inputs, and results kept out of git, so no personally identifiable
information (PII) is ever published.

Accept: `results/`, `library/`, `input/`, and real `config/` files are git-ignored; only
`config/examples/` templates are committed.

## US4 — Tailor per offer (next)

As a candidate, I want a tailored CV + cover letter + human-review prefill pack per shortlisted offer,
so I apply faster without auto-submitting anything.

Accept: `results/offers/<slug>/{match,cv,cover-letter,gap-report,ats-check,prefill-pack}.md`; no
automated submission.

## US5 — Tailor in my voice (next)

As a candidate, I want tailored CVs and cover letters written in my own writing style — or a tone I
set — so they read like me rather than a template.

Accept: the user adds CV + cover-letter samples to `config/` (git-ignored); the tailor stage matches
that style, or a configured tone, while the evidence library supplies the facts. See #16.
