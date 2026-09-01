# Plan 001 — high & mid-ROI issue roadmap

> Status: 2026-06-30. From the approved plan-mode plan over the open-issue ROI/feasibility pass.
>
> **Status: SHIPPED (confirmed 2026-09-01).** All 4 tracked items closed: #195, #214, #210, #193 —
> the last three picked up via plan 002; #195 via ADR-0003. This file predates this repo's
> SHIPPED-stamp convention (plans 004+); retroactively confirmed rather than left stale.

## Progress

- ✅ **#212** expand `default-seed.json` (+52 ATS + Berlin RSS) — merged (PR #218 → `ae37fea`).
- ✅ **#201** validate e2e output quality — closed with a quality rubric (this session's real-data e2e).
- ✅ **#209** real shortlist → local dashboard — merged (PR #219 → `678e41e`).
- ⬜ **#195** `config/lanes.json` single lane source (lanes.json half only) — **next**.
- ⬜ **#214** focused per-lane runs (`cfg.lane`) — after #195.
- ⬜ **#210** relocate publishable trends → `public-data/` + guard.
- ⏸ **#193** reusable release workflows — GATED on `qte77/.github#33` (watch).
- ⏸ PARKED (build only on a real trigger): **#195 JobRecord** half, **#199** ats-parser grounding.
- Out of scope (batchable quick-wins): #197, #188, #187.

## Conventions (every slice)

- Branch per issue off `main`; commit by topic (`git commit --no-gpg-sign`); push; **squash-merge on
  green** (`gh pr merge <n> --squash --admin --delete-branch`).
- **TDD red→green for MODULES only** (`src/ajoa_kit/*.py`). No tests for L3 workflow scripts
  (`.claude/workflows/*.js` → `node --check`), L4 `ui/`, Makefile/CI/`.gitignore` glue, `scripts/`
  glue, config JSON, docs.
- Gates: `make check` (ruff line-length **100** + ruff-format + pyright `src/ajoa_kit` + complexipy ≤10 +
  offline pytest cov≥80) and `make docs-lint`.
- Docs/switches per issue: CHANGELOG (scriv fragment under `changelog.d/`, NOT lint-checked) · README ·
  architecture · roadmap · userstory · URL/env/CLI switches.

## Remaining work — exact touchpoints

### #195 — config/lanes.json (JobRecord half PARKED)

- Add tracked `config/lanes.json` = canonical `[{key,label,focus,gapHint}]` (the 7 lanes hardcoded in
  `cc-workflow-evidence-library.js:49`).
- Add `load_lanes(config_dir)` in `src/ajoa_kit/ingest.py` mirroring `load_keywords` (`ingest.py:130`:
  optional override → hardcoded `DEFAULT_LANES` fallback). **MODULE → TDD** in `tests/test_ingest.py`
  (override read; default when absent).
- Both workflow scripts already guard `(cfg.lanes && cfg.lanes.length)` (`evidence-library.js:49`,
  `relevance.js:49`) → operator passes the loaded array as `cfg.lanes`; slim the JS fallbacks to a
  "mirrors config/lanes.json" comment.
- `config/lanes.json` is tracked-but-gitignored (post-#213) → **`git add -f`**.
- Docs: `architecture.md` (`:109` backlog line + §Data-contracts), `CONTRIBUTING.md` config-file list,
  CHANGELOG.

### #214 — focused per-lane runs (`cfg.lane`); after #195

- `cc-workflow-relevance.js`: `const LANE_FILTER = cfg.lane || null` then
  `const ACTIVE_LANES = LANE_FILTER ? LANES.filter(k => k === LANE_FILTER) : LANES`; use `ACTIVE_LANES`
  in `RESULT` enum (`:68`) + `gatePrompt` (`:87`). Glue → `node --check`, no test.
- Document the re-bucket rule (adding/removing a lane ⇒ full relevance re-run) + the new `cfg.lane` arg
  (relevance.js header, CONTRIBUTING/quickstart, architecture §Position lanes, CHANGELOG).

### #210 — relocate publishable trends → `public-data/` + guard

- `src/ajoa_kit/trend_snapshot.py:279-280`: write to `public-data/` not `results/` (add
  `AppSettings.public_data_dir` / `AJOA_PUBLIC_DATA_DIR`). **MODULE → TDD** (output-path test, mirror
  `test_trend_snapshot.py:147` tmp_path+monkeypatch).
- Glue (no test): Makefile `trends-data` (`:103` — `git add -f public-data/…` + tree-allowlist guard) +
  `preview` (`:79`); `.github/workflows/gh-pages.yaml:61`; `ingest-daily.yaml:86`; `.gitignore`
  add `public-data/`.
- Docs: architecture (Data-layout, PII boundary `:145`, contracts), CONTRIBUTING (+env), CHANGELOG.

### #193 — reusable release workflows (GATED)

- When `qte77/.github#33` merges: replace inline `bump-my-version.yaml` + `tag-release.yaml` with
  `uses: qte77/.github/.github/workflows/{bump-version,tag-release,publish}.yml@<SHA>` (mirror
  `lint-md-links.yml:17`; pin full SHA). actionlint, no test.

## Backlog (post-run review — fold-ins)

Lower-priority items surfaced this session; batch into the relevant slice or a cleanup PR.

### Quick wins

- **`!results/**` in the markdownlint-cli2 config** — its globs are `**/*.md` without excluding the
  git-ignored `results/`, so local `make docs-lint` fails on `results/` artifacts (CI is clean). One
  line; makes local docs-lint trustworthy again.
- **#197** — `ScoredItem` `extra="ignore"` → `"allow"` (`src/ajoa_kit/models.py:25`): one line + one
  round-trip test in `tests/test_persist_scored.py`. MODULE → TDD.

### Cleanups / deletions

- **Stale `#52` references** — `#52` is closed but still cited as an active gate in `docs/roadmap.md:81`
  and `docs/architecture.md:224` (the `app.js` header was fixed in #209). One-line sweep.
- `docs/architecture.md` "Built" bullet now says "`make preview`" twice (the #209 edit) — cosmetic.

### Enhancements

- **#209 v2 (shipped)** — the local shortlist expand now shows the tailored CV + cover letter:
  `persist_offer` writes a `results/offers/<slug>/meta.json` (JD id) and `attach_tailor_docs` joins the
  pack back to each shortlist row by id (robust to a custom `--slug`). Original spec in the
  [#209 comment](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/209#issuecomment-4844914822).
- Reconsider the `config/*` `git add -f` friction (post-#213): if hand-editing the seed / `lanes.json`
  annoys, re-add just `!/config/default-seed.json` (+ `!/config/lanes.json`) — buys it back for two
  files without resurrecting the full re-include dance.

## Gotchas

- `config/default-seed.json` (and future `config/lanes.json`) are tracked-but-gitignored after #213 →
  `git add -f`.
- `lint / links` (lychee) is flaky on whole-repo external links → re-run the failed job
  (`gh run rerun <run-id> --failed`).
- Local `make docs-lint` fails on `results/**` artifacts (markdownlint config globs `**/*.md` without
  `!results/**`); CI is clean (no `results/` in a fresh checkout). *Follow-up: add `!results/**`.*
- gh + git push need `env -u GH_TOKEN -u GITHUB_TOKEN`. Denied bash here:
  tail/cat/head/`grep|`/`;`-chains/sleep-chains/`ls`/`--watch`.
- Opened this session: **#217** (backfill `_date_verified` + scheduled source freshness re-probe).
