# Handoff 004 — #271 relevance fit rubric (LEAN)

**State:** `main` clean at `e8238d7`, synced. **Implemented in #271** (scope expanded 2026-07-09 — typed `ScoredItem` end-to-end, see plan). Plan (approved,
lean scope, with full symbol-level source map):
[docs/plans/004-relevance-fit-rubric.md](../plans/004-relevance-fit-rubric.md) — **read it; don't
re-map the codebase**, the source map is there.

> A cloud (Ultraplan) session was launched to refine this plan. If an owner-approved refined version
> exists, reconcile against it first; otherwise the lean plan above is canonical.

## What this is (one paragraph)

Make the relevance screen's output **explainable** for the human at GATE 2. Two additive changes, no
behaviour change to scoring/dropping: (1) the L3 workflow `cc-workflow-relevance.js` enriches its
`rationale` to name the fit dimensions (skill / experience / culture-location / progression /
motivation) in prose and emits two optional structured fields — `deadline` and `deal_breaker`; (2)
`persist_scored.write_lane` surfaces those two flags in `shortlist.md`. Scope was expanded 2026-07-09:
`ScoredItem` gains typed `deadline`/`deal_breaker` and the persist/refresh pipeline now carries
`list[ScoredItem]` end-to-end (`extra="allow"` stays, #197). The 5 numeric sub-scores and config-driven tunability were
**deliberately deferred** (YAGNI) — see the plan's Out-of-scope.

## How to execute (per-slice recipe)

1. Branch `feat/relevance-rubric` off fresh `main`.
2. **TDD first** (`tests/test_persist_scored.py`, extend `_item`/`_run` + the #197 round-trip test):
   round-trip `deadline`/`deal_breaker` into `jobs-scored.json` + `shortlist.json`; render assertion on
   `shortlist.md`. Confirm red.
3. Implement: `persist_scored.write_lane` render (green) → then the JS schema+prompt (glue, no JS test).
4. `Changed` changelog fragment (`make changelog_new`; `mkdir -p changelog.d` first if empty after a
   release); architecture.md Shortlist-row note.
5. Mutators (`ruff --fix`/format) → **gate LAST** (`make check`; `markdownlint-cli2 --no-globs` on
   changed md). Any post-gate edit → re-run the full gate.
6. Commit by topic (`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN git push` → PR **`Closes #271`**
   → `gh pr checks <n> --watch` → `gh pr merge <n> --squash --admin --delete-branch` → prune local.

## Gotchas (this environment)

- All `gh` / `git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN` (bare `gh` 401s; `gh auth setup-git`
  once per session before the first push).
- **Gate runs LAST**; run mutators before it. Keep `write_lane` ≤10 complexity (complexipy).
- **No JS tests** — `cc-workflow-relevance.js` is glue; the `RESULT` schema enforces shape at runtime,
  verified live. Don't add a JS harness.
- The relevance workflow can't run in CI (LLM). Prove the persist path offline via the canned e2e
  fixture (#165); optionally drive one real `cc-workflow-relevance.js` run via the Workflow tool.
- markdownlint traps on docs: MD004 (a wrapped line starting `+`/`-`), MD049 (emphasis-style is
  *consistent* — match the file's existing italic). CI `lint/markdown` also 429s intermittently on the
  shared config fetch — just re-run the job.

## Touch points (current state — verify, don't re-map; line-level detail is in the plan)

| File | Current state |
|---|---|
| `.claude/workflows/cc-workflow-relevance.js` | `RESULT` item schema has `id/title/company/best_lane/score/verdict/rationale/url` (no `deadline`/`deal_breaker`); `gatePrompt` scoring line enumerates the returned fields. |
| `src/ajoa_kit/persist_scored.py` | `write_lane` renders `shortlist.md` with an explicit `tag` (`score/verdict` + `· stale`) + title@company / url / rationale bullets — no flag surfacing yet. |
| `src/ajoa_kit/models.py` | `ScoredItem` gains typed `deadline`/`deal_breaker` (#271); persist/merge/refresh carry `ScoredItem` end-to-end, `extra="allow"` stays (#197). |
| `tests/test_persist_scored.py` | has `_item`/`_run` helpers + `test_unknown_result_field_survives_round_trip` (the template); no `deadline`/`deal_breaker` test yet. |
| `changelog.d/` | empty after the v0.6.1 release — `mkdir -p changelog.d` before `make changelog_new`. |

## Deferred (out of scope — track on #271 or a new issue)

Numeric per-dimension sub-scores; config-driven criteria file (`config/relevance-criteria.json` +
`DEFAULT_CRITERIA` + `load_criteria` + `ajoa-kit criteria --json` → `args.criteria`), mirroring the
`../agentic-market-research-to-gtm` `config/validation_criteria.md` pattern for tunable weights /
verdict thresholds / deal-breaker rules.
