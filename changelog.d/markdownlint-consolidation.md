### Changed

- Consolidate markdownlint configuration into a single `.markdownlint-cli2.jsonc`
  (rules moved under its `config` key); remove the separate `.markdownlint.jsonc`.
  CI and `make docs-lint` behavior is unchanged (#45).
