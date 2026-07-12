# Handoff 006 — companies-hiring: tab UX (#3 date · #4 sort) + hiring trend series (#2)

**State (2026-07-12):** `main` green at `bdc620d`. #284 company tracker + #295 prefill paste-helper +
single-column offer-expand (#298) all SHIPPED. This is the approved next sprint, scope KISS-reviewed:
**full** #2 (local per-company + publishable geo×field) + **both** #3/#4. Plan (with the full
symbol-level source map — **read it; don't re-map the codebase**):
[docs/plans/006-companies-hiring-trend.md](../plans/006-companies-hiring-trend.md).

## What this is (one paragraph)

Three follow-ups to the local-only Companies tab. **#3** shows the snapshot's "as of" date; **#4** makes
the columns click-to-sort. **#2** adds a hiring **time series** "like the keyword trends": a **local**
per-company series (business data → git-ignored `results/`) **and** a **publishable geo × field**
aggregate (no company names → `data` branch + gh-pages, same aggregate-only bar as the keyword trends).
It **reuses the keyword-trends pipeline wholesale** — same `{week, counts}` shape (no new model), a
one-line publish-allowlist extension, and the existing `trends.js` chart code.

## Resume here (in order — one PR per slice)

0. **Open two tracking issues first** (the plan's item numbers #2/#3/#4 are not GitHub issues):
   (a) "companies-tab UX (snapshot date + sortable columns)", (b) "companies-hiring trend series (local +
   publishable)". Each PR `Closes` its issue; cross-ref `#269`/`#191` with "for #N" (never "closes").
1. **S1 (#3 + #4)** — `feat/companies-tab-ux`, changelog fragment. `build_ui_companies.py` stamps the
   snapshot date + wraps `companies.json` as `{snapshot, rows}`; `companies.js` renders the date +
   click-to-sort. No module → no test; verify headless.
2. **S2a (#2 pipeline)** — `feat/companies-snapshot`, TDD. New `ajoa_kit.companies_trend` module +
   `ajoa-kit companies-snapshot` verb; emits local `results/hiring-companies.ndjson` (company keys) +
   publishable `public-data/hiring-{weekly,daily,monthly}.ndjson` (geo×field keys). Wire publish
   (`TRENDS_PUBLISH` + the two workflow mirrors + a cron step). Docs: CONTRIBUTING (verb + data-branch
   URLs), architecture, ADR-0002/research note. **This is the only slice with tests.**
3. **S2b (#2 charts)** — `feat/companies-trend-ui`, changelog fragment. Publishable geo×field chart
   (reuse `trends.js`) + local per-company detail in the Companies tab (`make preview` bundles it).

## Per-slice recipe

Branch off fresh `main` → **TDD red→green only for the S2a module** → implement → mutators
(`ruff --fix`/format) → **gate LAST** (`make check` + `markdownlint-cli2 --no-globs` on changed md +
`actionlint` on changed workflows) → commit by topic (`--no-gpg-sign`) → `env -u GH_TOKEN
-u GITHUB_TOKEN` push (`gh auth setup-git` once) → PR → `gh pr checks <n> --watch` → `gh pr merge <n>
--squash --admin --delete-branch` on green → prune local + `git remote prune origin`.

## Gotchas (this environment)

- All `gh`/`git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN` (bare `gh` 401s).
- **Boundary is structural:** the `make trends-data` fail-closed guard aborts the `data`-branch push if
  any non-allowlisted path is in the tree — add **only** the geo×field `hiring-*.ndjson` to
  `TRENDS_PUBLISH`; company names never leave `results/`.
- **Shrink guard:** the published series accumulates — the cron's restore-from-`data` loop must include
  `hiring-*` (else a fresh snapshot looks like a shrink and the push is refused).
- **No new pydantic model** — reuse `WeekCounts`/`DayCounts`/`MonthCounts`; the `counts` keys just become
  geo×field (public) / company (local) strings.
- `ui/` has no JS unit tests — verify with `make ui-check` (needs `POLYFETCH_DIR=../polyfetch-scrape`) +
  a headless e2e via polyfetch's patchright venv (capture `page.on("console")`).
- markdownlint: MD004/MD049 traps; `lint/markdown` 429s intermittently (re-run); `lint/links` runs
  whole-repo lychee. Changelog fragments live in git-ignored-by-lint `changelog.d/`.
- Post-merge, verify the cron end-to-end with a `workflow_dispatch` of `ingest-daily` (as done for #217).

## Touch points (current state — verify, don't re-map; line-level detail is in the plan)

| File | Current state |
|---|---|
| `src/ajoa_kit/trend_snapshot.py` | keyword-trends pipeline to mirror: `_bucket`/`parse_*`/`weekly_from_daily`/`monthly_from_daily`/`_upsert*`; `date_of` seam (`_first_seen`/`_posted_at`); writes `public-data/trends{,-daily,-monthly}.ndjson`. |
| `src/ajoa_kit/companies.py` | shipped #284: `parse_geo`/`_field`/`aggregate_companies`. Reuse `parse_geo`+`_field` for the bucket keys. |
| `src/ajoa_kit/models.py` | `WeekCounts`/`DayCounts`/`MonthCounts` `{week/date/month, counts}` — reuse. `CompanyRow` docstring records the company/geo publish prohibition. |
| `src/ajoa_kit/companies_trend.py` | **does not exist** — the new S2a module. |
| `Makefile` | `TRENDS_PUBLISH` SSOT (add loop + shrink guard + fail-closed boundary guard); `trends-data` push; `preview` bundles trends + runs `build_ui_companies.py`. **No `hiring-*` yet.** |
| `.github/workflows/ingest-daily.yaml` | cron; restore-trends loop; `trend-snapshot` step; `make trends-data`. **No `companies-snapshot` step yet.** |
| `.github/workflows/gh-pages.yaml` | `TRENDS_FILES` same-origin bundle. **No `hiring-*` yet.** |
| `ui/src/trends.js` | `GRANULARITIES`/`fetchTrends`/`loadRealTrends`/`pivot`/`renderChart`/`windowRecords` — reuse for the hiring chart. |
| `scripts/build_ui_companies.py` · `ui/src/companies.js` | shipped #284 (aggregate-for-preview + Companies-tab render). **#3 date + #4 sort + #2b local detail go here.** No snapshot date, no sortable headers yet. |
| `results/corpus.json` | carries `first_seen`/`last_seen`/`company`/`location`/`lane_hint` per record — the series source, no re-scrape. |
| GitHub issues | **no** issue yet for #2 or #3/#4 (open both, step 0). `#269`/`#191` open (cross-ref). |
