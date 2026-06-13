### Added

- `AppSettings` (pydantic-settings) runtime config and an `ajoa-kit` CLI — an `argparse`
  dispatcher with `ingest` / `chunk` / `persist` / `probe` subcommands. `config/` and
  `results/` are env-overridable via `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` and resolve from
  the working directory, so the package works as an installed wheel. Formalized in ADR-0001
  (backend / CLI / orchestration / UI four-layer separation with a one-way import rule).

### Changed

- Dropped the hardcoded `ROOT = Path(__file__).resolve().parents[2]` from the pipeline
  modules; path resolution now flows through `AppSettings`. `scripts/ingest.sh` reduced to a
  thin env shim that anchors `AJOA_*_DIR` and delegates to `ajoa-kit ingest`; `Makefile`
  targets map to the CLI subcommands.
