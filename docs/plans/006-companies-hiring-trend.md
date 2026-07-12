# Plan 006 — companies-hiring: tab UX (#3 date · #4 sort) + hiring trend series (#2 local + publishable)

**Status: PLANNED (2026-07-12).** `main` green at `bdc620d`. Follow-ups to the shipped #284 company
tracker (`ajoa_kit.companies` + `scripts/build_ui_companies.py` + the local-only Companies tab) and the
prefill paste-helper (#295). Scope confirmed after an explicit KISS/YAGNI review — the user chose the
**full** #2 (local per-company **and** publishable geo×field) plus **both** #3/#4. This plan carries the
symbol-level source map so a resuming session **does not re-map the codebase**. Handoff:
[docs/handoffs/006-companies-hiring-trend.md](../handoffs/006-companies-hiring-trend.md) — read first.

Item numbers below (#2/#3/#4) are the user's request items, **not** GitHub issues — open the tracking
issues as the first step of each slice (see "Docs, switches & issues"). Real GitHub issues are written
`#NNN`.

## Context

The #284 Companies tab shows a **current snapshot** (who's hiring by geo × field) + a **dormant**
heating/cooling momentum tag (it lights up on its own once the corpus spans ~4+ weeks). Three asks:

- **#3** — show the snapshot's "as of" date so a viewer knows how fresh it is.
- **#4** — click a column header to sort the table asc/desc (the default city-sort buries the top hirers).
- **#2** — a **time series** of hiring "similar to the keyword trends": a **local** per-company series
  (business data → stays under git-ignored `results/`) **and** a **publishable geo × field** aggregate
  (no company names → non-copyrightable facts, like the keyword trends → `data` branch + gh-pages).

The keyword-trends machinery is reused wholesale: the `{week, counts}` NDJSON shape is **identical** to
`WeekCounts`, so **no new model**; publishing is a **one-line allowlist extension** + two workflow
mirrors; the dashboard chart reuses `trends.js` fetch/pivot/render verbatim.

## Prioritized slices (ship order — one PR each)

| # | Slice | What | Test? |
|---|---|---|---|
| **S1** | #3 + #4 companies-tab UX | snapshot-date header + click-to-sort columns | no (UI/glue) |
| **S2a** | `companies-snapshot` verb + publish | corpus → hiring NDJSON (local + geo×field) + publish wiring | **yes (module TDD)** |
| **S2b** | dashboard views | publishable geo×field chart + local per-company detail | no (no-build UI) |

---

## Source map (reuse, don't rebuild — verified 2026-07-12, `file:line`)

### Keyword-trends pipeline — mirror this for #2 (`src/ajoa_kit/trend_snapshot.py`)

- `main()` **286-326** — reads `results/corpus.json` (else `jobs-raw.json`); the **`date_of` seam**:
  `_first_seen` **143-145** (`job["first_seen"]`) vs `_posted_at` **138-140**. Vocabulary via
  `load_keywords` + `build_patterns` **304-305**. Writes to `settings.public_data_dir` at **311-315**.
- `extract_counts(jobs, pattern)` **41-52** — per-key **document frequency** (per-JD set; a JD counts a
  key once). Returns `{key: int}`. *(For #2, replace the keyword pattern with a `key_of(job)` that emits
  the geo×field / company bucket key — see `_bucket` below.)*
- Date → bucket label: `_DATE_PARSERS` **84** (`_from_epoch` 55 / `_from_iso` 68 / `_from_rfc822` 76);
  `parse_week` **87-103** → `YYYY-Www`, `parse_day` **106-119** → `YYYY-MM-DD`, `parse_month` **122-135**
  → `YYYY-MM`; all return `None` on unparseable (skip-and-count).
- `_bucket(jobs, pattern, key_of)` **148-167** — the **shared core**: groups jobs by `key_of(job)`
  (default a date parser), runs `extract_counts` per group, returns `({bucket: counts}, skipped)`.
- `bucket_by_day` **170-181** (takes `date_of`), `weekly_from_daily` **184-200** /
  `monthly_from_daily` **220-235** (roll up by **summing** day buckets — series can never disagree),
  `bucket_by_week` **203-217** / `bucket_by_month` **238-248** (day→rollup composites).
- `_upsert(path, key_field, record)` **251-268** — `json.dumps(sort_keys=True)`, rewrites the file
  dropping any prior line with the same key, appends. Uses `split("\n")` (not `splitlines()`) 260-266.
- `upsert_week`/`upsert_day`/`upsert_month` **271-283** — validate via the pydantic model then `_upsert`
  with key field `week`/`date`/`month`.
- **Line shape:** `{"counts": {key: int}, "week"|"date"|"month": "<label>"}` (sorted keys). No PII ever.

### Models (`src/ajoa_kit/models.py`) — reuse verbatim

- `WeekCounts` **67-76** `{week, counts}` · `DayCounts` **79-87** `{date, counts}` · `MonthCounts`
  **90-98** `{month, counts}`. **#2's publishable series reuses these** (counts keys become
  `"<geo> · <field>"` strings). `CompanyRow` **101-120** — the existing local snapshot contract; its
  docstring **110-113** states company + geo is exactly what the data-branch boundary guard forbids.

### Bucket keys for #2 (`src/ajoa_kit/companies.py`, shipped #284)

- `parse_geo(location, remote)` **45-62** → canonical `(city, region)`; `_CITY_ALIASES` **26-34**;
  Remote/Unknown buckets. `_field(rec, lane_by_id)` **79-81** — scored lane → `lane_hint` → `"unscored"`.
  `_momentum` **90-98** (14d vs prior-14d `first_seen` intake). `aggregate_companies` **105-150** keyed
  on `(city, field, company)`. → **publishable key** = `f"{city}·{region}? {field}"` geo×field (no
  company); **local key** = `company`.

### Corpus (the source — no re-scrape needed)

- `normalize.record()` **115-136** emits `company, company_slug, lane_hint, title, location, remote,
  posted_at, …`. `corpus.merge_corpus()` **35-81** stamps `first_seen` / `last_seen` / `last_changed` /
  `content_hash`. So each `results/corpus.json` record already carries `first_seen + company + location +
  remote + lane_hint` — everything to build the series from `first_seen` with zero re-scraping.

### Publish mechanism (`Makefile`)

- **`TRENDS_PUBLISH` SSOT** **:127** — one definition feeds the add loop + shrink guard + boundary guard.
  **Add `public-data/hiring-{weekly,daily,monthly}.ndjson` here (the single edit).**
- `trends-data` **:129-162** — weekly-exists gate **130**; **shrink guard 135-143** (refuse push if a
  file would lose buckets vs `origin/data`, `TRENDS_FORCE=1` overrides); force-add into a throwaway index
  **147-150** (`git add -f`); **fail-closed boundary guard 154-159** (walks the tree; any non-allowlisted
  path aborts; empty allowlist matches nothing → structurally prevents a company file leaking); parentless
  `commit-tree` + `push -f origin …:data` **160-161**.
- `preview` **:79-117** bundles trends into a throwaway copy and already runs `build_ui_companies.py`.

### Cron + deploy workflows

- `.github/workflows/ingest-daily.yaml` — cron `0 6 * * *` **:12**; env `AJOA_*_DIR` absolute **30-35**;
  **restore-trends-from-data loop :102** (add `hiring-*.ndjson` so upsert accumulates); `trend-snapshot`
  step **112-114**; `make trends-data` push **116-120**. **New `companies-snapshot` step slots between
  112-114 and 116-120.** All `uses:` SHA-pinned (checkout `9c091bb…` v7.0.0, setup-uv `11f9893b…` v8.3.2).
- `.github/workflows/gh-pages.yaml` — `TRENDS_FILES` same-origin bundle **61-64** (add `hiring-*.ndjson`).

### Dashboard (`ui/src/trends.js`) — reuse for #2b

- `defaultDataBase()` **12-21** (`?base=` override). `GRANULARITIES` **27-31** — `week/day/month →
  {file, key, toDate}`, mirrors `TRENDS_PUBLISH`. `fetchTrends(url)` **76-88** (split `"\n"` → `JSON.parse`
  per line, `null` on miss). `loadRealTrends(gran)` **95-112** — same-origin `public/data/<file>` first,
  then `${DATA_BASE_URL}/public-data/<file>`. `pivot(records)` **65-72** (`labels = r[key]`, `keys` =
  union of `counts`). `renderChart` **119-147** / `renderTrends` **201-212** / `windowRecords` **194-199**.
  A hiring chart reuses fetch/pivot/window unchanged — only a new `GRANULARITIES`-style map + a
  `loadRealTrends` clone pointing at `hiring-*.ndjson`.
- `scripts/build_ui_companies.py` (aggregate-for-preview) — **stamp the #3 snapshot date here**.
  `ui/src/companies.js` `loadRealCompanies` + `renderCompanies` (shipped #284) — **#3 header + #4 sort +
  #2b local detail here**.

---

## Slice specs

### S1 — #3 snapshot date · #4 sortable columns (one small PR)

- **#3:** `build_ui_companies.py` computes `snapshot = max(last_seen across corpus)` and writes
  `companies.json` as `{"snapshot": "<YYYY-MM-DD>", "rows": [...]}` (contract array→object; only
  `build_ui_companies` + `companies.js` consume it). `companies.js` `loadRealCompanies` returns
  `.snapshot`/`.rows`; `renderCompanies` shows "snapshot as of `<date>`" in the section head.
- **#4:** `companies.js` — click a `<th>` sorts `rows` by that column (company/city/region/field/count/
  momentum), toggles asc/desc, re-renders with a ▲/▼ indicator; default `(city, field, -count, company)`.
  ~30 lines vanilla JS; every interpolated value already goes through `esc()`.
- No module logic → **no unit test** (glue/UI); verify headless.

### S2a — `companies-snapshot` verb + publishable aggregate (module → TDD, then publish wiring)

- **New module `src/ajoa_kit/companies_trend.py`** (pure, TDD): read `results/corpus.json`, bucket by
  `first_seen` reusing `trend_snapshot._bucket` / `parse_day` / `weekly_from_daily` / `monthly_from_daily`
  / `_upsert*`; per-bucket key via `companies.parse_geo` + `companies._field`. Emit **two** trios:
  - **Publishable** `public-data/hiring-{weekly,daily,monthly}.ndjson` = `{week|date|month,
    counts:{"<geo> · <field>": n}}` — **no company names** — via `WeekCounts`/`DayCounts`/`MonthCounts`.
  - **Local** `results/hiring-companies.ndjson` = `{week, counts:{"<company>": n}}` — git-ignored.
- **CLI:** add `_companies_snapshot` handler + `companies-snapshot` subparser in `__main__.py` (mirror
  `_trend_snapshot`, no args).
- **Publish wiring:** `TRENDS_PUBLISH` += the three `hiring-*` paths (Makefile:127) · `ingest-daily.yaml`
  restore loop (:102) + a new `companies-snapshot` step (between :112-114 and :116-120) · `gh-pages.yaml`
  `TRENDS_FILES` (:61-64). SHA-pin unchanged.
- **Tests** `tests/test_companies_trend.py` (value-add): buckets by `first_seen`; geo×field vs company
  keys; day→week/month rollups agree (sum); the publishable trio carries **no company name** in any
  `counts` key. Mirror `tests/test_trend_snapshot.py` style.

### S2b — dashboard views (one PR)

- **Publishable geo×field chart** (gh-pages): a `GRANULARITIES`-style entry + a `loadRealTrends` clone
  for `hiring-*.ndjson`, rendered via the existing `pivot`/`renderChart`/`windowRecords`. Surface as a
  second chart block (Market-trends tab) or a chart in the Companies tab.
- **Local per-company detail** (preview-only): render `results/hiring-companies.ndjson` (bundle it in
  `make preview` alongside the other local data) as a compact per-company hiring sparkline / small chart
  in the Companies tab. Local-only; never published.

---

## Docs, switches & issues (answers the standing checks)

- **S1:** CHANGELOG (Added/Changed). **No new url/env/cli switch** (`companies.json` array→object is
  internal). README/architecture/roadmap/userstory: **no change** (local-only UX). **Open** one issue:
  "companies-tab UX (snapshot date + sortable columns)"; the PR `Closes` it.
- **S2a/S2b:** CHANGELOG (Added). **New CLI verb `companies-snapshot`** → document in CONTRIBUTING CLI
  table + `__main__` usage docstring. **New published files** `public-data/hiring-*.ndjson` → document
  the data-branch URLs in CONTRIBUTING §Trends data branch + README (mirror the keyword-trends URL docs);
  `AJOA_PUBLIC_DATA_DIR` already exists (no new env). **architecture.md** — Built list + §Data layout
  (publishable geo×field series **and** the local git-ignored `results/hiring-companies.ndjson`); **no
  new ADR** (mirrors how keyword trends are documented) + a one-line **ADR-0002 / research.md** note that
  geo×field hiring counts are the same aggregate-only category. **roadmap.md** shipped bullet;
  **userstory.md** / **ui/README.md** optional. **Open** one issue: "companies-hiring trend series (local
  and publishable)"; the PR(s) `Closes` it. **Cross-reference** `#269` (posted_at rides this machinery) and
  `#191` (corpus durability underpins it) with "for #N" — do **not** close them.

