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
make docs_lint   # markdownlint + lychee link check
make ui_check    # fast headless dashboard smoke (CSP/render/console)
make ui_e2e      # full dashboard e2e — local + remote, viewports/device/themes/interactions
make ui_shots    # regenerate the README screencast GIFs (light + dark)
```

`make docs_lint` needs two tools `uv sync` does **not** install —
[`markdownlint-cli2`](https://github.com/DavidAnson/markdownlint-cli2) (npm) and
[`lychee`](https://github.com/lycheeverse/lychee) (cargo) — run `make install_docs_tools` once
(needs `npm` + `cargo` on `PATH`). The `ui_*` targets borrow the sibling `polyfetch-scrape`
patchright venv (set `POLYFETCH_DIR`); the headless-testing dos & don'ts are in
[docs/testing-headless-ui.md](docs/testing-headless-ui.md).

### Pipeline

The full per-search run. The orchestration steps run via the Claude Code Workflow tool — see each
script's header in [`.claude/workflows/`](.claude/workflows/) for the exact `args`:

```bash
POLYFETCH_DIR=../polyfetch-scrape make ingest         # -> results/jobs-raw.json
#   uv run ajoa-kit ingest --merge  also folds the pull into results/corpus.json (the daily-cron corpus)
make chunk                                            # -> results/batches/ + manifest.json
# relevance (Workflow tool) — batchCount = results/batches/manifest.json .batch_count:
#   Workflow({ scriptPath: ".claude/workflows/cc-workflow-relevance.js", args: { rootDir: ".", batchCount: <N> } })
make persist FILE=<workflow-output.json>              # -> results/<lane>/shortlist.*
# tailor one shortlisted offer (Workflow tool); add `critique: true` for the draft→critique→revise pass (#272):
#   Workflow({ scriptPath: ".claude/workflows/cc-workflow-tailor-offer.js", args: { rootDir: ".", lane: "engineering", offerId: "<id>" } })
uv run ajoa-kit persist-offer <workflow-output.json>  # -> results/offers/<slug>/*.md
uv run ajoa-kit ats-check results/offers/<slug>/cv.md # ATS parse-safety gate
uv run ajoa-kit render-pdf results/offers/<slug>/cv.md # optional -> cv.pdf (needs: uv sync --extra pdf)
```

Build the evidence library once, upstream, via the Stage-1 Workflow
(`.claude/workflows/cc-workflow-evidence-library.js`) → `results/evidence-library.json`.

### CLI subcommands

Every step is also a subcommand — `uv run ajoa-kit <cmd>` (the `make` targets wrap the
ingest/chunk/persist ones). Most take a positional path or no args; the flags:

| Subcommand | Flags / args |
|---|---|
| `ingest` | `--merge` — also fold the pull into a running `results/corpus.json` (4-state dedup-merge) · reads `config/seed.json`, else `config/default-seed.json` |
| `chunk` | `--batch-size N` (default 40) · `--new` — batch only the latest-pull `corpus.json` delta (offers new or changed this pull) for an incremental re-screen (#226/#235) |
| `persist` | `FILE` — the relevance workflow result · `--merge` — union into the existing shortlists / `jobs-scored.json` by id instead of overwriting (#226) |
| `persist-offer` | `FILE` — the tailor workflow result · `--slug <slug>` |
| `refresh` | reconcile shortlists vs the corpus `delisted` state + a read-only URL re-probe · `--lane <name>` (default: all buckets) · `--delete` (remove vs flag `stale`) · `--dry-run` |
| `verify-sources` | re-probe every `config/default-seed.json` `feeds`/`ats` source (read-only, no auth), stamp `_date_verified` on the live ones, report the rest for manual triage · `--dry-run` (#217) |
| `ats-check` | `FILE` — a CV markdown file |
| `render-pdf` | `FILE` — a tailored markdown file · `--out <path>` (default `<file>.pdf`) — optional Markdown→PDF export; needs the `[pdf]` extra (`uv sync --extra pdf`) |
| `lanes` | `--json` — emit the workflow `lanes` arg from `config/lanes.json` (the canonical 7 lanes) |
| `style` | `--json` — emit the tailor `style` arg from `config/style.json` |
| `prefill-fields` | `--ats <name> --slug <board> --job-id <id>` (Greenhouse schema lookup) |
| `probe` | — (probe candidate slugs across ATS platforms) |
| `trend-snapshot` | — (see [§Trends data branch](#trends-data-branch)) |
| `companies-snapshot` | — company-hiring series: publishable geo-by-field + local per-company (see [§Trends data branch](#trends-data-branch)) |
| `discover` | — reads the config `discovery` source (yc-oss) → emerging/hiring company signal in `results/emerging-companies.json` (local business data, never published; needs polyfetch env) (#292) |
| `status` | `<slug>` — set/read a local application-outcome status per offer · `--stage <applied/responded/interview/offer/rejected>` `--date <YYYY-MM-DD>` `--notes <text>` (#273) |

Per-adapter endpoint URLs live in `src/ajoa_kit/sources.py`; sources are ToS-tiered per
[ADR-0002](docs/decisions/0002-source-tos-tiers.md).

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `AJOA_CONFIG_DIR` | `config` | where `seed.json` / `keywords.json` / `style.json` are read (the tracked `keywords.json` is canonical + published as trend keys — keep it generic; use a private dir for personal vocab) |
| `AJOA_RESULTS_DIR` | `results` | where ingest/chunk/persist artifacts (PII) are written |
| `AJOA_PUBLIC_DATA_DIR` | `public-data` | where PII-free publishable trends are written (the only data published, #210) |
| `POLYFETCH_DIR` | `../polyfetch-scrape` | the `polyfetch-scrape` checkout `make ingest` / `probe` borrow |
| `PORT` | `8000` | port for `make preview` |
| `TRENDS_FORCE` | *(unset)* | `1` skips `make trends_data`'s shrink guard (which refuses a push that would drop bucket counts) for an intentional prune |
| `.env` file | *(none)* | optional dotenv (`AppSettings.env_file`, `src/ajoa_kit/settings.py`) that sets any `AJOA_*` override above; git-ignored — keep private paths out of the repo |

## Opening a PR

1. Branch off `main` — one topic branch per slice (`feat/…`, `docs/…`, `ci/…`).
2. Commit by topic; keep `make check` and `make docs_lint` green before pushing.
3. Add a changelog fragment (below).
4. Open the PR against `main`; wait for CI (`gh pr checks <n> --watch`).
5. Squash-merge once green.

## Changelog (per behaviour-changing PR)

Every **behaviour-changing** PR adds one [scriv](https://scriv.readthedocs.io/) fragment under
`changelog.d/` (pure docs / roadmap / CI-config tweaks are exempt):

```bash
make changelog_new   # create + stage a fragment
```

Edit it under a `### Added` / `### Changed` / `### Fixed` heading. Fragments collect into
`CHANGELOG.md` at release (see below).

