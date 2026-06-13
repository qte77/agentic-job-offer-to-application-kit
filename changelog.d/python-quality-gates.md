### Added

- Static-analysis gates: `pyright` (basic mode) and `complexipy` (cognitive complexity ≤ 10),
  wired into `make check` and exposed as `check_types` / `check_complexity` targets.