## Verification

- **S1:** headless (polyfetch patchright): Companies tab shows "snapshot as of …"; clicking each header
  flips row order asc/desc; `make ui-check` + `make check` (no new module) + markdownlint.
- **S2a:** `pytest tests/test_companies_trend.py` red→green; a real `companies-snapshot` over
  `results/corpus.json` → inspect the NDJSON (weeks, geo×field keys, **no company name** in the public
  files); `make trends-data` **boundary guard passes** (dry-check: only allowlisted paths in the tree);
  confirm `results/hiring-companies.ndjson` never appears in `git status`/the data branch. `actionlint`
  on the changed workflows.
- **S2b:** headless render of both charts (data-branch fetch for the published one; preview bundle for
  the local one), no console errors. **Post-merge:** a `workflow_dispatch` of `ingest-daily` to confirm
  the cron produces + publishes the new series (like the #217 verify-sources dispatch check).

## Execution & gotchas

- Per slice: branch off fresh `main` (`feat/…`/`ci/…`) → TDD (S2a module only) → implement → mutators
  (`ruff --fix`/format) → **gate LAST** (`make check` + `markdownlint-cli2 --no-globs` on changed md +
  `actionlint` on changed workflows) → commit by topic (`--no-gpg-sign`) → `env -u GH_TOKEN
  -u GITHUB_TOKEN` push/gh (`gh auth setup-git` once) → PR → `gh pr checks <n> --watch` → squash
  `--admin --delete-branch` on green → prune local + `git remote prune origin`.
- **Boundary is structural:** the fail-closed boundary guard (Makefile:154-159) aborts the data-branch
  push if any non-allowlisted path is in the tree — so a company-named file can never leak. Add **only**
  the geo×field `hiring-*.ndjson` to `TRENDS_PUBLISH`.
- **Shrink guard:** the published series accumulates; a run that would drop buckets is refused
  (`TRENDS_FORCE=1` overrides for an intentional prune) — restore from the data branch before snapshotting
  (the cron's restore loop already does this; add `hiring-*` to it).
- **Config gitignore trap (learned #217):** anything under `config/`/`results/` matching `.gitignore`
  needs `git add -f` in a workflow — N/A here (we write to `public-data/` + git-ignored `results/`), but
  keep in mind if a step ever commits a config/seed file.
- **Changelog:** S1/S2a/S2b each need a `make changelog_new` fragment (`mkdir -p changelog.d` if empty);
  the ADR/CONTRIBUTING/architecture doc edits ride in the S2a PR.

## Backlog context (open issues, ROI, post-Wave-1)

7 open: `#191` corpus-durability (bug, **H** — foundation for the tracker + this trend; needs a decision +
a secret), `#272` tailor critique loop (**M-H**), `#292` discovery sources (**M-H**, phase it), `#269`
posted_at axis (**M**, ~free once this trend machinery lands), `#274` upskilling (M), `#275` md→PDF spike
(L), `#193` reusable release workflows (L, upstream-blocked). Suggested next after this plan: **#191**
(rising priority — more features now depend on the corpus history), then **#272**.
