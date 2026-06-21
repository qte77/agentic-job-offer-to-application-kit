# Contributing

This guide is for **human contributors**. To run the kit, see [README.md](README.md); for the
machine-facing rulebook — principles, constraints, quality gates, and the value-add-TDD rule — see
[AGENTS.md](AGENTS.md).

## Dev loop

```bash
make install     # sync the dev environment (uv)
make check       # ruff + format-check + pyright + complexipy + offline pytest + coverage (CI parity)
make docs-lint   # markdownlint + lychee link check
```

`make help` lists all targets.

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
