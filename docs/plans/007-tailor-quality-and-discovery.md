# Plan 007 — tailor-quality (#272 critique loop · #274 upskilling pointers) + discovery (#292)

**Status: SHIPPED (2026-07-13)** — S1 #272 (#317) · S2 #274 (#318) · S3 #292 (#319). Three backlog features, two clusters.
Carries a symbol-level source map (verified 2026-07-12, `file:line`) so a resuming session **does not
re-map the codebase**. Handoff:
[docs/handoffs/007-tailor-quality-and-discovery.md](../handoffs/007-tailor-quality-and-discovery.md) — read first.

## Context

Follow-ups after plan 006 shipped (Companies tab, hiring series, `parse_geo` normalization). Three
open issues:

- **#272** — an OPTIONAL drafter→critique→revise `agent()` loop in the tailor pass + an
  anti-keyword-stuffing guardrail. Highest-value *feature* for the core deliverable (the application pack).
- **#274** — extend the existing honest gap report with 1–2 upskilling resource pointers per uncovered
  must-have.
- **#292** — a curated startup-**discovery** layer: read public sources, extract company names, derive
  an emerging-company/who's-hiring signal feeding the #284 tracker. Aggregate-only, local-only.

**Steer from the 2026-07-12 adversarial distillation (`results/adversarial-hn-launch.md`, git-ignored):**
the two tailor features (#272/#274) serve the ICP (a technically-fluent active searcher) → **worth
building**. #292 was **de-prioritized** — it chases trend/discovery *breadth* the red-team killed as a
differentiator. It still has real *personal-tool* value (which startups are emerging/hiring), so it is
planned **scoped to exactly ONE OK-tier source (phase 1), local-only output**, sequenced last, and
explicitly caveated as personal-tool utility (not a differentiator); a second source only if that
value proves out.

## Prioritized slices (ship order — one PR each)

| # | Slice | Cluster | What | Test? |
|---|---|---|---|---|
| **S1 ✅** | #272 critique loop | tailor | optional draft→critique→revise phase (JS glue) + deterministic anti-stuffing detector (Python) — **shipped #317** | **yes** (the pure detector; loop verified live) |
| **S2 ✅** | #274 upskilling pointers | tailor | match pass emits `resources` per uncovered must-have; render in coverage table — **shipped #318** | **yes** (`coverage_summary` extension) |
| **S3 ✅** | #292 discovery (phased) | discovery | new L1 `discover.py` + `discover` verb + `"discovery"` seed key (yc-oss) + per-source tiering; local-only output — **shipped #319** | **yes** (pure extractor/normalizer/signal) |

S1+S2 share the tailor workflow file and may ride one branch if you prefer; kept separate by topic here.

---

## Source map (reuse, don't rebuild — verified 2026-07-12, `file:line`)

### Tailor pass — mirror for #272/#274 (`.claude/workflows/cc-workflow-tailor-offer.js`, 206 lines, L3)

- Invoked via the Workflow tool only (ADR-0001 L3, not a CLI verb):
  `Workflow({ scriptPath: '.claude/workflows/cc-workflow-tailor-offer.js', args: { rootDir, lane, offerId, style?, fields? } })`
  or `Workflow({ name: 'tailor-offer' })`. The "tailor-offer skill" in the env IS this workflow's `meta`.
- **3 phases / 5 `agent()` calls:** `phase('Match')` **106** → 1 agent → `matchSchema` **78–100**
  `{match, must_haves:[{requirement,covered,evidence|null}]}`. `phase('Tailor')` **123** → `parallel([...])`
  **124–166** of 3 agents → `cv`, `cover_letter`, `gap_report` (each fed `${SOURCES}` + the match). The
  **gap agent 154–166** ("for the candidate's eyes, not the employer") is **exactly what #274 extends**.
  `phase('Prefill')` **168** → 1 agent → `prefill_pack` (`[NEEDS HUMAN INPUT]`, no-auto-apply).
- Return **195–205:** `{slug, lane, offer_id, match, must_haves, cv, cover_letter, gap_report, prefill_pack}`.
- **`SOURCES` block 62–67** ("Tailor only to evidence that exists; never invent experience") = the
  grounding the #272 critic checks each line against. CV prompt already seeds anti-stuffing ("NO hidden
  text / keyword-stuffing … Use only evidenced bullets").
- **#272 seam:** a new OPTIONAL phase between `parallel(...)` (ends **166**) and `phase('Prefill')`
  (**168**), gated by `args.critique` — a critic `agent()` over `cv`/`cover_letter` vs `SOURCES`, then a
  revise `agent()`, before prefill consumes `cv.cv`/`cover.cover_letter`. Add a `meta.phases` entry **37–41**.
- **#274 seam:** extend the gap agent prompt (**154–166**) to emit `resources` per uncovered must-have;
  extend `matchSchema` `must_haves` items (**78–100**) with an optional `resources: string[]`.

### Persist + render (Python, L1/L2 — the TDD surface)

- `src/ajoa_kit/__main__.py` **52–56, 179–184** — `persist-offer FILE --slug` → `ajoa_kit.persist_offer.main`.
- `src/ajoa_kit/persist_offer.py` — `ARTIFACTS` **31–37** (pack keys → `{match,cv,cover-letter,gap-report,prefill-pack}.md`);
  `write_pack()` **86–129** validates all-or-nothing, writes `results/offers/<safe_slug>/`, plus **optional
  side artifacts kept OUT of `ARTIFACTS`**: `coverage-report.md` (**110–113**, via `coverage_summary`),
  `cv-ats-check.md` (**114–123**, via `parse_safety_warnings`), `meta.json` (**126–128**). **This optional-6th-artifact
  pattern is what a #272 critique artifact and #274's resources reuse.**
- `src/ajoa_kit/coverage.py` — `coverage_summary(must_haves, gap_report)`: pure, defensive (never raises
  on missing/None), renders a `| Must-have | covered/gap | Evidence |` table + gap body. TDD:
  `tests/test_coverage.py`. **#274 extends this table with a Resources column/line.**
- `src/ajoa_kit/ats_check.py` — `parse_safety_warnings(cv)`: pure parse-safety detector, TDD
  `tests/test_ats_check.py`. **#272's deterministic anti-stuffing detector is a sibling here** (keyword-density
  / repeated-ngram), surfaced as an optional persist artifact like `cv-ats-check.md`.
