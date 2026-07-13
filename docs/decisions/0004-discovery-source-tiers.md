# ADR-0004 — Discovery-source tiers (emerging-company signal)

**Status:** Accepted (2026-07-13)

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
- Partially reopens the ADR-0002 slug-discovery deferral: this reads a public directory to derive
  *company signal*, not to auto-derive ATS board tokens — the latter stays deferred (ADR-0002 §Out of scope).

## Out of scope (own follow-on slices)

- ATS-slug resolution for discovered companies (name→slug probe already exists in `slug_probe.py`; wiring
  discovery into it is a later slice).
- A second discovery source; publishing any discovery output (forbidden by the boundary above).

## References

- [ADR-0002](0002-source-tos-tiers.md) — source ToS/ToU tiers this extends; §Out of scope slug-discovery note.
- [ADR-0001](0001-backend-cli-ui-separation.md) — four-layer split + PII/business-data boundary.
- Issue #292 (discovery), #284 (consumer — company-hiring tracker).
