### Added

- **Automated release flow** (modeled on `qte77/paperverse`): `bump-my-version.yaml` (a
  `workflow_dispatch` bump that opens a `chore(release)` PR — bumping `pyproject.toml` + the README
  badge + `src/ajoa_kit/__init__.py`, syncing `uv.lock`, and collecting `changelog.d/` fragments into
  `CHANGELOG.md`), `tag-release.yaml` (annotated-tags the merge commit on a version change), and
  `publish-release.yaml` (cuts a GitHub Release from the matching `CHANGELOG.md` block). Adds the
  `[tool.bumpversion]` config + the `bump-my-version` dev dep + `__version__` in the package, and a
  CONTRIBUTING.md "Releasing" section.

### Changed

- Renamed `.github/workflows/pages.yaml` → `.github/workflows/gh-pages.yaml` (paperverse naming).
