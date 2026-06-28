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

Accept: `ajoa-kit ingest` → scored `results/<lane>/shortlist.md`, each with a lane, a 0–5 score, and a
one-line rationale.

## US3 — Keep my data private

As a candidate, I want my evidence, inputs, and results kept out of git, so no personally identifiable
information (PII) is ever published.

Accept: `results/`, `library/`, `input/`, and real `config/` files are git-ignored; only
the synthetic `examples/alexis-doe/` workspace is committed.

## US4 — Tailor per offer

As a candidate, I want a tailored CV + cover letter + human-review prefill pack — plus a check of how
well I cover the JD's must-haves — per shortlisted offer, so I apply faster without auto-submitting
anything.

Accept: `cc-workflow-tailor-offer.js` → `ajoa-kit persist-offer` writes
`results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md` (plus `coverage-report.md`,
a must-have / covered-gap / evidence table, when the match returns `must_haves`, #55); `ajoa-kit
ats-check` gates the CV for parse-safety; no automated submission.

## US5 — Tailor in my voice

As a candidate, I want tailored CVs and cover letters written in my own writing style — or a tone I
set — so they read like me rather than a template.

Accept: the user adds CV + cover-letter samples to `config/` (git-ignored); the tailor stage matches
that style, or a configured tone, while the evidence library supplies the facts. See #16.

## US6 — Stay aware of the market passively

As a candidate running an ongoing search, I want a scheduled daily ingest to track the job market over
time without re-running anything by hand, so I can see how demand for my skills trends week over week.

Accept: `.github/workflows/ingest-daily.yaml` runs `ajoa-kit ingest --merge` on a daily cron, folding
each pull into a running `results/corpus.json` (a 4-state dedup-merge stamping `first_seen` /
`last_seen`) and publishing only aggregate, keyword-only trends (`{week, counts}`, no PII) to the
`data` branch for the dashboard. No manual re-run; no JD content leaves the private corpus artifact. See #164.
