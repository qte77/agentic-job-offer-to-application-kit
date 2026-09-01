# Plan 002 — refresh completion + lane-check (+ a lint one-liner)

> Status: 2026-06-30. From the ROI/feasibility pass over the open issues (handoff-001 roadmap shipped).
> Tier 1 + 2, minus the two items deferred on a KISS/YAGNI review.
>
> **Status: SHIPPED (confirmed 2026-09-01).** All 4 tracked items closed: #226, #227, and the two
> originally YAGNI-deferred (#197, #217) both shipped later anyway. Retroactively confirmed —
> predates the SHIPPED-stamp convention plans 004+ use.

## Context

Handoff-001 (#195 lanes · #214 refresh · #210 public-data · #222 CI) is shipped. A fresh ROI pass over
the 9 open issues clustered them; the user picked Tier 1 + 2 to execute, then **deferred #197 and #217**
on YAGNI grounds:

- **#197** flips `ScoredItem` to `extra="allow"`, but the issue itself notes no result field is dropped
  today — pure forward-compat speculation. Flip it when a field actually lands.
- **#217** (scheduled source re-probe) — the issue itself calls it "low-stakes, not urgent", and a
  normal `ingest` run already lists dead sources in `results/jobs-raw.summary.md` ("Failed").

The remaining, genuinely-earning work:

- **#226** — complete the refresh feature: cheaply screen only *new* offers (the "scan new" half whose
  "check still valid" half shipped in #214 / #224).
- **#195a** — give the #195 lane loader a real consumer that fixes a real bug (a hallucinated
  `best_lane` silently spawns a junk `results/<bogus>/` directory).
- **#227b** — one-line lint-config fix so local `make docs-lint` stops failing on git-ignored `results/`.

Emphasis: strict TDD (model the behavior as tests first, then implement); tests for `src/ajoa_kit/*.py`
modules only, non-trivial; CLI dispatch / config get no test. Strict lint + typing + sec; ruff len 100.

## Per-slice recipe

Branch off `main` → behavior tests (red) → implement (green) → `make check` + `make docs-lint` →
CHANGELOG fragment + doc impact → push (`env -u GH_TOKEN -u GITHUB_TOKEN`) → PR → squash-merge on green
→ sync `main` → checkpoint. **#226 → #195a** both touch `persist_scored.py`, so do them sequentially.

## Slice 1 — #226 incremental new-offer delta-screen

### Behavior (TDD first)

- `test_chunk_new_batches_only_the_delta` — `corpus.json` with mixed `first_seen`; `chunk(new=True)`
  batches only entries whose `first_seen == max(last_seen)`; `manifest.batch_count` equals the delta
  count; `jobs-raw.json` is left untouched.
- `test_chunk_new_fails_loud_without_corpus` — `new=True` and no `corpus.json` raises (clear message).
- `test_persist_merge_unions_into_existing_buckets` — an existing `results/ml/shortlist.json` plus a
  merge result with a *new* `ml` id and an *updated* existing id yields the union by id (existing kept,
  new added, same-id wins for the new item); a lane absent from the delta is untouched.
- `test_persist_merge_unions_jobs_scored` — `results/jobs-scored.json` `relevant[]` unions by id too.

### Implementation

- `src/ajoa_kit/chunk.py` — `main(batch, *, new=False)`: when `new`, read `results/corpus.json`, take
  `latest = max(last_seen)`, set `jobs = [r for r if first_seen == latest]`; else read `jobs-raw.json`
  (current). Reuse the existing batch loop + manifest. v1 is `first_seen`-new only; re-screening
  `changed` entries is a noted follow-up.
- `src/ajoa_kit/persist_scored.py` — `merge_shortlists(rel, results_dir)` (union by id into each
  existing per-lane bucket, then `write_lane`) plus `main(src, *, merge=False)` (merge unions into the
  buckets and `jobs-scored.json` `relevant` by id; otherwise the current overwrite). Reuse `write_lane`.
- `src/ajoa_kit/__main__.py` — `chunk --new`, `persist --merge` (glue, no test).

### Docs / switches

New CLI flags `chunk --new` / `persist --merge` documented in the CONTRIBUTING CLI table plus the
quickstart refresh-cycle recipe (`ingest --merge` → `refresh` → `chunk --new` → relevance →
`persist --merge`), an architecture pipeline note, and a CHANGELOG fragment. Close #226.

## Slice 2 — #195a `persist_scored` lane-membership check

### Behavior (TDD first)

- `test_persist_routes_hallucinated_lane_to_unsorted` — an item whose `best_lane` is not in
  `load_lanes()` lands in `results/unsorted/` (never a junk `results/<bogus>/` dir) and is tallied as
  invalid; a valid `best_lane` still buckets normally.

### Implementation

- `src/ajoa_kit/persist_scored.py` `main()` — `valid = {l.key for l in load_lanes(config_dir)}`; before
  bucketing, blank any `best_lane` not in `valid` (the existing `… or "unsorted"` routes it to
  `unsorted/`) and tally an invalid count for the summary line. Keeps the scored JD, drops only the
  hallucinated lane — and makes `ingest.load_lanes` a live consumer.

### Docs

CHANGELOG plus a comment on #195 (lane-check shipped; the JobRecord half stays parked — the JD record
is Python-produced and -consumed, so always well-formed). Keep #195 open.

## Slice 3 — #227b markdownlint `results/**` exclusion

Config only, no test: `.markdownlint-cli2.jsonc` adds `"results/**"` to `ignores` (joining
`node_modules` / `.git` / `.venv` / `changelog.d`), so local `make docs-lint` stops failing on
git-ignored `results/<lane>/shortlist.md`. Changelog-exempt. Comment on #227 (markdownlint done; the #52
sweep still needs a decision and remains open).

## Doc-impact and switch matrix

| Slice | CHANGELOG | CONTRIBUTING | quickstart | architecture | new switches |
|---|---|---|---|---|---|
| #226 | yes | CLI rows | refresh-cycle recipe | pipeline note | CLI `chunk --new`, `persist --merge` |
| #195a | yes | — | — | contracts (lane-check) | — |
| #227b | exempt | — | — | — | — |

README / roadmap / userstory / env / url need no changes — the refresh cycle is already storied as US7,
and all new switches are CLI (documented in CONTRIBUTING / quickstart).

## Issues

Close #226 on merge; keep #195 open (comment); #227 stays open (markdownlint done → comment, #52 sweep
needs a decision); #197 and #217 deferred (left open with a YAGNI note). No new issues.

## Verification

- Per slice: `make check` (ruff + ruff-format + pyright + complexipy ≤ 10 + offline pytest cov ≥ 80)
  and `make docs-lint`.
- #226 offline: a tmp `corpus.json` (one new + one old `first_seen`) → `chunk --new` batches only the
  new one; persist a first result, then `persist --merge` a second → the bucket is the union (no clobber).
- #195a: persist a result with a bogus `best_lane` → no `results/<bogus>/` dir; the JD lands in
  `unsorted/`.
