### Changed

- docs: commands are now tracked once in a canonical CONTRIBUTING.md "Commands" section (the Makefile
  named as the source of truth) — covering the dev loop, the full pipeline, a CLI subcommand/flags
  table, and an environment-variable table (`AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` / `POLYFETCH_DIR` /
  `PORT`, previously undocumented). README and quickstart now reference it instead of repeating
  command spell-outs, and the workflow-script headers de-stale their prerequisite/persist steps
  (the old `python -m ajoa_kit.persist_scored` / `python -m ajoa_kit.chunk` forms) to point at the
  same reference. The relevance workflow's hardcoded lane keys now carry a comment noting the
  canonical lane definitions live in the evidence-library workflow.