- No pydantic pack model — the pack "schema" is the workflow's inline JSON schemas (JS-side). Do NOT add one.

### Evidence library (grounding corpus)

- `results/evidence-library.json` (`LIBRARY_PATH`, tailor script **59**); built by
  `.claude/workflows/cc-workflow-evidence-library.js` (Stage-1, `meta.name:'evidence-library'`). Shape:
  `headline, positioningSummary, skillClusters[{cluster,bullets}], masterCvBullets, perProject[...],
  <lane>Angle, gapNarrative, toneApplied`. De-identified example: `examples/alexis-doe/results/evidence-library.json`.
  This is the "genuine OFFERS / honest MISSING" the #272 critic validates against.

### Discovery — build for #292 (new; mirror these, `file:line`)

- **Source config** `config/default-seed.json`: loader `sources.py` `load_sources()` **317–336** reads ONLY
  `feeds`/`ats`/`aggregators`; **keys beyond those are ignored** → a new top-level **`"discovery"`** key is
  invisible to `ingest.main()` (matches "not scrapers in feeds/ats"). Entry precedent (aggregators added as
  a 3rd type, `sources.py:310`). Every entry carries `_date_verified` + a free-text `_tos` (ADR-0002).
- **Fetch glue** `src/ajoa_kit/sources.py`: `get_json()`/`get_bytes()` do `# lazy … from polyfetch_scrape
  import fetch` + SSRF guard (`_is_http`, #256); one `from_*` generator per endpoint; dispatch tables
  `ATS`/`AGGREGATORS`. `ingest.py` `main()` **196–204** loops sources warn-and-continue.
- **Record shape** `normalize.record()` **115–136** emits `company` (plain str, `""` for RSS). Consumer:
  `companies.py` `aggregate_companies()` keys on `company`; `companies_trend.py` `company_key()` skips blanks.
  → **join point = a shared company-name normalizer** (analogue of `parse_geo`/`_CITY_ALIASES`
  `companies.py:26-62`); discovery emits a local aggregate file keyed by normalized company, joined to
  `CompanyRow.company` / `results/hiring-companies.ndjson`. Discovery does **not** inject JD records.
- **Reachability/probe** `slug_probe.py` — `probe` verb (`__main__.py:252`), `PROBES` dict, `fetch_status()`;
  name→ATS-slug resolution for discovered companies.
- **ADR-0002** `docs/decisions/0002-source-tos-tiers.md`: OK/CAUTION/BLOCKED tiers; `_date_verified` +
  `verify-sources` re-probe required before shipping a source. **Slug-discovery was explicitly deferred there**
  → #292 partially reopens it → needs a discovery ADR (0003) or an ADR-0002 amendment recording per-source
  tiering + the YC Work-at-a-Startup login-wall exclusion.
- **Four-layer (ADR-0001):** L1 `src/ajoa_kit/discover.py` — PURE (no net/IO, TDD): `extract_companies(payload,
  fmt)`, `normalize_company(name)`, `emerging_signal(names_by_source, corpus)`; + network glue (lazy polyfetch,
  SSRF guard, warn-continue, `_date_verified`). L2 `discover` verb in `__main__.py` (lazy-import like `_probe`/
  `_companies_snapshot`). L3 not needed (deterministic, no LLM judgment). **Publication boundary:** discovery
  output names companies → **business data → local `results/` only, NEVER the `data` branch** (boundary guard forbids).

---

## Slice specs

### S1 — #272 tailor critique loop (feat)

- **JS (glue, verified live):** in `cc-workflow-tailor-offer.js`, add an OPTIONAL phase after the tailor
  `parallel(...)` (166) / before Prefill (168), gated by `args.critique` (default off): a critic `agent()`
  scores each CV/cover line on relevance/uniqueness/cover-letter-dependency vs `SOURCES` + emits
  fabrication/keyword-stuffing flags; a revise `agent()` trims/rewrites only flagged lines (never invents,
  never removes an honest gap). Add the `meta.phases` entry. Optional `critiqueRounds` int (default 1).
- **Python (pure, TDD — red→green):** `src/ajoa_kit/stuffing.py` (sibling of `ats_check.py`) — a
  deterministic anti-keyword-stuffing detector (e.g. per-keyword density over a threshold, repeated n-gram /
  list-stuffing) → `stuffing_warnings(cv) -> list[str]`. Surfaced at persist as an optional artifact
  `cv-stuffing-check.md` (mirror `persist_offer.py:114–123` `cv-ats-check.md`, kept OUT of `ARTIFACTS`).
- **Tests** `tests/test_stuffing.py`: behavior-focused (flags density stuffing + repeated list-stuffing;
  clean CV → no warnings; defensive on empty/None). NOT the agent loop (glue, verified live).
- **Switch:** workflow `args.critique` (+ `critiqueRounds`) — document in the script header + CONTRIBUTING
  §Pipeline. No CLI/env change.

### S2 — #274 gap-report upskilling pointers (feat)

- **JS (glue):** extend the gap agent prompt (154–166) — for each uncovered must-have, suggest 1–2 concrete,
  generic, non-fabricated learning pointers (topic/course/doc). Extend `matchSchema` `must_haves` items with
  optional `resources: string[]`.
- **Python (pure, TDD):** extend `coverage.py` `coverage_summary` to render a Resources column/line per
  uncovered must-have (defensive: missing/None `resources` → blank). TDD in `tests/test_coverage.py`
  (resources render when present; absent → unchanged table; None-safe).
- **No new switch.** Rides the existing gap-report + `must_haves` → `coverage_summary` path.

### S3 — #292 discovery (phased, minimal; feat)

- **New L1 `src/ajoa_kit/discover.py` (pure, TDD):** `normalize_company(name)` (strip `Inc/Ltd/GmbH/LLC`
  suffixes, casefold, alias-merge — mirror `parse_geo`); `extract_companies(payload, fmt)` per source format;
  `emerging_signal(names_by_source, corpus)` → `{company: {sources, first_seen_in_corpus?, hiring?}}` joined
  to corpus `company` values. + network glue (lazy `polyfetch_scrape`, `_is_http` SSRF guard, warn-continue).
- **Config:** a `"discovery"` array in `config/default-seed.json` — **exactly ONE OK-tier public source
  (phase 1)** (e.g. the YC Startup Directory public pages, ToS-permitting). Entry ToS-tiered +
  `_date_verified`. Explicitly NOT the full 8-source list; YC Work-at-a-Startup EXCLUDED (login-walled).
  A second source only after the phase-1 ICP value proves out.
- **CLI:** `ajoa-kit discover` verb (`__main__.py`, lazy-import) → writes local `results/emerging-companies.json`
  (aggregate: company → signal). **Never published** (business data; boundary guard forbids).
- **ADR:** new `docs/decisions/0003-discovery-source-tiers.md` (or amend ADR-0002) — per-source OK/CAUTION/
  BLOCKED tiering for the chosen source(s) + the YC WaaS exclusion + reachability-verify.
- **Tests** `tests/test_discover.py`: `normalize_company` canonicalization; `extract_companies` per fmt;
  `emerging_signal` join + no company name leaks to any public path. Mirror `tests/test_companies.py`.
- **Distillation caveat (record in the PR):** this is personal-tool utility, not a differentiator —
  keep it small; do NOT expand trend breadth to chase "market intel".

---

## Docs, switches & issues (answers the standing checks)

- **CHANGELOG:** S1 Added (critique loop + stuffing check); S2 Added/Changed (gap-report resources); S3 Added
  (`discover` verb + emerging-company signal). One `make changelog_new` fragment per slice.
- **README / architecture / roadmap / userstory:** S1/S2 → architecture "Built" one-liner (tailor now has an
  optional critique pass + gap-report upskilling); roadmap shipped bullets. S3 → architecture Built + §Data
  layout (`results/emerging-companies.json` local, business data, never published) + roadmap; README optional.
- **url / env / cli switches:** S1 = workflow `args.critique`/`critiqueRounds` (document in script header +
  CONTRIBUTING §Pipeline). S2 = none. S3 = new CLI verb `discover` (document CONTRIBUTING CLI table + `__main__`
  usage) + new `"discovery"` seed key (document in the seed/ADR). `AJOA_*_DIR` unchanged.
- **Issues:** all three are **already OPEN** (#272/#274/#292) — no new issues to file; each PR `Closes` its
  issue. Cross-ref `#284` (S3 consumer) with "for #284" (do not close). S3's ADR reopens the ADR-0002
  slug-discovery deferral note — link it.

## Verification

- **S1:** `pytest tests/test_stuffing.py` red→green; a live tailor run with `args.critique:true` over a real
  offer → inspect `cv-stuffing-check.md` + that the critic trimmed flagged lines without inventing/removing
  honest gaps; `make check`.
- **S2:** `pytest tests/test_coverage.py` red→green; a live tailor run → `coverage-report.md`/`gap-report.md`
  shows resources per uncovered must-have; `make check`.
- **S3:** `pytest tests/test_discover.py` red→green; a real `ajoa-kit discover` over the seeded source →
  inspect `results/emerging-companies.json` (normalized names, signal, join to corpus); confirm it never
  appears in `git status`/the data branch; `actionlint` if any workflow touched; `make check`.

## Execution & gotchas

- Per slice: branch off fresh `main` (`feat/…`) → **TDD red→green for the pure Python only** (S1 stuffing
  detector, S2 coverage extension, S3 discover module); the `agent()`/prompt changes are glue, **verified
  live** (a real Workflow run), not unit-tested → mutators (`ruff --fix`/format) → **gate LAST**
  (`make check` + `markdownlint-cli2 --no-globs` on changed md + `actionlint` on changed workflows) → commit
  by topic (`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN` push/gh → PR (`Closes #NNN`) →
  `gh pr checks <n> --watch` → squash `--admin --delete-branch` on green → prune.
- **Assume strict lint/typing/sec** (ruff incl. `S`/bandit, `ruff format`, pyright, complexipy ≤10). The
  `×` multiplication sign trips RUF001/2/3 — use `x`; `·` middle dot is fine.
- **S3 boundary is structural:** discovery output names companies → business data → local `results/` only.
  The `make trends_data` fail-closed allowlist would refuse it on the `data` branch anyway — never add it to
  `TRENDS_PUBLISH`.
- **S3 ToS:** the new source must be OK-tier + reachability-verified (ADR-0002) before shipping in the seed;
  read-only public GET only; YC Work-at-a-Startup is login-walled → excluded.
- **Changelog:** each slice needs a `make changelog_new` fragment (`mkdir -p changelog.d` if empty).
