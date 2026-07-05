# Handoff 003 — deploy hygiene + hardening + StyleBrief typing

**State:** `main` clean, synced (post PR #258). Plan (approved, with full source map):
[docs/plans/003-deploy-hygiene-hardening-typing.md](../plans/003-deploy-hygiene-hardening-typing.md).
**Nothing of plan 003 is implemented yet** — three PRs, execute in order.

**Session context (2026-07-05, all shipped):** Wave 1 `verify-sources` + seed backfill (#217½,
PR #247) · Wave 2 monthly trends data layer (#188½, PR #248) · refactor epic #249 closed via
PRs #250/#253/#254 (models → `models.py`; `defaults.py` + tracked `config/keywords.json` SSOT;
`ingest.py` split into `sources.py` / `normalize.py`; `TRENDS_PUBLISH` + shrink guard; `app.js` →
orchestrator + 3 ES modules) · cron heal (#252, `defusedxml` `--with` trio) · button contrast fix
(#255, `appearance: none`, reporter-confirmed) · footer version (#258, bump-managed) · plugins repo:
`triaging-security-report` skill v1.2.0. Issues #251/#256/#257 were filed from this session's
evidence — plan 003 closes all three.

## The three PRs (detail + source map in the plan — don't re-explore)

1. **`fix/deploy-hygiene`** (closes #251): delete gh-pages.yaml's `paths:` block; fix the stale
   "no redeploy" claim in CONTRIBUTING + ui/README; add `TRENDS_FORCE` to the CONTRIBUTING env
   table; add the missing #249 epic bullet + a reliability line to roadmap; 1-line `Fixed` fragment.
   **Glue only — zero tests.**
2. **`harden/batch`** (closes #256): TDD scheme guard on `sources.get_json/get_bytes`
   (`ValueError` on non-http(s); `slug_probe` untouched — different contract); new
   `tests/test_persist_offer.py` pinning `safe_slug` (examples + small Hypothesis property);
   token-out-of-argv credential-helper swap in gh-pages.yaml (exact snippet in the plan);
   `Security` fragment. **Verify by a real dispatched deploy** — the credential swap is only proven
   by an actual push.
3. **`refactor/style-brief`** (closes #257): pin `ajoa-kit style --json` stdout byte-for-byte
   FIRST (green→green — the swap can't change it: `as_directives` hand-builds the dict), then
   `StyleBrief` → pydantic in `models.py`; `style.py` re-imports it (zero test churn);
   architecture contracts-table row; `Changed` fragment.

## Per-slice recipe

branch off fresh `main` → (PR 2/3) tests first → implement → **gate LAST** (`make check`; changed
docs via `markdownlint-cli2 --no-globs <files>`) → CHANGELOG fragment → commit by topic
(`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN git push` → PR with `Closes #n` →
`gh pr checks <n> --watch` → `gh pr merge <n> --squash --admin --delete-branch` → prune local
branch → sync `main` before the next PR.

## Gotchas (this environment)

- All `gh` / `git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN` (bare `gh` 401s;
  `gh auth setup-git` once per session before the first push).
- **Gate runs LAST**: run `ruff --fix` / formatters BEFORE `make check`; any edit *after* the gate
  (even a comment) → re-run the full gate. (Two CI reds this session from skipping this.)
- Borrowed polyfetch venv for live/import checks:
  `PYTHONPATH=src AJOA_CONFIG_DIR=config uv run --directory ../polyfetch-scrape --with pydantic
  --with pydantic-settings --with defusedxml python -m ajoa_kit <verb>` (all three `--with` needed;
  `defusedxml` is no longer transitive from polyfetch).
- Denied Bash here: `tail`/`cat`/`head`/`grep`-with-pipe/`-A`/`ls`/`find`/`;`-chains/`sleep` — use
  Read/Grep tools and `&&`-chains; write long command output to the scratchpad then Read it.
- `make ui-check` needs `POLYFETCH_DIR` (patchright); it now allowlists the by-design
  `shortlist.json` 404. ruff line length = 100; complexipy max = 10/function.
- Pages deploy can wedge (stuck `building`) — recovery in #251 comments; a raw `polyfetch.fetch` of
  an expected `src/*.js` beats render checks for "is the split actually live" (a stale bundle
  renders identically).

## Next / open (post-plan-003)

- **Wave 3** (#187 + #188 UI half): Daily/Monthly dropdown + same-origin bundles + synthetic-data
  banner, built on the now-isolated `ui/src/trends.js`. Do once ~3–4 wks of daily data accrue.
- **Deferred/parked (leave open):** #195 (JobRecord half), #217 (scheduled re-probe). **Blocked:**
  #193 (`qte77/.github#33` still OPEN). **Decision pending:** #199 (recommend close as declined).
- **Plugins repo:** #190 (OWASP-LLM skill + ATLAS→`securing-mas`; recon attached — ATLAS half is a
  copy/reformat from `ai-agents-research/docs/sdlc-lcm/ai-security-governance-analysis.md`).
- **`temp/docs/`** (outside repo): PDF-author feedback + live-verification report — owner to send.

## Touch points (current state — verify, don't re-map)

> Pre-implementation snapshot. Full symbol-level source map is in the
> [plan](../plans/003-deploy-hygiene-hardening-typing.md#source-map-verified-2026-07-05--symbol-anchors-no-line-numbers-re-verify-before-editing).

| PR | File | Current state to verify against |
|---|---|---|
| 1 | `.github/workflows/gh-pages.yaml` | `on.push` has `branches: [main, data]` **+ a `paths:` list** → delete the list. |
| 1 | `CONTRIBUTING.md` / `ui/README.md` | both carry "no redeploy" wording; CONTRIBUTING env table lacks `TRENDS_FORCE`. |
| 1 | `docs/roadmap.md` | Shipped list ends at the Wave-2 monthly bullet — **no #249 epic bullet**. |
| 2 | `src/ajoa_kit/sources.py` | `get_json`/`get_bytes` — no scheme guard; lazy `polyfetch_scrape` import inside; raise `FetchError` on non-200. |
| 2 | `tests/test_fetch.py` | fakes `polyfetch_scrape` via `monkeypatch.setitem(sys.modules, …)` — copy for scheme tests. |
| 2 | `src/ajoa_kit/persist_offer.py` | `safe_slug` = `_NON_SLUG.sub("-", raw.lower()).strip("-")`, raises on empty. **`tests/test_persist_offer.py` absent** → the pin creates it. |
| 2 | `.github/workflows/gh-pages.yaml` | publish step pushes via `https://x-access-token:${GH_TOKEN}@…` → credential-helper swap. |
| 3 | `src/ajoa_kit/style.py` | `@dataclass StyleBrief(tone, cv_sample, cover_letter_sample = "")`; `as_directives` hand-builds `{cv, coverLetter}` (dataclass never serialized); only `style.py` + `test_style.py` reference it. |
| 3 | `src/ajoa_kit/models.py` | holds Lane/ScoredItem/Week/Day/MonthCounts → StyleBrief joins; docstring enumerates the family. |
| 3 | `tests/test_style.py` | 5 examples + 1 property; **no `main(as_json=True)` stdout pin** → the new test adds it. |
