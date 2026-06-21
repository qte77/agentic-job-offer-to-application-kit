### Fixed

- `docs/workflows/cc-workflow-*.js`: the Workflow tool delivers a script's `args` as a JSON
  **string**, so the documented `Workflow({ scriptPath, args: { … } })` invocation threw
  `args.<field> required`. The relevance / tailor-offer / evidence-library scripts now `JSON.parse`
  a string `args`, so the documented one-liner runs as written (no wrapper needed).
- `examples/alexis-doe/README.md`: refreshed the stale `python -m ajoa_kit.persist_scored` line to
  `ajoa-kit persist`, added a **Stage-3** walkthrough (tailor → `persist-offer` → `ats-check`), and
  documented persisting into the example workspace via `AJOA_RESULTS_DIR` (`persist` is not
  `rootDir`-aware). The two workflow-script header comments now cite `ajoa-kit persist` / `persist-offer`.

### Changed

- `persist-offer` / `persist` now render each generated artifact's title as YAML **frontmatter**
  (`---` / `title:` / `---`) instead of a wrapping `# H1`, so each file keeps a single H1 from its
  own body — markdownlint strips frontmatter, so the packs no longer emit MD025 "multiple
  top-level headings".
