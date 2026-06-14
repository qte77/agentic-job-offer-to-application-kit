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
`CHANGELOG.md` at release (`make changelog_release VERSION=X.Y.Z`).
