# Handoff 002 — refresh completion + lane-check

**State:** `main` clean, synced. Plan: [docs/plans/002-refresh-completion-lane-check.md](../plans/002-refresh-completion-lane-check.md).

**Done (handoff-001 roadmap, shipped):** lanes SSOT (#195, PR #223), refresh liveness (#214 / #224),
trends relocated to `public-data/` with a data-branch guard (#210 / #225), the CI markdown unblock
(#222), and the doc-gap closes (#228). Follow-ups opened: #226, #227. This plan came from the ROI pass
over the 9 open issues (Tier 1 + 2, minus deferred #197 / #217).

## Resume here (in order)

1. **#226** — delta-screen. `chunk.py` `main(batch, *, new=False)` (batch the `first_seen == max(last_seen)`
   corpus delta) + `persist_scored.py` `merge_shortlists` / `main(src, *, merge=False)` (union by id,
   reuse `write_lane`) + `__main__` `chunk --new` / `persist --merge`. **TDD** the two modules. Branch
   `feat/delta-screen`. Close #226.
2. **#195a** — lane-check. After #226. `persist_scored.main()` blanks any `best_lane` not in
   `load_lanes()` → routes to `unsorted/` (no junk `results/<bogus>/` dir) + tallies invalid. **TDD**.
   Branch `feat/lane-check`. Keep #195 open (comment).
3. **#227b** — one line: add `"results/**"` to `.markdownlint-cli2.jsonc` `ignores`. No test, exempt.
   Comment on #227.

**Deferred (YAGNI; left open):** #197 (no field dropped today), #217 (not urgent; `ingest` already
reports dead sources). **Gated:** #193 (`qte77/.github#33` open). **Needs a decision:** #227 #52 sweep
(is `pseudonymize-text` dropped or deferred?).

## Per-slice recipe

branch off `main` → TDD red→green (modules only) → `make check` + `make docs-lint` → CHANGELOG fragment
(`changelog.d/`) + doc impact → push (`env -u GH_TOKEN -u GITHUB_TOKEN git push`) → PR → squash-merge on
green (`gh pr merge <n> --squash --admin --delete-branch`) → sync `main`.

## Gotchas

- `git` rebase signs commits → use `git -c commit.gpgsign=false rebase`; commits use `--no-gpg-sign`.
- All `gh` / `git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN`. Denied Bash here: `tail`/`cat`/`head`/
  `grep |`/`;`-chains/`sleep`/`ls`/`find`.
- Local `make docs-lint` fails on `results/**` artifacts until #227b lands — verify a changed `.md`
  alone with `markdownlint-cli2 --no-globs <file>`.
- Flaky `lint / links` (lychee) → `gh run rerun <run-id> --failed`, then merge. ruff line-length 100.

## Touch points (current state)

Target signatures + the delta algorithm are in the [plan](../plans/002-refresh-completion-lane-check.md);
this table is only the **current-state** anchor, so a resuming agent verifies known points instead of
re-mapping. Paths + symbols, no line numbers (they drift) — verify before editing.

| Slice | File | Current state to verify against |
|---|---|---|
| #226 | `src/ajoa_kit/chunk.py` | `main(batch=DEFAULT_BATCH=40)`, reads `results/jobs-raw.json` wholesale, single func, no delta. `chunk.main(batch=40)` is called by keyword in `tests/test_e2e_pipeline.py` → a keyword-only `new` stays back-compat. |
| #226 | `src/ajoa_kit/persist_scored.py` | `main(src=None)`; `write_lane(lane, items, results_dir)` already shared with `refresh.py`; `write_shortlists` full-overwrites via `by_lane.setdefault(best_lane or "unsorted", …)`; no `merge_shortlists` yet. `ScoredItem` (`models.py`) is `extra="ignore"`, union key = `id`. |
| #226 | `src/ajoa_kit/__main__.py` | `_chunk`→`run(batch=…)`, `_persist`→`run(src=…)`; `chunk` parser has only `--batch-size`, `persist` only positional `FILE`. |
| #226 | `results/corpus.json` | records carry `first_seen`/`last_seen`/`content_hash` (`corpus.py::merge_corpus`); flat JSON array. |
| #226 | tests | **`tests/test_chunk.py` does not exist** (only indirect e2e coverage) — the two delta tests create it. `tests/test_persist_scored.py` has `_item`/`_run` helpers (`AJOA_RESULTS_DIR` + `tmp_path`/`capsys`). |
| #195a | `src/ajoa_kit/ingest.py` | `load_lanes(config_dir) -> list[Lane]` (extract `{ln.key for …}`); `config/lanes.json` = cxo/founding/engineering/ml/fde/cloud/architect; **not yet imported by `persist_scored.py`**. |
| #227b | `.markdownlint-cli2.jsonc` (root) | `ignores` = node_modules/.git/.venv/changelog.d — add `"results/**"`. |
