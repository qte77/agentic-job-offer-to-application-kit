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

## Decision

Classify every candidate source into one of three tiers. Only **OK** sources ship in `feeds` / `ats`.

### Tier table

| Tier | Sources | Basis |
| --- | --- | --- |
| **OK — ship/ingest** | Greenhouse, Lever, Ashby, Personio (no-auth public GET board APIs); RSS/Atom feeds (built for consumption); the arbeitnow + The Muse aggregator APIs (robots-allowed, attribution requested) | Documented public endpoints; Lever README states postings "may be scraped by third parties" |
| **CAUTION — keep in `_blocked` / `_deferred`, do not ship** | Recruitee, Workable; JSON aggregators jobicy / himalayas / remotive | API exists but a robots/ToS conflict is unresolved (see per-source) |
| **BLOCKED — never ingest (paste-only or structurally impossible)** | LinkedIn, Indeed, StepStone, jobs.ch, RemoteOK, Google for Jobs | ToS bars automation, robots disallows job/api paths, or there is no public listings API |

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

### Legal backbone

Reading a public, no-auth endpoint is not "unauthorized access" under the US CFAA (Van Buren, 2021;
hiQ v. LinkedIn, 9th Cir. 2022). Aggregate keyword counts are non-copyrightable facts (Feist) —
verbatim JD text is not, which is why the public dashboard ships only aggregate `{week, counts}` data
(ADR-0001 PII gate + #11). Full citations and the submit-side boundary live in
[research.md §Delivery](../research.md#delivery); this ADR does not restate them.

## Consequences

- `config/default-seed.json` `_comment` points here; `_blocked` gains Google for Jobs, and RemoteOK's
  `_reason` is corrected to match the probe (API 200 + attribution; AI-crawlers blocked — not a blanket
  403). Every `_blocked` / `_deferred` entry carries a `_date_verified` stamp (date of the last
  ToS/reachability check). crewai / latticeflow stay `_blocked` via the #96 re-probe, where their
  reasons are verified.
- **Freshness upkeep (#217).** Every `feeds` / `ats` entry now also carries a `_date_verified` stamp
  (previously only `_blocked` / `_deferred` did), and it is **expected on new `feeds` / `ats`
  entries**. `ajoa-kit verify-sources [--dry-run]` re-probes them read-only (no auth) and re-stamps the
  live ones — feeds by a 2xx/3xx GET, ats boards by a live role count via `slug_probe.PROBES` — while
  reporting the rest for manual triage; a one-pass backfill dated all 142 sources (2026-07-04). Running
  it on a schedule is **deferred** (low-stakes: a normal `ingest` run already lists dead sources in its
  summary), so the verb is run by hand for now.
- #94 shipped the **arbeitnow** adapter (loaded `aggregators` key); attribution is recorded in
  config/ADR — the published dashboard emits only aggregate facts, not arbeitnow content, so no
  on-page backlink. jobicy / himalayas / remotive stay `_deferred` pending the robots/ToS resolutions
  above.
- The kit stays **no-auth / no-key**; keyed aggregators are out of model (see Out of scope).

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