## Releasing

SemVer; the version lives in `pyproject.toml` `[project].version` (mirrored in the README badge,
`src/ajoa_kit/__init__.py`, and the dashboard footer `ui/index.html` `#app-version`). `CHANGELOG.md`
is assembled by scriv from the per-PR fragments above.

**Cutting a release** (maintainer):

1. Run **bump-my-version** (`patch` / `minor` / `major`) from the Actions tab —
   `gh workflow run bump-my-version.yaml -f bump_type=patch`. It bumps `pyproject.toml` + the README
   badge + `src/ajoa_kit/__init__.py` + the dashboard footer, syncs `uv.lock`, collects the
   `changelog.d/` fragments into `CHANGELOG.md`, and opens a `chore(release): bump …` PR.
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
`ui/` or `main`). On the published site the deploy bundles it **same-origin** — `gh-pages.yaml`
copies it from the `data` branch at deploy time — so the live charts refresh whenever the site
redeploys (trigger details below). Local dev and forks fall back to fetching it at runtime from
`raw.githubusercontent.com/<owner>/<repo>/data/public-data/trends.ndjson` (auto-derived from the Pages
origin, so a fork self-hosts its own). The geo-by-field **company-hiring** series
(`hiring-{weekly,daily,monthly}.ndjson`) rides the same branch and same-origin bundling — aggregate,
**no company names** (same category as the keyword counts); the per-company breakdown stays **local**
in git-ignored `results/hiring-companies.ndjson`, never published. To refresh them:

```bash
uv run ajoa-kit trend-snapshot      # -> public-data/trends{,-daily,-monthly}.ndjson (needs the polyfetch venv; not run in CI)
uv run ajoa-kit companies-snapshot  # -> public-data/hiring-{weekly,daily,monthly}.ndjson (geo-by-field) + local results/hiring-companies.ndjson
make trends_data                    # force-push the $(TRENDS_PUBLISH) files -> the `data` branch
```

A **local** `make trends_data` push re-triggers the Pages deploy directly, which re-bundles the fresh
same-origin trends (Pages may serve the prior copy for up to ~10 min while its cache expires). The
nightly `ingest-daily.yaml` cron pushes with `GITHUB_TOKEN`, and a `GITHUB_TOKEN` push can't
self-trigger a workflow (GitHub loop prevention), so the cron **dispatches** `gh-pages.yaml`
explicitly after its push. CI can't generate this data itself: `trend-snapshot` needs the
`polyfetch-scrape` stack, which isn't available in Actions.

The dashboard auto-derives this URL from its own Pages origin (so a fork self-hosts); append
`?base=<raw-githubusercontent-prefix>` to override it for local dev, a fork, or a custom domain.
