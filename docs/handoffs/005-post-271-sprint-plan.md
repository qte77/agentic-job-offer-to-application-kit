# Handoff 005 — post-#271 sprint (docs hygiene · trends-UI · flags · market-intel)

**State (2026-07-11):** `main` green at `e98de56`. **Sprint 1 SHIPPED** (#282/#285/#286, fixes #287/#289/#290);
`complexipy` pinned `<6` (#288 — **must stay <6**). Deep `posted_at` trends published to `data`
(171/545/58). Open: **#284** tracker (resume here), **#292** discovery sources. Plan (approved,
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

Nothing yet — this handoff + plan are the first artifacts. Context already gathered (in the plan's
source map): the trends-loss diagnosis, the UI/switch/README/root audit, and the tracker feasibility.

## Resume here (in order)

1. **Slice 1 — docs/hygiene closeout** (branch `docs/audit-hygiene`, changelog-EXEMPT): `.gitignore`
   `.env`+cache dirs · `CONTRIBUTING` `.env` env-row · `roadmap.md` #271 bullet + trim stale "relevance"
   line · `README` move `## Why` up + coverage/python badges · `AGENTS.md` pointer to `AGENT_LEARNINGS.md`.
2. **Slice 5 — issue comments** (no branch, `gh`): #191 (trend-loss + keep-stopgap), #187/#188
   (published-but-unwired). Do early so the context is captured.
3. **Slice 2 — trends-granularity UI** (`feat/trends-granularity`, needs a changelog fragment): add a
   week|day|month `<select>`; thread the `.week`/`.date`/`.month` label-key through `pivot`/`renderTrends`/
   `windowRecords`. Verify `make ui-check` + e2e.
4. **Slice 3 — dashboard flags** (`feat/ui-shortlist-flags`, fragment): badges in the Role cell + `.due`/
   `.deal-breaker` pills + demo.json rows.
5. **Slice 4 — #260 eval** (chore): may end "leave it"; document on #260.
6. **Sprint 2 — company tracker MVP**: open the issue first (with the ToU/PII notes); then the build
   script (a module → **TDD it**) + a local-only preview view.

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

## Touch points (current state — verify, don't re-map; line-level detail is in the plan)

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
