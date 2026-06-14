### Added

- Coverage gate in `make check` via `pytest-cov` (`--cov=ajoa_kit`), with
  `fail_under` set to the current floor (41%) in `[tool.coverage.report]`. This
  guards against coverage regression; it is not a target to chase with trivial
  tests (#33).
