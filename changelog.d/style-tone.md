### Added

- Writing style / tone for the Stage-3 tailor pass (#16): a git-ignored `config/style.json` lets the
  candidate set a `tone` and/or point to their own CV / cover-letter samples; per artifact a sample
  wins over the tone, which wins over a neutral default. `src/ajoa_kit/style.py` resolves it (with a
  sample-size cap and fail-loud on a missing referenced file), `ajoa-kit style [--json]` previews the
  directives, and `cc-workflow-tailor-offer.js` applies them via an optional `style` arg. The evidence
  library still supplies the facts — style shapes voice, not content.

### Changed

- `ajoa-kit` CLI dispatch refactored to argparse `set_defaults(func=...)` handlers (flat complexity as
  subcommands grow); behavior unchanged.
