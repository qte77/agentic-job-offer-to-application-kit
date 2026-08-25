# ADR-0002 — Source ToS/ToU tiers for ingest adapters

**Status:** Accepted (2026-06-20)

**Relates to:** [ADR-0001](0001-backend-cli-ui-separation.md) (Layer 1 sourcing model + PII gate);
the safe/unsafe delivery boundary in [research.md §Delivery](../research.md#delivery); the shipped
[config/default-seed.json](../../config/default-seed.json) registry (#10). Issues #94 (aggregator
adapters), #95 (this ADR), #96 (company re-probe).

## Context

The kit ingests job descriptions by *reading* public, no-auth board endpoints (ADR-0001 Layer 1).
Which sources are safe to ship in `config/default-seed.json` was a recurring judgement scattered
across `_reason` / `_tos` strings in the seed file and prose in `research.md`. This ADR makes the
tiering explicit and records both the legal backbone and a 2026-06-20 empirical re-verification
(read-only `polyfetch` probes of each API + `robots.txt` + ToS page).

The loader (`sources.load_sources`) consumes **only** `feeds` + `ats` + `aggregators`; `_blocked` and
`_deferred` are documentation, never loaded — so this ADR governs what graduates *into* those loaded
keys.

`config/manual-jds.json` (#364) is **not** a source under this ADR. It holds individual postings a
human read and captured by hand; it is loaded by `ingest.load_manual_jds`, never by
`sources.load_sources`, and adds no adapter, endpoint or recurring poll to the registry. It is the
mechanism for the **paste-only** outcome this ADR already prescribes for BLOCKED sources — not a
fourth tier and not an exemption from the three.

## Decision

Classify every candidate source into one of three tiers. Only **OK** sources ship in `feeds` / `ats`.

### Tier table

| Tier | Sources | Basis |
| --- | --- | --- |
| **OK — ship/ingest** | Greenhouse, Lever, Ashby, Personio (no-auth public GET board APIs); RSS/Atom feeds (built for consumption); the arbeitnow + The Muse aggregator APIs (robots-allowed, attribution requested) | Documented public endpoints; Lever README states postings "may be scraped by third parties" |
| **CAUTION — keep in `_blocked` / `_deferred`, do not ship** | Recruitee, Workable; JSON aggregators jobicy / himalayas / remotive | API exists but a robots/ToS conflict is unresolved (see per-source) |
| **BLOCKED — never ingest (paste-only or structurally impossible)** | LinkedIn, Indeed, StepStone, jobs.ch, RemoteOK, Google for Jobs, Work at a Startup (workatastartup.com) | ToS bars automation, robots disallows job/api paths, or there is no public listings API |

### Per-source findings (read-only polyfetch probes, 2026-06-20)

- **arbeitnow** — *cleanest aggregator.* API is robots-allowed, returns HTTP 200 with
  `x-ratelimit-limit: 5`; ToS §11 asks for a link back to arbeitnow.com when reusing their content.
  Shipped in #94 under the loaded `aggregators` key. The published dashboard emits only aggregate
  `{week,counts}` facts (Feist), never arbeitnow listings, so no on-page backlink is required;
  attribution is recorded in `config/default-seed.json` + this ADR for provenance.
- **The Muse** — public `api/public/jobs` returns HTTP 200 no-auth with full JD + nested metadata;
  `robots.txt` `User-agent: *` disallows only `/api/users*` (**not** `/api/public`). API ToS requests
  attribution (a themuse.com link). Shipped via `from_themuse` (page-1 + an eng-relevant `category`
  filter); aggregate-only `{week,counts}` output reproduces no Muse content (Feist), so no on-page
  backlink is required — recorded in config + this ADR for provenance.
- **jobicy** — open API (`ai-train=yes`, full JD) **but** `robots.txt` `Disallow: /api/` + asks for
  ≤~1 poll/hour + bans redistribution to other aggregators. Robots conflict → CAUTION, not shipped.
- **himalayas** — public `/jobs/api` returns 200 unauthenticated, but the general ToS §30 requires
  *prior written approval* for automated tools; no dedicated API-ToS grant → CAUTION.
- **remotive** — `robots.txt` `Disallow: /api/*`; ToS requires attribution (follow link + name) +
  ≤4 req/day + a 24h delay, with a private *paid* API for heavier use → GATED (deferred).
- **RemoteOK** — JSON API returns 200 with an in-payload notice requiring a *follow* backlink; but
  `robots.txt` blocks `ClaudeBot` / `GPTBot` and declares `ai-train=no` → BLOCKED (AI-crawler-hostile).
- **Google for Jobs** — a search surface, **not** a data source: no public candidate-side listings
  API. The only path is scraping SERPs, which violates Google ToS + `robots.txt` (`Disallow: /search`)
  → BLOCKED.
- **LinkedIn / Indeed** — `robots.txt` disallows `/jobs*` + `/api/*`, and the User Agreement / ToS bar
  automation (see research.md §Delivery) → paste-only, BLOCKED.
- **Work at a Startup (workatastartup.com)** — re-verified 2026-08-25. `robots.txt` is fully
  permissive (`User-Agent: * / Disallow:`, unchanged from the 2026-08-07 finding), but that is only
  half of the test. Two independent grounds land BLOCKED:
  - **Structural.** Unauthenticated access serves one company's roles at a time behind a "Sign up to
    see more" gate — there is no public listings feed to poll, satisfying this ADR's own BLOCKED
    definition ("no public listings API") on its own.
  - **Legal.** Y Combinator's own Terms of Use (`ycombinator.com/legal#tou`, fetched 2026-08-25)
    states verbatim: *"You agree not to...engage in or use any data mining, robots, scraping or
    similar data gathering or extraction methods."* `workatastartup.com/terms` self-titles as
    *"Terms of Use | Y Combinator's Work at a Startup"* and YC's own legal hub lists no separate
    terms document for the product — strong evidence the same ToU governs. **One link in that chain
    is unverified**: `workatastartup.com/terms`'s own page body could not be directly read this
    session (it is client-rendered with no server-side text, and the local headless-Chromium
    reinstall needed to render it failed on `ENOSPC` — disk space, not a site or ToS block). The
    structural ground alone is sufficient for BLOCKED regardless of how that gap resolves.
  - **Hand capture remains available**, unchanged by this finding — a human reading and pasting one
    posting they were entitled to see is governed by conduct, not destination (see below), and this
    is exactly how HumanLayer's `config/manual-jds.json` entry was already captured.
- **Berlin Startup Jobs** (#212, 2026-06-30) — `berlinstartupjobs.com/feed/?cat=engineering-tech` RSS;
  `robots.txt` allows `/feed` (GPTBot/ClaudeBot permitted, 10s crawl-delay); ToS §3.13 acknowledges
  crawlers over public listings (only registered *customers* are barred from extraction scripts).
  OK → shipped under `feeds`.
- **2026-06-30 company batch** (#212) — 52 companies added on already-OK platforms (Greenhouse / Lever /
  Ashby), each re-probed live (200 + roles); no new platform tiering needed. Excluded as not-automatable
  or non-OK: **ai-jobs.net** (no public RSS/Atom/JSON feed — interactive CSV/JSON export only);
  `euremotejobs` / `nodesk` (`ai-train=no`, `ClaudeBot Disallow: /`); `jobs.heise.de` / `jobs.t3n.de`
  (whitelist-only `robots.txt`). High-fit companies reachable only on a non-OK ATS stay paste-only:
  Klarna / Zalando (Workday), Hugging Face / Snyk (Workable), Cognigy (SmartRecruiters), DeepMind
  (Google/Workday).

### Hand capture is bounded by conduct, not by destination

A `config/manual-jds.json` entry may carry only text a human was entitled to read, obtained by a
one-off read-only GET or render of a public page — including driving that page's own disclosure
controls (clicking an accordion open) when that is simply what a reader does. It must never be used
to:

- bypass a login, paywall or rate limit;
- run a recurring or bulk capture over a CAUTION/BLOCKED source — that is an ingest adapter wearing
  a different name, and it belongs in the tier table above;
- redistribute verbatim JD text. `config/` and `results/` are git-ignored and the published
  dashboard emits only aggregate `{week,counts}` facts (Feist), which is what keeps the paste-only
  path safe.

The test is what was done to obtain the text, not which file it landed in.

### Legal backbone

Reading a public, no-auth endpoint is not "unauthorized access" under the US CFAA (Van Buren, 2021;
hiQ v. LinkedIn, 9th Cir. 2022). Aggregate keyword counts — and the geo-by-field hiring counts
(plan 006) — are non-copyrightable facts (Feist); verbatim JD text and per-company breakdowns are
not, which is why the public dashboard ships only aggregate `{week, counts}` data (the per-company
hiring series stays local; ADR-0001 PII gate + #11). Full citations and the submit-side boundary live in
[research.md §Delivery](../research.md#delivery); this ADR does not restate them.

## Consequences

- `config/default-seed.json` `_comment` points here; `_blocked` gains Google for Jobs, and RemoteOK's
  `_reason` is corrected to match the probe (API 200 + attribution; AI-crawlers blocked — not a blanket
  403). Every `_blocked` / `_deferred` entry carries a `_date_verified` stamp (date of the last
  ToS/reachability check). crewai / latticeflow stay `_blocked` via the #96 re-probe, where their
  reasons are verified. `_blocked` also gains `workatastartup` (2026-08-25, plan-010 item 9) — no
  listings feed without auth, and YC's own Terms of Use bars data mining/robots/scraping; the
  plan's own prior "wanted, but opt-in" framing is superseded, since BLOCKED forecloses any adapter
  including one added to a user's personal `config/seed.json` — the sanctioned path stays paste-only
  hand capture under "conduct, not destination" below.
- **Freshness upkeep (#217).** Every `feeds` / `ats` entry now also carries a `_date_verified` stamp
  (previously only `_blocked` / `_deferred` did), and it is **expected on new `feeds` / `ats`
  entries**. `ajoa-kit verify-sources [--dry-run]` re-probes them read-only (no auth) and re-stamps the
  live ones — feeds by a 2xx/3xx GET, ats boards by a live role count via `slug_probe.PROBES` — while
  reporting the rest for manual triage; a one-pass backfill dated all 142 sources (2026-07-04). It now
  runs **monthly** via `.github/workflows/verify-sources.yaml` (`schedule` + `workflow_dispatch`): the
  cron re-stamps the live ones and, when the seed changes, opens a review PR listing any
  dead/unconfirmed slugs to drop or triage. It can still be run by hand for an ad-hoc check.
- #94 shipped the **arbeitnow** adapter (loaded `aggregators` key); attribution is recorded in
  config/ADR — the published dashboard emits only aggregate facts, not arbeitnow content, so no
  on-page backlink. jobicy / himalayas / remotive stay `_deferred` pending the robots/ToS resolutions
  above.
- The kit stays **no-auth / no-key**; keyed aggregators are out of model (see Out of scope).
- **Manual JDs sit largely outside the freshness loop.** They carry no `_date_verified` and
  `verify-sources` never sees them (it walks `feeds` / `ats` only). `refresh` cannot expire them via
  the corpus either — injection keeps `last_seen` at the newest pull date, so `is_delisted` is always
  False. Its URL re-probe is the one channel that can still fire, and only when the entry's `url` is
  the posting itself and the board answers 404/410; a careers-page or empty `url` is never
  provable-gone. **Prefer a role-specific `url` when capturing, and expect to retire a manual posting
  by deleting its entry.**

## Out of scope (future outlook)

- **Slug-discovery** (auto-deriving board tokens from public directories) — such directories are
  unofficial (their own ToS/quality risk) and it stays per-board underneath, so it only moves curation
  from a JSON file to a scraper. Deferred (roadmap outlook), not pursued now.
- **Jooble / Adzuna / Reed** — official APIs, but all **keyed + commercial ToS** (Adzuna covers FR/UK/
  US/IT; Reed is UK), outside the kit's no-auth/no-key model. Outlook only (#109). Welcome to the
  Jungle (FR) and similar SPA boards expose no public no-auth listings API → paste-only.
- **Operational gaps:** `robots.txt` parsing/enforcement in the fetch path, plus a courtesy
  rate-limit / crawl-delay — tracked as open gaps, not yet implemented.

## References

- [ADR-0001](0001-backend-cli-ui-separation.md) — four-layer split, Layer 1 sourcing model, PII gate.
- [research.md §Delivery](../research.md#delivery) — safe/unsafe boundary, per-platform READ/SUBMIT
  analysis, CFAA/GDPR citations, and primary sources (retrieved 2026-06-14).
- [config/default-seed.json](../../config/default-seed.json) — the shipped registry this ADR governs.
- Kit issues #10 (sources catalog), #94 (aggregator adapters), #95 (this ADR), #96 (company re-probe),
  #217 (`_date_verified` backfill + `verify-sources` re-probe verb).
