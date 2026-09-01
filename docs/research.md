# Research — agentic-job-offer-to-application-kit

Research dimensions the design relies on. A run produces the candidate-specific
instances (positioning, matched offers) in `results/`; this doc stays generic.

## Portfolio positioning

Stage 1 extracts the account's *through-line* — its real center of gravity — from
the project repos (and an optional profile README), then frames all evidence in
that voice rather than as a scattered skills list. Output: a one-line headline, a
positioning summary, skill clusters, and a positioning paragraph per target lane,
each honest about gaps. An adversarial verification pass (keep / downgrade / drop)
keeps every bullet defensible. For breadth-heavy portfolios, the framing reads
breadth as architectural range (one pattern applied across domains), not "jack of
all trades".

## Target lanes

Lanes are configurable. Example set: CxO (fractional CTO / advisor), founding
engineer, software engineer (senior IC), cloud / DevOps / platform, software /
systems architect — each with an honest gap note.

## Fetching (web-access layer)

- **Native WebFetch** takes only url + prompt — no custom headers — so it cannot
  pass header/UA-based blocks; a UA swap alone fails against TLS/JA3 fingerprinting.
  On JS SPAs it returns only an HTML shell. **WebSearch** returns links, not content.
- So the layer uses native tools first (WebSearch to discover, WebFetch to fetch)
  and **falls back to — or is replaced by — polyfetch**: tier-1 (httpx) already
  beats some 403s; tier-2 (curl_cffi) impersonates a real browser TLS handshake;
  tier-3 (headless) renders JS.
- Prefer a **feed/API over rendering**: job boards are typically SPAs, but often
  publish an RSS/Atom feed or call a backend JSON API discoverable in the page's
  JS bundle — far lighter and more ToS-aligned than a headless browser. **Paste**
  is the always-available fallback.

## Market / boards

Job sources grouped by **type**, region-agnostic — fill the specific per-region list at deployment
(in `config/seed.json`, not here). Most boards are JS SPAs, so apply the fetching strategy above
(feed/API first, **paste** fallback). Where a board is powered by a public ATS, prefer the no-auth
endpoints in the §ATS feed/API endpoints table over scraping the board; sources that publish an
RSS/Atom or JSON feed are the cheapest to ingest and are flagged below.

