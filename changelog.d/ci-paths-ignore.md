### Changed

- Skip the `CI` (ruff + pytest) and `CodeQL` workflows for docs-only changes
  (`docs/**`, `changelog.d/**`, `*.md`, `examples/**/*.md`, `lychee.toml`,
  `.markdownlint-cli2.jsonc`) via `paths-ignore`. The `Lint MD and Links`
  workflow still runs on those changes (#34).
