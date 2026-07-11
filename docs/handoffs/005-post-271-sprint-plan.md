# Handoff 005 — post-#271 sprint (docs hygiene · trends-UI · flags · market-intel)

**State (2026-07-11):** `main` green at `2e835b1`. **Sprint 1 SHIPPED** (#282/#285/#286, fixes #287/#289/#290);
`complexipy` pinned `<6` (#288 — **must stay <6**). Deep `posted_at` trends published to `data`
(171/545/58). **Sprint 2 SHIPPED:** company tracker #284 (#294) · prefill paste-helper #295 (#296).
Open: **#292** discovery sources, **#269** posted_at backfill (resume here). Plan (approved,
with full symbol-level source map — **read it; don't re-map the codebase**):
[docs/plans/005-post-271-sprint-plan.md](../plans/005-post-271-sprint-plan.md).

## What this is (one paragraph)

A prioritized post-#271 sprint. **Sprint 1** (do first): a docs/hygiene closeout (one PR), then wire the
**already-published** daily/monthly trend series into the dashboard (#187/#188 — the pipeline emits
`trends-daily.ndjson` + `trends-monthly.ndjson` every run but `ui/src/trends.js` fetches only weekly),
then surface `deadline`/`deal_breaker` in the shortlist UI (they already render in `shortlist.md`), then
a quick #260 deploy-filter eval, plus three issue comments. **Sprint 2**: a local-only company-hiring
tracker (geo × field, "heating-up / cooling-off" hiring — snapshot now, momentum accrues). S3+ and
backlog are issue-tracked in the plan. Two NEW issues to open (dashboard flags · company tracker).

## Done

- **Sprint 1** — docs hygiene (#282), trends-granularity UI (#285), dashboard flags (#286) + fixes
  #287/#289/#290; #260 eval closed "keep it"; #187/#188 closed.
- **Sprint 2** — company-hiring tracker (#284 → #294): `ajoa_kit.companies` (TDD'd) +
  `scripts/build_ui_companies.py` + a local-only Companies tab. Prefill paste-helper (#295 → #296):
  the offer expand now Copy-surfaces the prefill pack (clipboard only, human submits — no auto-apply).

## Resume here

Sprints 1–2 are shipped (see **Done**). Remaining post-#271 backlog, in priority order:

1. **#292 — curated startup-discovery sources** (aggregate company signal, ToU-tiered per ADR-0002) →
   feeds the #284 tracker's company breadth.
2. **#269 — posted_at backfill** (bootstraps the tracker's heating/cooling momentum earlier; the live
   corpus spans only ~2 weeks post-reset, so momentum currently ships dormant).
3. **S3+** (issue-tracked in the plan): #272 tailor critique loop · #273 outcome tracker · #274 · #275.

## Per-slice recipe

Branch off fresh `main` → **TDD red→green only if the slice touches a `.py` module** (S1 = docs/UI/
gitignore → none; the S2 build script → yes) → implement → mutators (`ruff --fix`/format) → **gate LAST**
(`make check` + `markdownlint-cli2 --no-globs` on changed md) → commit by topic (`--no-gpg-sign`) →
`env -u GH_TOKEN -u GITHUB_TOKEN git push` (`gh auth setup-git` once) → PR → `gh pr checks <n> --watch` →
`gh pr merge <n> --squash --admin --delete-branch` → prune local. Issue comments via `gh` (no branch).

## Gotchas (this environment)

- All `gh`/`git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN` (bare `gh` 401s).
- **Changelog:** Slice 1 + #260 are **exempt** (docs/CI-config, CONTRIBUTING §Changelog); Slices 2 & 3
  each need a `make changelog_new` fragment (`mkdir -p changelog.d` first if empty).
- **`ui/` has no JS unit tests** (no-build vanilla) — verify with `make ui-check` (needs
  `POLYFETCH_DIR=../polyfetch-scrape`) + a headless e2e via polyfetch's patchright venv.
- markdownlint: MD004 (a wrapped line starting `+`/`-`), MD049 (match the file's italic). CI
  `lint/markdown` 429s intermittently (re-run); `lint/links` runs whole-repo lychee.
- Company tracker stays **local-only** (the `data`-branch boundary guard forbids company/PII data); a
  published version needs an ADR-0002 ToU review + PII scrub first.

## Touch points (pre-sprint snapshot — Sprints 1–2 now shipped; verify against `main` before relying)

| File | Current state |
|---|---|
| `ui/src/trends.js` | `loadRealTrends` fetches **only** weekly `trends.ndjson`; `pivot`/`renderTrends`/`windowRecords` hard-code `.week`. No daily/monthly wiring; the `<select>` is a time-window, not granularity. |
| `ui/src/shortlist.js` | `renderShortlist` row template has 5 `<td>` (company/title+rationale/lane/score/verdict); **no** `deadline`/`deal_breaker` rendering; no `stale` UI precedent. |
| `ui/src/style.css` | has `.lane`/`.score`/`.verdict` pills + `--data-caution`/`--data-negative` tokens; **no** `.due`/`.deal-breaker` classes yet. |
| `ui/public/data/demo.json` | shortlist items lack `deadline`/`deal_breaker`. |
| `public-data/*.ndjson` (data branch) | `trends.ndjson` weekly (only W26–W28 after the reset), `trends-daily.ndjson`, `trends-monthly.ndjson` all published; UI ignores the latter two. |
| `.gitignore` | ignores `.venv`/`.pytest_cache`/`.ruff_cache`/`.coverage`; **missing** `.env`, `.complexipy_cache/`, `.hypothesis/`. |
| `src/ajoa_kit/settings.py` | `AppSettings` reads `.env` (`env_file=".env"`) — undocumented + un-gitignored. |
| `CONTRIBUTING.md` | env table has 6 rows; **no** `.env` row. |
| `docs/roadmap.md` | no #271 bullet; the ADR-0003 "Later" line still lists the (shipped) "relevance" boundary. |
| `README.md` | `## Why` sits after `## How`; badges lack coverage + python. |
| `AGENT_LEARNINGS.md` | root file, **zero inbound references**. |
| `scripts/build_ui_shortlist.py` | the aggregate-for-preview pattern to mirror for the company tracker. |
| `.github/workflows/gh-pages.yaml` | deploys on every `main` push; `ingest-daily.yaml` dispatches it explicitly. |
| GitHub issues | #187/#188/#191 open (comment); **no** issue yet for dashboard flags or the company tracker (open both). |
