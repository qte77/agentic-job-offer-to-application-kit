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
