# Contributing

This guide is for **human contributors**. The full command reference — run, dev, and release — is in
[§Commands](#commands) below; for the project overview see [README.md](README.md); for the
machine-facing rulebook — principles, constraints, quality gates, and the value-add-TDD rule — see
[AGENTS.md](AGENTS.md).

## Commands

The **Makefile is the source of truth** for commands — `make help` lists every target. This section
documents them; the rest of the docs link here instead of repeating commands.

### Dev loop

```bash
make install     # sync the dev environment (uv)
make check       # ruff + format-check + pyright + complexipy + offline pytest + coverage (CI parity)
make docs-lint   # markdownlint + lychee link check
```

### Pipeline

The full per-search run. The orchestration steps run via the Claude Code Workflow tool — see each
script's header in [`docs/workflows/`](docs/workflows/) for the exact `args`:

```bash
POLYFETCH_DIR=../polyfetch-scrape make ingest         # -> results/jobs-raw.json
make chunk                                            # -> results/batches/ + manifest.json
# relevance (Workflow tool) — batchCount = results/batches/manifest.json .batch_count:
#   Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js", args: { rootDir: ".", batchCount: <N> } })
make persist FILE=<workflow-output.json>              # -> results/<lane>/shortlist.*
# tailor one shortlisted offer (Workflow tool):
#   Workflow({ scriptPath: "docs/workflows/cc-workflow-tailor-offer.js", args: { rootDir: ".", lane: "engineering", offerId: "<id>" } })
uv run ajoa-kit persist-offer <workflow-output.json>  # -> results/offers/<slug>/*.md
uv run ajoa-kit ats-check results/offers/<slug>/cv.md # ATS parse-safety gate
```

Build the evidence library once, upstream, via the Stage-1 Workflow
(`docs/workflows/cc-workflow-evidence-library.js`) → `results/evidence-library.json`.

### CLI subcommands

Every step is also a subcommand — `uv run ajoa-kit <cmd>` (the `make` targets wrap the
ingest/chunk/persist ones). Most take a positional path or no args; the flags:

| Subcommand | Flags / args |
|---|---|
| `ingest` | — (reads `config/seed.json`, else `config/default-seed.json`) |
| `chunk` | `--batch-size N` (default 40) |
| `persist` | `FILE` — the relevance workflow result |
| `persist-offer` | `FILE` — the tailor workflow result · `--slug <slug>` |
| `ats-check` | `FILE` — a CV markdown file |
| `style` | `--json` — emit the tailor `style` arg from `config/style.json` |
| `prefill-fields` | `--ats <name> --slug <board> --job-id <id>` (Greenhouse schema lookup) |
| `probe` | — (probe candidate slugs across ATS platforms) |
| `trend-snapshot` | — (see [§Trends data branch](#trends-data-branch)) |

Per-adapter endpoint URLs live in `src/ajoa_kit/ingest.py`; sources are ToS-tiered per
[ADR-0002](docs/decisions/0002-source-tos-tiers.md).

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `AJOA_CONFIG_DIR` | `config` | where `seed.json` / `keywords.json` / `style.json` are read |
| `AJOA_RESULTS_DIR` | `results` | where ingest/chunk/persist artifacts are written |
| `POLYFETCH_DIR` | `../polyfetch-scrape` | the `polyfetch-scrape` checkout `make ingest` / `probe` borrow |
| `PORT` | `8000` | port for `make preview` |

## Opening a PR

1. Branch off `main` — one topic branch per slice (`feat/…`, `docs/…`, `ci/…`).
2. Commit by topic; keep `make check` and `make docs-lint` green before pushing.
3. Add a changelog fragment (below).
4. Open the PR against `main`; wait for CI (`gh pr checks <n> --watch`).
5. Squash-merge once green.

## Changelog (required per PR)

Every PR adds one [scriv](https://scriv.readthedocs.io/) fragment under `changelog.d/`:

```bash
make changelog_new   # create + stage a fragment
```

Edit it under a `### Added` / `### Changed` / `### Fixed` heading. Fragments collect into
`CHANGELOG.md` at release (see below).

## Releasing

SemVer; the version lives in `pyproject.toml` `[project].version` (mirrored in the README badge and
`src/ajoa_kit/__init__.py`). `CHANGELOG.md` is assembled by scriv from the per-PR fragments above.

**Cutting a release** (maintainer):

1. Run **bump-my-version** (`patch` / `minor` / `major`) from the Actions tab —
   `gh workflow run bump-my-version.yaml -f bump_type=patch`. It bumps `pyproject.toml` + the README
   badge + `src/ajoa_kit/__init__.py`, syncs `uv.lock`, collects the `changelog.d/` fragments into
   `CHANGELOG.md`, and opens a `chore(release): bump …` PR.
2. **Run the PR's checks.** It is bot-authored (`GITHUB_TOKEN`), so its Actions checks idle at
   `action_required` until a real-user event — push an empty commit to the bump branch
   (`git commit --allow-empty -m "ci: run checks" && git push origin HEAD:<bump-branch>`) or close +
   reopen the PR.
3. Merge on green — `gh pr merge <n> --squash --admin --delete-branch`. **tag-release** then fires on
   `main` and tags the merge commit `vX.Y.Z` (always reachable from `main` — no tag drift).
4. Optionally publish a GitHub Release with notes from the `CHANGELOG.md` block —
   `gh workflow run publish-release.yaml -f tag=vX.Y.Z`. The default flow is tag-only.

**Releasing the current version without bumping** (e.g. the first `v0.1.0`, already declared in
`pyproject.toml`) — `tag-release` only fires on a version *change*, so collect and tag manually:

```bash
make changelog_release VERSION=0.1.0       # scriv collect -> CHANGELOG.md (deletes fragments)
# commit + merge the changelog PR, then on main:
git -c tag.gpgSign=false tag -a v0.1.0 -m "Release v0.1.0" && git push origin v0.1.0
gh workflow run publish-release.yaml -f tag=v0.1.0
```

## Trends data branch

The dashboard's real **market-trends** data lives only on the orphan **`data`** branch (never in
`ui/` or `main`); the live site fetches it at runtime from
`raw.githubusercontent.com/<owner>/<repo>/data/results/trends.ndjson` (auto-derived from the Pages
origin, so a fork self-hosts its own). To refresh it:

```bash
uv run ajoa-kit trend-snapshot   # -> results/trends.ndjson (needs the polyfetch venv; not run in CI)
make trends-data                 # force-push results/trends.ndjson -> the `data` branch
```

The live dashboard picks it up on the next page load — no redeploy. CI can't generate this data
itself: `trend-snapshot` needs the `polyfetch-scrape` stack, which isn't available in Actions.
