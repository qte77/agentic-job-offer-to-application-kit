# ADR-0004 — Discovery-source tiers (emerging-company signal)

**Status:** Accepted (2026-07-13); amended 2026-08-22 (Phase 2 — discovery → JDs + ATS slugs; see Amendment)

**Relates to:** [ADR-0002](0002-source-tos-tiers.md) (the OK/CAUTION/BLOCKED ToS/ToU tiering this ADR
extends to the discovery layer, and whose "slug-discovery … deferred" out-of-scope note this partially
reopens); [ADR-0001](0001-backend-cli-ui-separation.md) (the four-layer split + the PII/business-data
boundary); [architecture.md §Data layout](../architecture.md#data-layout). Issue #292; consumer #284.

## Context

Issue #292 adds a curated **discovery layer**: read a public source, extract **company names**, and derive an
**emerging / who's-hiring** signal that feeds the company-hiring tracker (#284). This is distinct from
ingest — the sources are not ATS/feed endpoints, and the `sources.load_sources` loader reads only
`feeds` / `ats` / `aggregators`, so a new top-level **`"discovery"`** seed key is inert to ingest.

Two things narrow the ToS/ToU bar below ingest's (ADR-0002):

- **Aggregate-only.** We derive **non-copyrightable facts** (company name, YC batch, hiring flag —
  *Feist*), never a source's listings, JD text, or newsletter body. Facts/aggregate stats are
  transformative; a source's copy is not reproduced.
- **Local-only.** The output names companies → **business data** → written to
  `results/emerging-companies.json` and **never published**. The `make trends_data` fail-closed
  allowlist (`TRENDS_PUBLISH`) would refuse it on the `data` branch anyway.

The non-negotiables from ADR-0002 still hold: **read-only public GET, no auth/login bypass**, respect
robots, no PII, and every source is tiered + reachability-verified before wiring.

## Decision

**Phase 1 ships exactly ONE source, tiered on *reading to aggregate*, not *reproducing*.** The
per-source tiers for the candidate set (issue #292 "sources to evaluate"):

| Tier | Source | Rationale |
|---|---|---|
| **OK (shipped)** | **yc-oss** — `yc-oss.github.io/api/companies/hiring.json` | Community mirror of YC's public directory (provenance: YC's public Algolia index), static JSON on **GitHub Pages** — `github.io` robots allows `/`; read-only no-auth GET. Carries `name` + `batch` + `isHiring` per company in one GET. Repo has no LICENSE → we take **non-copyrightable facts only** (*Feist*), locally. Reachability-verified 2026-07-13. |
| **CAUTION (not shipped)** | Official **api.ycombinator.com** company API | First-party and richer, but its `robots.txt` is a blanket `Disallow: /`. Tiering it OK would contradict the ADR-0002 **jobicy** precedent (robots `Disallow:/api` → CAUTION). The yc-oss mirror gives the same facts robots-clean, so the mirror is preferred. |
| **BLOCKED** | YC **Work at a Startup** job board | Login-walled — reading it needs an authenticated session, which the read-only-public-GET rule forbids. Excluded. |
| **Deferred** | Harmonic Hot25, Ramp reports, a16z Build / Next Play / Early Day / Founders-You-Should-Know newsletters | Prose sources: company-name extraction from newsletter bodies is unreliable for a deterministic extractor, and several are newsletters/paywalled. A second source is added only if the phase-1 value proves out. |

**Distillation caveat (2026-07-12).** Discovery is **personal-tool utility, not a differentiator** — the
red-team killed trend/discovery *breadth* as a moat. Kept deliberately small (one source); do **not**
expand to chase "market intel."

## Consequences

- One `"discovery"` entry in `config/default-seed.json` (yc-oss), carrying `_date_verified` + a
  free-text `_tos`. Inert to ingest (loader ignores the key).
- `ajoa-kit discover` writes `results/emerging-companies.json` (`{company: {name, sources, batch, hiring,
  in_corpus}}`), joined to the local corpus by a normalized company key. **Never published** — the
  business-data boundary is structural (the `trends_data` allowlist + this ADR), not just convention.
- Adding a second source requires the same tiering + reachability-verify pass recorded here.
- Further candidates evaluated 2026-07-14 (startups.gallery, HN "Who is hiring?", Wellfound, Crunchbase,
  hnhiring.com, breakout-startup newsletters) are recorded **per-source** in `config/default-seed.json`
  `_blocked` / `_deferred` (tagged `_kind: "discovery"`) so they are not re-researched — the seed is the
  machine-readable list; this ADR narrates only the shipped decision. Bottom line: **none cleared the bar;
  the HN Algolia API is the sole phase-2 lead** (public/no-auth but needs free-text extraction).
- Partially reopens the ADR-0002 slug-discovery deferral: this reads a public directory to derive
  *company signal*, not to auto-derive ATS board tokens — the latter stays deferred (ADR-0002 §Out of scope).

## Amendment — Phase 2 (2026-08-22): discovery → JDs + first-party ATS slugs

Phase 2 promotes two slices the phase-1 "Out of scope" list deferred, because both proved reachable
**read-only without a login** (unlike the WaaS board) and both keep the phase-1 boundary (read-only
public GET, local-only output, never published, tiered). The "kept small / not a market-intel moat"
caveat still holds — this is personal-tool *reach* with a human in the loop, not breadth-as-a-moat.

| Tier | Source | Rationale |
|---|---|---|
| **CAUTION (shipped)** | **yc-oss → public YC JDs** (`ajoa_kit.yc_jobs`, `ajoa-kit discover-yc`) | Follows the yc-oss `hiring` flag to each company's PUBLIC `ycombinator.com/companies/<slug>/jobs` page. YC `robots.txt` disallows `/companies?*` (query URLs) but **not** the clean `/companies/<slug>/jobs` path, so a read-only GET of that path is permitted. Emits normalized JD records (`yc:<slug>:<jobid>`) to local-only `results/yc-jobs.json`. Reachability + structure verified 2026-08-22. |
| **CAUTION (shipped)** | **startups.gallery** (`ajoa_kit.startups_gallery`, `ajoa-kit discover-slugs`) | A second discovery source **and** ATS-slug resolution. Broader than yc-oss (non-YC startups too); `robots.txt` is `Allow: /` but there is no published ToS (**absence ≠ permission**), so read-only public GET only, patchright-rendered. Cards link straight to the company's own ATS, so it is used to recover **first-party `(ats, slug)` refs** (ashby/greenhouse/lever) → local-only `results/emerging-slugs.json`, **human-reviewed before any seed change** — discovery *into* first-party ingest, not terminal scraping. |

Both stay **inert to ingest** (no loaded seed key); they are explicit, filter-driven CLI subcommands.
The pure parse/select/derive logic is offline-testable; the network fetch/render lazy-imports
`polyfetch_scrape`. YC **Work at a Startup** stays **BLOCKED** (login-walled) — Phase 2 does not touch it.

## Out of scope (own follow-on slices)

- Auto-adding discovered `emerging-slugs.json` refs to the seed (stays human-reviewed by design).
- Publishing any discovery output (forbidden by the boundary above).

## References

- [ADR-0002](0002-source-tos-tiers.md) — source ToS/ToU tiers this extends; §Out of scope slug-discovery note.
- [ADR-0001](0001-backend-cli-ui-separation.md) — four-layer split + PII/business-data boundary.
- Issue #292 (discovery), #284 (consumer — company-hiring tracker).