| Type | Representative sources (examples — fill per region) | Ingest path |
| --- | --- | --- |
| General tech | LinkedIn Jobs, Indeed, Glassdoor, Dice, Built In | SPA → paste; LinkedIn/Indeed automation is ToS-barred on their own platforms (see §Delivery) — paste only |
| Startup | Wellfound, Y Combinator "Work at a Startup", `startup.jobs` | SPA → paste; most listings are Greenhouse/Ashby/Lever ATS-backed → use the §ATS endpoints |
| AI / ML | `ai-jobs.net`, ML-focused boards, lab/company career pages | `ai-jobs.net` publishes a feed; lab pages are usually ATS-backed (§ATS); else SPA → paste |
| Remote-first | RemoteOK, We Work Remotely, Remotive, Working Nomads | Feed/API-first — these expose RSS/JSON feeds (cheap tier-1 ingest) |
| Research / RSE | `jobs.ac.uk`, EURAXESS, HigherEdJobs, Society of RSE board | RSS/Atom feeds common (feed-first); some institutional pages SPA → paste |
| Executive / fractional | Toptal, Catalant, Chief, Go Fractional, Continuum | SPA, mostly login-gated → paste |
| Co-founder / VC / accelerator | YC "Work at a Startup", VC talent-network boards (Getro / Consider-powered), CoFoundersLab | Getro/Consider boards often expose a JSON API (feed-first); YC SPA → paste |
| Aggregators | arbeitnow + The Muse (adopted); Adzuna, Reed, Jooble, Google Jobs | arbeitnow + The Muse are no-auth + robots-allowed → shipped under the `aggregators` key (ADR-0002); Adzuna/Reed/Jooble have public APIs but are **keyed + commercial** (out of the no-auth/no-key model, #109 outlook); Google for Jobs has no candidate-side listings API — blocked; others SPA → paste |

Verify any source before relying on it — board APIs, feeds, and terms change. The authoritative
ToS/ToU tier classification for shipped sources is [ADR-0002](decisions/0002-source-tos-tiers.md).

## ATS feed/API endpoints (no-auth)

The ingest layer (`src/ajoa_kit/sources.py` adapters, orchestrated by `ingest.py`) pulls job descriptions from public,
no-auth feed/API endpoints — company slugs come from `config/seed.json`, never
hard-coded; each adapter yields one normalized record shape. Parsing is stdlib-only
(`json` + `xml.etree`, `defusedxml` when available); polyfetch is the default fetcher
(feed/JSON resolves on tier-1 httpx, so the anti-bot fallback chain is rarely needed).

| Source | Endpoint pattern |
| --- | --- |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true` |
| Ashby | `api.ashbyhq.com/posting-api/job-board/<slug>` |
| Lever | `api.lever.co/v0/postings/<slug>?mode=json` |
| Recruitee | `<slug>.recruitee.com/api/offers` |
| Workable | `apply.workable.com/api/v1/widget/accounts/<slug>` |
| Personio | `<slug>.jobs.personio.de/xml?language=en` (XML) |
| RSS / Atom | any feed URL |
| Aggregator (arbeitnow) | `www.arbeitnow.com/api/job-board-api` (JSON, multi-employer; backlink per ToS §11) |
| Aggregator (The Muse) | `www.themuse.com/api/public/jobs` (JSON, multi-employer; robots-allowed; attribution per API ToS) |

These are **read-only** public endpoints. Application *submission* is deliberately
out of scope: the kit delivers a human-reviewed pre-fill pack, never an automated
submission.

## ATS

Modern ATS parse both PDF and .docx **if the doc is clean** (single column,
standard headings, no tables / text-boxes / graphics) — layout matters more than
the extension. Default to a clean text-based PDF; keep .docx for older / enterprise
ATS and editable requests; obey the portal. Dense two-column templates (e.g.
Deedy) are for human eyes / direct sends, not ATS portals. No hidden-text /
keyword-stuffing tricks (dishonest, detectable, self-defeating) — use parse-safe
formatting + honest keyword alignment instead.

## Delivery

How a tailored pack reaches the employer. This is a **cited research synthesis, not
legal advice** — for commercial use, have counsel and a GDPR-qualified reviewer check
it. All sources retrieved 2026-06-14; ATS terms and APIs change, so re-verify before
relying on any claim. Tracked in #8.

**Re-verified 2026-09-01** (plan 012, #417): all 8 primary sources below re-fetched and checked
against the specific claims in the Per-platform table and the LinkedIn/Indeed section — every
claim still holds. Two facts updated in this pass: Greenhouse's docs URLs now redirect
`developers.greenhouse.io` → `docs.greenhouse.io` (content unchanged, citations below updated);
Workable's application-question schema, previously "unconfirmed," is now confirmed to need
`r_jobs` Bearer auth (401 without) — same employer-key-gated pattern as Ashby (see the
Residual-uncertainties note below). Nothing found bears on the 2026-09-01 fill-without-submit
addendum either way — no platform has ToS or bot-detection language specific to scripted
field-filling as distinct from submission or scraping.

### The safe / unsafe boundary

- **Safe (what the kit does):** no-auth *reading* of public job-board GET APIs to
  assemble a per-offer pre-fill pack that a **human reviews and submits manually**.
- **Unsafe (out of scope, never automate):** programmatic application *submission*,
  CAPTCHA bypass, RPA, browser autofill/automation extensions, or submitting with an
  employer API key the kit does not legitimately hold.

### Per-platform (verified against primary API docs)

| Platform | Public READ (no auth) | Programmatic SUBMIT |
| --- | --- | --- |
| Greenhouse | Yes — all Job Board GET endpoints; `?questions=true` returns the application field schema, which the docs invite you to use to build your own form | Employer API key (Basic Auth); no candidate-side path |
| Lever | Yes — published postings are public and "may be scraped by third parties" (official README) | Employer key generated by a Super Admin |
| Ashby | Yes — `posting-api/job-board/<slug>` GET needs no auth | `applicationForm.submit` needs an employer key (`candidatesWrite`) |
| Workable | Listing feeds public | `POST /jobs/:shortcode/candidates` needs an employer token (`w_candidates`) |

Across all four, **submission is gated behind an employer-issued key** a candidate
tool cannot hold — there is no unauthenticated candidate-side submit endpoint.

**Application-question schema (the prefill pack's input, #56):** only **Greenhouse** exposes it
unauth (`?questions=true`, which the docs invite you to use). Verified 2026-06-20: **Ashby's** public
`posting-api/job-board/<slug>` GET returns job metadata + an `applyUrl` only (keys: `title`,
`location`, `department`, `descriptionHtml`, `applyUrl`, … ) — **no** embedded form/question schema
(the form renders behind the apply flow). Lever/Workable are submit-key-gated; Recruitee/Personio
unverified. So `prefill.py` fetches the live schema for Greenhouse and falls back to `GENERIC_FIELDS`
for every other ATS.

### LinkedIn / Indeed

Both prohibit automation on **their own** platforms: LinkedIn's User Agreement §8.2
bans "software, devices, scripts, robots ... (such as crawlers, browser plugins and
add-ons ...)" used to scrape/copy or access via unauthorized automation; Indeed's ToS
bans "automation, scripting, or bots to automate the Indeed Apply process" outside its
authorized vendors. Both target their hosted apply flows — **not** reading job data
from third-party ATS APIs that syndicate the same roles. The boundary depends on
*where* data is read, not who posted the role.

### US CFAA (Van Buren, 2021)

The Supreme Court read "exceeds authorized access" narrowly: it does not cover someone
with "improper motives for obtaining information that is otherwise available to them."
Reading a publicly open, no-auth endpoint is therefore not unauthorized access
regardless of motive (hiQ v. LinkedIn, 9th Cir. 2022, and Meta v. Bright Data
reinforce this). Automated *submission* without the employer credentials an endpoint
requires would instead implicate the separate "without authorization" prong — exactly
the line the kit stays behind.

### Residual uncertainties (unverified — do not rely on without checking)

- **Personio, Recruitee:** not verified this cycle; assumed employer-keyed submit by
  pattern. Check their developer docs before trusting either.
- **Workable question schema:** confirmed 2026-09-01 — `GET /jobs/:shortcode/questions` needs
  `r_jobs` Bearer auth (401 without), the same employer-key-gated pattern as Ashby (verified
  2026-06-20 — *not* exposed; see the application-question schema note above). Not fetchable
  without an employer key.
- **Non-US computer-misuse law** (UK CMA 1990; EU Directive 2013/40; DE StGB §202a; CH
  StGB Art. 143bis): no primary-source claims survived verification. These generally
  criminalise access to systems one is *not authorised* to access; reading a documented
  no-auth endpoint is unlikely to qualify, but this is **uncertain** and
  jurisdiction-specific (targets are global).
- **GDPR:** no claim survived verification. A candidate processing *their own* PII in a
  local pack is almost certainly the data subject (own legitimate interest), but
  retention, third-party-data, and controller/processor questions are unverified — get
  a GDPR-qualified review.
- **Third-party autofill tools** (Simplify, LazyApply, Sonara): appear to be
  browser-extension/RPA, not open APIs; documented ban outcomes unconfirmed.
- **Time-sensitivity:** Greenhouse is moving the *employer-side* Harvest API to OAuth
  v3 (Basic Auth deprecated 2026-08-31); the public Job Board API is unaffected.

### Implication for the kit

The kit's design — no-auth READ plus a human-submitted pre-fill pack — sits on the safe
side of every dimension verified above. The Stage-3 `prefill-pack` artifact may assemble
field values (optionally from Greenhouse's public `?questions=true` schema) for human
review and manual submission. It must **never** POST to a submit endpoint, bypass a
CAPTCHA, drive a browser autofill extension, or use an employer key.

### Addendum (2026-09-01) — scoped exception: writing form fields, never submitting

**This is the project owner's deliberate risk decision, not a legal conclusion or new
research finding.** It narrows one line above — "drive a browser autofill extension" —
for one specific action: scripting a *value into a field* on the offer's own real
application form (via `polyfetch-scrape`'s `render_session`), gated by an explicit,
per-action human trigger (a CLI flag or a UI button click — never a standing "autofill
everything" toggle). Everything else in this document's safe/unsafe boundary is
**unchanged and still absolute**: no code path may POST to a submit endpoint, click a
submit control, bypass a CAPTCHA, or act without the human present and reviewing —
those lines are not touched by this addendum.

**Reasoning offered for this narrower exception** (not independently re-verified —
treat as the owner's stated rationale, same evidentiary weight as any other unverified
claim in this document until someone checks it):

- The CFAA analysis above (Van Buren) is specific to *submission* implicating the
  "without authorization" prong; it does not analyze fill-without-submit, so this
  narrower action is not something the research found to be a settled violation — but
  that is a **gap in the analysis**, not a finding that it is safe.
- This is a candidate filling in *their own* application on a page they are
  legitimately visiting to apply, once, on their own initiative and with a click they
  make each time — a different shape of use than a multi-tenant SaaS product driving
  the same forms at scale for many users, which is closer to what LinkedIn's/Indeed's
  automation clauses and most ATS platforms' bot-detection are aimed at.

**What this addendum does NOT resolve** — still open, still genuinely uncertain:

- The "Residual uncertainties" note above — *"Third-party autofill tools (Simplify,
  LazyApply, Sonara)... documented ban outcomes unconfirmed"* — still applies in full.
  Real tools doing exactly this exist and their ToS standing has not been settled by
  anyone verified here; this addendum does not change that.
- Bot-detection heuristics on a target ATS (behavioral analysis, honeypot fields,
  timing checks) can flag or silently corrupt a scripted fill regardless of its legal
  standing — a functional risk to the candidate's own application, separate from and
  in addition to the legal one.
- Any implementation must keep the human-consent gate **per action**, never a batch
  "do this for every offer automatically" mode, and must never let a filled-but-
  unreviewed form auto-advance to submission.

### Primary sources (retrieved 2026-06-14)

- Greenhouse Job Board API — <https://docs.greenhouse.io/job-board.html> (`developers.` redirects
  here as of 2026-09-01)
- Greenhouse Candidate Ingestion API — <https://docs.greenhouse.io/candidate-ingestion.html>
  (`developers.` redirects here as of 2026-09-01)
- Ashby public posting API — <https://developers.ashbyhq.com/docs/public-job-posting-api>
- Ashby `applicationForm.submit` — <https://developers.ashbyhq.com/reference/applicationformsubmit>
- Lever Postings API — <https://github.com/lever/postings-api>
- Workable API — <https://help.workable.com/hc/en-us/articles/115013356548-Workable-API-Documentation>
- LinkedIn User Agreement §8.2 — <https://www.linkedin.com/legal/user-agreement>
- Indeed Terms of Service — <https://www.indeed.com/legal>
- Van Buren v. United States, 593 U.S. 374 (2021) — <https://www.supremecourt.gov/opinions/20pdf/19-783_k53l.pdf>
- EU Directive 2013/40/EU — <https://eur-lex.europa.eu/eli/dir/2013/40/oj/eng>
- UK Computer Misuse Act guidance (CPS) — <https://www.cps.gov.uk/legal-guidance/computer-misuse-act>
- EDPB legitimate-interest guidelines (2024) — <https://www.edpb.europa.eu/system/files/2024-10/edpb_guidelines_202401_legitimateinterest_en.pdf>

## Reference pattern

`agentic-market-research-to-gtm`: `config(sources, targets) -> multi-phase agentic
pipeline -> results`, with shared subagent guidelines and dual-mode / validation
ceremony. This concept reuses the skeleton and modernizes the engine (the Workflow
tool) while dropping the ceremony (KISS / YAGNI).

## Common gaps to address (narrative, once)

Solo / open-source portfolios often lack verifiable employment history, team-scale
work, or production-at-scale ops. The gap narrative addresses such gaps honestly
once and reuses them across applications — not patched per offer.

## Writing style / tone

Own-voice or set-tone CV / cover-letter writing (a sample wins over a `tone` string, which wins over
a neutral default) is a shipped Stage-3 feature; its configuration (`config/style.json`) and usage
(`ajoa-kit style`) live in [quickstart §Writing style](quickstart.md#writing-style-optional).
