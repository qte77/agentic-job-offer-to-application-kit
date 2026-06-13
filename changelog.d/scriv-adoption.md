### Added

- Changelog fragments via [scriv](https://github.com/nedbat/scriv): each PR adds one file
  under `changelog.d/` (`make changelog_new`); `make changelog_preview` shows the assembled
  entry and `make changelog_release VERSION=X.Y.Z` collects fragments into `CHANGELOG.md`.
