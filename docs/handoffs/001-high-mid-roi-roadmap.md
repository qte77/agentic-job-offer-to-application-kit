# Handoff 001 — high/mid-ROI issue roadmap

**State:** `main` @ `678e41e`, clean, synced. Roadmap: [docs/plans/001-high-mid-roi-roadmap.md](../plans/001-high-mid-roi-roadmap.md).

**Done this session:** #212 (merged PR #218), #201 (closed with a quality rubric), #209 (merged PR #219).
Also opened #217 (seed `_date_verified` backfill + scheduled freshness re-probe).

## Resume here (in order)

1. **#195** — `config/lanes.json` + `load_lanes()` in `ingest.py` (mirror `load_keywords:130`), **TDD**
   in `test_ingest.py`; slim the two JS lane fallbacks to "mirrors config/lanes.json". Branch
   `feat/lanes-config`. `git add -f config/lanes.json`.
2. **#214** — `cfg.lane` filter (`ACTIVE_LANES`) in `cc-workflow-relevance.js` (glue, `node --check`).
   After #195. Document the new arg + re-bucket rule.
3. **#210** — `trend_snapshot.py:279-280` → `public-data/` (**TDD** the writer) + Makefile/gh-pages/
   ingest-daily/.gitignore glue + `trends-data` tree-allowlist guard.
4. **#193** — blocked; act only after `qte77/.github#33` merges.

PARKED (don't build proactively): #195-JobRecord, #199.

## Per-slice recipe

branch off `main` → TDD (modules only; glue/JS/docs get none) → `make check` + `make docs-lint` →
CHANGELOG fragment (`changelog.d/`) + doc impact → push (`env -u GH_TOKEN -u GITHUB_TOKEN git push`) →
PR → **squash-merge on green** (`--squash --admin --delete-branch`) → sync `main`.

## Gotchas

- `git add -f` for `config/*` (tracked-but-gitignored since #213).
- Flaky `lint / links` (lychee) → `gh run rerun <run-id> --failed`, then merge.
- Local `make docs-lint` errors are all `results/**` (git-ignored artifacts; CI is clean) — verify your
  changed `.md` alone passes lychee.
- All `gh`/`git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN`. Avoid `tail`/`cat`/`head`/`grep |`/
  `;`-chains/`sleep`-chains in Bash (denied here).
- ruff line-length = 100.
