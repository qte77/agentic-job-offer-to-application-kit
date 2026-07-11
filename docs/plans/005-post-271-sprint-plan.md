# Plan 005 — post-#271 sprint: docs hygiene + trends-UI + dashboard flags + market-intel tracker

**Status: Sprints 1–2 SHIPPED (2026-07-11)** — docs hygiene #282 · trends-granularity UI #285 · dashboard
flags #286; follow-on fixes #287 (picker styling) #289 (`make preview` bundles daily/monthly) #290
(picker order). `complexipy` pinned `<6` (#288 — 6.0 breaks the ≤10 gate; adopting 6.x = a deliberate
refactor of `persist_scored.main`/`refresh.main`). Deep `posted_at` trends (171w/545d/58m) published to
the `data` branch (#191 commented; live series now a posted_at/first_seen hybrid, semantics on #269).
**Sprint 2 SHIPPED:** company tracker #284 (#294) · prefill paste-helper #295 (#296). **Next: #292**
(discovery) + **#269** (posted_at backfill). #187/#188 closed. Handoff:
[docs/handoffs/005-post-271-sprint-plan.md](../handoffs/005-post-271-sprint-plan.md) — read it first.
This plan carries the full symbol-level source map so a resuming session **does not re-map the
codebase**.

## Context

PR #271 (typed relevance rubric + `ScoredItem` end-to-end) merged (508a62e). A docs/switch/README/root
audit + a trends diagnosis surfaced this backlog. Two findings shaped priorities: (1) the pipeline
**produces `trends-daily.ndjson` + `trends-monthly.ndjson` every run but `ui/src/trends.js` fetches
only the weekly series** (produce-but-unused = #187/#188); (2) the weekly trend history was **reset
~2026-06-27** — the live `data`-branch `trends.ndjson` is only W26–W28 (~1549 B) vs the README
screenshot's W13–W25; forward-protection now holds, the old weeks are only recoverable from a pre-reset
corpus artifact (deemed not worth it — KISS).

## Prioritized plan (ROI = value ÷ effort; H/M/L)

| Sprint | Item | ROI | Cluster |
|---|---|---|---|
| **S1** | Docs/hygiene closeout (`.env`, roadmap #271, badges, gitignore, pointers) | High | docs |
| **S1** | Trends-granularity UI (#187 daily + #188 monthly) | High | viz |
| **S1** | Dashboard `deadline`/`deal_breaker` flags | Med | viz |
| **S1** | #260 deploy-on-every-push filter eval (chore) | Med | reliability |
| **S2 ✅** | Company-hiring tracker MVP (local, geo × field, heating/cooling) — **shipped #294** | High* | market-intel |
| **S2 ✅** | Prefill paste-helper — dashboard per-doc Copy of the prefill pack — **shipped #296** | Med | app-quality |
| **S2** | #269 posted_at backfill (bootstraps the tracker's delta) | Med | viz |
| **S3** | #272 tailor critique loop · #273 outcome tracker | Med(strategic-H) | app-quality |
| **backlog** | #217 source freshness · #193 reusable release workflows · #274 · #275 | Med/low | — |
| **defer** | #195 JobRecord (YAGNI — jobs-raw always well-formed) · #191 durable store (stopgap holds) | Low | — |

`*` tracker value is strategic but its *heating/cooling* delta needs history depth we lack (~3 weeks
post-reset); ship the snapshot now, the delta accrues over ~4–8 weeks (+ #269 bootstrap).

---

## S1 slices — spec + source map

### Slice 1 — docs/hygiene closeout (one PR; **changelog-EXEMPT** per CONTRIBUTING.md:92)

- **`.gitignore`** (root): currently ignores `results/` (line 6), `public-data/` (9), the config seed
  override (10), and `.venv/.pytest_cache/.ruff_cache/.coverage` (~16–23). **Add** `.env`,
  `.complexipy_cache/`, `.hypothesis/`.
- **`src/ajoa_kit/settings.py`**: `AppSettings` — `env_prefix="AJOA_"`, `env_file=".env"` (line 32);
  fields `config_dir` (35), `results_dir` (39), `public_data_dir` (43). The `.env` support is real but
  **undocumented + un-gitignored** (a user could commit private `AJOA_*` paths) — the one switch gap.
- **`CONTRIBUTING.md`**: env table lines 72–79 (rows AJOA_CONFIG_DIR:74 / RESULTS_DIR:75 /
  PUBLIC_DATA_DIR:76 / POLYFETCH_DIR:77 / PORT:78 / TRENDS_FORCE:79). **Add** an `.env` row
  ("optional; overrides `AJOA_*`; git-ignored — keep private paths here").
- **`docs/roadmap.md`**: shipped-bullet convention — see #197 (95–97), #214 (55–58), #226 (59–64).
  **Add** a #271 bullet (explainable rationale + `deadline`/`deal_breaker`; `ScoredItem` typed
  end-to-end per ADR-0003). **Trim** the stale "relevance" from the ADR-0003 "Later" line (125–127:
  "a `JobRecord` model + parse-on-read at the JD / **relevance** / tailor boundaries") — #271 shipped
  that boundary (ADR-0003:80 already reads "through persist + the merge/refresh re-reads (#271)").
- **`README.md`**: badge block 6–11 (License / Version:7 / CodeQL:8 / CodeFactor:9 / CI:10 /
  Lint-MD:11). Sections `## What`:13 · `## How`:54 · `## Why`:96 · `## Refs`:102 · `## License`:115.
  **Move `## Why` (96–100) above `## How` (54)** (canonical order). **Add** two static shields badges:
  `coverage-≥80%` (pyproject.toml `fail_under = 80`, line 79) + `python-3.11+` (`requires-python`,
  pyproject.toml:6). Maintain like the Version badge.
- **`AGENT_LEARNINGS.md`** (root) — orphan (zero inbound refs, `git grep AGENT_LEARNINGS` empty).
  **Add** a one-line pointer in `AGENTS.md`; note `CLAUDE.md` is a symlink alias of `AGENTS.md`.
- **Keep as-is** (verified clean): `.markdownlint-cli2.jsonc` (auto-discovery), `lychee.toml`
  (Makefile:60), `NOTICE`, `changelog.d/`.

### Slice 2 — trends-granularity UI (#187 daily + #188 monthly) (**needs a changelog fragment**)

- **`ui/src/trends.js`**: `DATA_BASE_URL` derived 12–21 (`?base=` override at 20). `loadRealTrends()`
  80–91 fetches **only** weekly `public/data/trends.ndjson` (same-origin) / `…/public-data/trends.ndjson`
  (data branch). `fetchTrends(url)` 61–73 (NDJSON → records). `pivot(records)` 50–57 assumes each
  record has **`.week`**. `renderTrends(trendRecords, range)` 179–189 sorts by `a.week` then windows.
  `windowRecords(sorted, value)` 171–177 windows by ISO-week via `isoWeekToDate` 159–167. The existing
  `<select>` ("3mo") is a **time-window** (weeks-back), NOT a granularity switch.
- **Published series** (data branch `public-data/`, bundled same-origin by gh-pages): `trends.ndjson`
  (weekly `{week,counts}`), `trends-daily.ndjson` (`{date,counts}`, 5821 B), `trends-monthly.ndjson`
  (`{month,counts}`, 1050 B). Written by `trend_snapshot.py` (models `WeekCounts`/`DayCounts`/
  `MonthCounts`, models.py:67–98).
- **Design:** add a granularity `<select>` (week | day | month) in `ui/index.html` beside the window
  control; on change, fetch the matching NDJSON (`trends.ndjson` / `trends-daily.ndjson` /
  `trends-monthly.ndjson`, both same-origin + data-branch fallback like `loadRealTrends`) and render.
  **Key logic change:** `pivot`/`renderTrends`/`windowRecords` hard-code `.week`; daily is `.date`,
  monthly is `.month` → thread a label-key accessor (`record.week|date|month`) and a per-granularity
  window parse (or window by record count for day/month). Keep the label-key access DRY.
- **Verify:** `make ui-check` (`scripts/ui_check.py` serves `ui/`, asserts `#trends-line` width +
  fonts + `tr.offer-row`); extend a headless e2e for the granularity switch. No JS unit tests (no-build).

### Slice 3 — dashboard deadline/deal_breaker flags (**needs a changelog fragment**)

- **`ui/src/shortlist.js`**: `renderShortlist` 62–108, row template 88–97 (five `<td>`: company /
  title+rationale / lane / score / verdict). **Add** two optional badges inside the Role `<td>`
  (90–93, next to `.role-title`/`.rationale`) — `${it.deadline ? '<span class="due">due '+esc(it.deadline)+'</span>' : ''}`
  and a `.deal-breaker` span with `esc(it.deal_breaker)`. `esc` = dom-utils.js:6–10, `safeUrl` = :14.
  `loadRealShortlist()` 33–42 already loads the real fields (`ScoredItem.model_dump`).
- **`ui/src/style.css`**: mirror the `.lane` pill (330–339) for `.due` (token `--data-caution`) and
  `.deal-breaker` (`--data-negative`); tokens declared ~line 39; `.score`/`.verdict` 341–357.
- **`ui/public/data/demo.json`**: item shape id/title/company/url/best_lane/score/verdict/rationale/
  cv/cover_letter (sample 12–23; `_synthetic` note line 2). **Add** `deadline` to one row +
  `deal_breaker` to another (fictional). Server precedent: `persist_scored.py::_flags` 77–82 +
  write_lane:101 (`· due <date>` / `· deal-breaker`). No `stale` UI precedent exists.

### Slice 4 — #260 deploy-on-every-push eval (chore)

- **`.github/workflows/gh-pages.yaml`** — the deploy trigger/paths. `ingest-daily.yaml:137–140`
  **dispatches** gh-pages explicitly (a `GITHUB_TOKEN` push can't self-trigger). Observed: every `main`
  push fires a full Pages deploy (~9 s). Eval restoring a `paths:` filter (redeploy only on `ui/` /
  `public-data/` changes) **without** breaking the cron's explicit dispatch. Outcome may be "leave it"
  (cheap) or a small filter — document the finding on #260.

### Slice 5 — issue comments (no branch; `gh`)

- **#191**: trend-loss diagnosis — live weekly series = W26–W28, screenshot = W13–W25, reset
  ~2026-06-27; forward-protection (restore + shrink-guard) holds; recovery needs a pre-reset corpus
  artifact; durable store deemed YAGNI for now (keep the `e8238d7` fail-loud stopgap).
- **#187 / #188**: confirmed — `trends-daily.ndjson` / `trends-monthly.ndjson` are produced & published
  every run but `ui/src/trends.js::loadRealTrends` wires only the weekly series (Slice 2 closes this).
- (optional) **#195**: lanes half shipped (#195); JobRecord half deferred as YAGNI.

---

## S2 slice — company-hiring tracker MVP (local-only) — **SHIPPED #294**

Delivered as `ajoa_kit.companies` (TDD'd: `parse_geo` lossless city-merge + `aggregate_companies`) +
`scripts/build_ui_companies.py` + a local-only Companies tab. The design notes below are retained as
the as-built record.

- **Data source:** `results/corpus.json` records (from `corpus.merge_corpus`, corpus.py:49–81) —
  fields `company`, `company_slug`, `location`, `best_lane`/`lane_hint`, `first_seen`, `last_seen`,
  `last_changed`, `content_hash`, `stale`. Plus `results/<lane>/shortlist.json` (`ScoredItem`).
- **Aggregate:** mirror `scripts/build_ui_shortlist.py` (`aggregate()` globs `results/*/shortlist.json`,
  skips `stale`, writes `public/data/shortlist.json` for `make preview` only). Add a sibling
  `scripts/build_ui_companies.py` producing `{geo, field, company, count, momentum}` from the corpus.
- **Heating-up / cooling-off:** per-company open-role count as a **delta over weeks** (from per-JD
  `first_seen`/`last_seen`/`stale`). Needs history depth — accrues over ~4–8 weeks post-reset; **#269**
  posted_at backfill bootstraps an approximate earlier baseline. Ship the snapshot (who's hiring by
  geo × field) first; the momentum tag lights up later.
- **Geo normalization:** free-text `location` → country/city — the main new work (look at `normalize.py`
  for existing normalization idiom). A build script is a **module** → **TDD it** (unlike the UI slices).
- **Render:** a new dashboard tab (like `#tab-trends`) or a preview-only view; **local-only** — the
  `data`-branch boundary guard (Makefile:133–141) forbids company data on the public branch.
- **ToU / GDPR / PII:** company + geo + field + counts = **business data** (companies aren't natural
  persons → GDPR low-risk); exclude recruiter names/emails. Local MVP = safe; a **published** version
  names companies → gate behind an **ADR-0002** ToU review + PII scrub. Capture all this in the issue.

## Backlog / defer (issue-tracked; no source map here)

Enhancements: #217 (source-freshness re-probe; `verify-sources` exists), #193 (reusable release
workflows), #274 (gap-report upskilling), #275 (md→PDF spike, no LaTeX). Larger: #272 (tailor
critique loop), #273 (outcome tracker). **Defer** #195 (YAGNI) and #191 durable store (stopgap
holds — see Slice 5 comment).

## Documented-switch reference (verified complete except `.env`)

- **Env:** `AJOA_CONFIG_DIR`/`RESULTS_DIR`/`PUBLIC_DATA_DIR` (settings.py:35–43) · `POLYFETCH_DIR` ·
  `PORT` · `TRENDS_FORCE` → CONTRIBUTING.md:72–79. **Gap:** `.env` (settings.py:32) — Slice 1 fixes it.
- **CLI:** 12 subcommands (`__main__.py`) → CONTRIBUTING.md:52–65 (complete).
- **URLs:** gh-pages `https://qte77.github.io/agentic-job-offer-to-application-kit/` · data branch
  `raw.githubusercontent.com/<owner>/<repo>/data/public-data/trends.ndjson` · `?base=` override
  (trends.js:16–20,83) → README.md:56, CONTRIBUTING.md §Trends data branch (132–154).

## Execution & gotchas

- Per slice: branch off fresh `main` (`feat/…`, `docs/…`, `ci/…`) → commit by topic → **gate LAST**
  (`make check` + `markdownlint-cli2 --no-globs` on changed md + lychee) → `--no-gpg-sign` commits →
  `env -u GH_TOKEN -u GITHUB_TOKEN` push/gh (`gh auth setup-git` once) → PR → `gh pr checks --watch` →
  `gh pr merge --squash --admin --delete-branch` → prune local.
- **TDD only for module (`.py`) slices** (the S2 build script) — the S1 docs/UI/gitignore slices touch
  no module, so no tests (repo rule: value-add only, not for docs/UI/scripts-without-logic).
- **Changelog:** docs closeout (Slice 1) + the #260 eval are **exempt** (CONTRIBUTING.md:92); the UI
  features (Slices 2, 3) each need a `make changelog_new` fragment (`mkdir -p changelog.d` if empty).
- `ui/` has **no JS unit tests** — verify via `make ui-check` (needs
  `POLYFETCH_DIR=../polyfetch-scrape`) plus a headless e2e through polyfetch's patchright venv.
- markdownlint traps: MD004 (a wrapped line starting `+`/`-`), MD049 (match the file's italic style);
  CI `lint/markdown` 429s intermittently (re-run); CI `lint/links` runs whole-repo lychee.
