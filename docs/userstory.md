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

Some postings no adapter can reach — published behind a JS accordion, a login, or a page with no
feed. Capture those by hand into `config/manual-jds.json`; `ingest` injects them into every pull, so
they are screened alongside everything else and survive later pulls rather than being dropped as
delisted.

Beyond the seeded ATS/feeds, two read-only **discovery** adapters widen reach without a login:
`ajoa-kit discover-yc` follows the yc-oss hiring feed to public YC company job pages
(`results/yc-jobs.json`), and `ajoa-kit discover-slugs` mines a filtered startups.gallery page for new
first-party ATS slugs to add to the seed (`results/emerging-slugs.json`) — both CAUTION-tier,
public-GET-only, local-only (ADR-0004 Phase 2).

## US3 — Keep my data private

As a candidate, I want my evidence, inputs, and results kept out of git, so no personally identifiable
information (PII) is ever published.

Accept: `results/` (now **exclusively PII**), `library/`, `input/`, and real `config/` files are
git-ignored and **never published**; the only data that crosses to the public `data` branch is the
PII-free keyword aggregates in `public-data/` (#210). Only the synthetic `examples/alexis-doe/`
workspace is committed.

## US3b — See my real shortlist locally

As a candidate, I want the dashboard to show my **real** shortlist when I run it locally (not just the
synthetic demo), while never publishing it, so I can review and filter my actual matches in one place.

Accept: `make preview` aggregates `results/<lane>/shortlist.json` into a throwaway, same-origin file
that `app.js` loads (`loadRealShortlist`); it is never committed, and `gh-pages.yaml` bundles no
shortlist, so the deployed demo stays synthetic. Expanding a row reveals the tailored CV + cover
letter for offers you've tailored — `build_ui_shortlist` joins `results/offers/<slug>/` to the row by
JD id (#209).

## US4 — Tailor per offer

As a candidate, I want a tailored CV + cover letter + human-review prefill pack — plus a check of how
well I cover the JD's must-haves — per shortlisted offer, so I apply faster without auto-submitting
anything.

Accept: `cc-workflow-tailor-offer.js` → `ajoa-kit persist-offer` writes
`results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md` (plus `coverage-report.md`,
a must-have / covered-gap / evidence table, when the match returns `must_haves`, #55); `ajoa-kit
ats-check` gates the CV for parse-safety; no automated submission. After applying, `ajoa-kit status
<slug> --stage applied/responded/interview/offer/rejected` records the outcome in a local
`results/offers/<slug>/status.json` (git-ignored PII), closing the apply→outcome loop (#273).

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

Running `ingest --merge` also writes a local "what changed today" digest to `results/daily-summary.md`
(new/changed/unchanged/delisted counts + new offers). Because it names companies/titles it stays
**local-only** — never uploaded by CI or pushed to a branch (#175).

## US7 — Keep my shortlist current

As a candidate revisiting my search over time, I want offers that have been filled or closed flagged
(or removed) from my shortlist, so it reflects what is still open instead of going stale.

Accept: `ajoa-kit refresh [--lane <name>]` re-checks each `results/<lane>/shortlist.json` entry against
the corpus `delisted` state and a read-only URL re-probe; dead offers are flagged `stale` by default
(kept as an audit trail, hidden from the dashboard) or removed with `--delete`; an inconclusive probe
(network error / timeout) never flags a live entry; `--dry-run` previews. See #214.

The inbound complement keeps it current from the other side: `ajoa-kit chunk --new` → `persist --merge`
screens the offers new or changed in the latest pull into the existing shortlists (union by `id`, no
clobber) instead of re-running the whole screen. See #226/#235.

## US8 — Cover every strong match automatically

As a candidate with shortlists growing across several lanes, I want every score-5 (or however I set
the bar) offer to get a tailored pack without me tracking which ones I've already done, so a strong
match never quietly falls through the cracks.

Accept: `ajoa-kit pack-plan --min-score 5 --json` selects every shortlist row a
[`config/pack-policy.json`](decisions/0005-pack-coverage-policy.md) policy targets (score/lane/dedup/
per-company-cap, CLI flags override the file) and writes `results/pack-plan.json` — exactly the ids
still missing a pack. Looping tailor + `persist-offer` over that list, then re-running `pack-plan`,
reports `missing: []` once coverage is complete; re-running any time after is a no-op for ids already
tailored (idempotent). See ADR-0005.

## US9 — Open my shortlisted offers without hunting each one down

As a candidate ready to apply, I want the kit to open each selected offer's application page in my
own browser, so I don't have to copy-paste URLs one at a time out of the shortlist before applying.

Accept: `ajoa-kit open-offers [--min-score N] [--lanes L1,L2] [--dry-run]` selects offers the same
way `pack-plan` does (reusing `PackPolicy`/`select()`) and opens each one's URL via stdlib
`webbrowser.open` — the human's own already-configured default browser, with zero automated
interaction with the target site. See #417.

Two further tiers were designed — locating and highlighting an offer's form fields, then scripting
candidate values into them (never submitting) — but were **deferred**: any headless-browser
interaction with a real ATS form, even read-only field-location, carries a bot-detection /
account-flagging risk to the candidate's own application. See
[`docs/plans/012-tiered-apply-prefill.md`](plans/012-tiered-apply-prefill.md)'s "Scope change"
section for the full reasoning.
