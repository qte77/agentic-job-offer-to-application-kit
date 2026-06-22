# Quickstart

The full run workflow and optional features. For the one-line overview see the
[README](../README.md#how); for the pipeline internals see [architecture.md](architecture.md).

Dev loop: `make help` · `make check` (lint + types + complexity + tests) · `make docs-lint`.

## Run your own search

```bash
make install                                          # sync the dev env (uv)
# the kit ships a tracked default source list (config/default-seed.json) — runs out of the box.
# to use your own, create config/seed.json (git-ignored); it overrides the default, e.g.:
#   {"feeds": [], "ats": [{"ats": "greenhouse", "slug": "acme", "company": "Acme", "lane": "engineering"}],
#    "aggregators": [{"name": "arbeitnow"}, {"name": "themuse"}]}   # broad no-auth aggregators (ToS-tiered in ADR-0002)
POLYFETCH_DIR=../polyfetch-scrape make ingest         # -> results/jobs-raw.json
make chunk                                            # -> results/batches/ + manifest.json
# relevance — Claude Code Workflow tool; batchCount = results/batches/manifest.json .batch_count:
#   Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
#              args: { rootDir: ".", batchCount: <N> } })
make persist FILE=<workflow-output.json>              # -> results/<lane>/shortlist.*
# tailor one shortlisted offer — Claude Code Workflow tool:
#   Workflow({ scriptPath: "docs/workflows/cc-workflow-tailor-offer.js",
#              args: { rootDir: ".", lane: "engineering", offerId: "<id>" } })
uv run ajoa-kit persist-offer <workflow-output.json>  # -> results/offers/<slug>/*.md
uv run ajoa-kit ats-check results/offers/<slug>/cv.md # ATS parse-safety gate
```

Each step is also a CLI subcommand — `uv run ajoa-kit {ingest,chunk,persist,persist-offer,ats-check,style,prefill-fields,probe,trend-snapshot}`
(the `make` targets wrap the ingest/chunk/persist ones); `config/` and `results/` locations are
env-overridable via `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR`. Most take a positional path or no args;
the optional flags are `chunk --batch-size N` (default 40), `persist-offer --slug <slug>`,
`prefill-fields --ats <name> --slug <board> --job-id <id>` (Greenhouse schema lookup), and
`style --json`.

Build the evidence library once, upstream, via the Stage-1 Workflow
(`docs/workflows/cc-workflow-evidence-library.js`) → `results/evidence-library.json`.

## Try the example (no fetch)

The synthetic [`examples/alexis-doe/`](../examples/alexis-doe/) workspace ships a pre-built evidence
library + batches, so run the relevance screen straight against it — no `make ingest`/`make chunk`:

```text
Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
           args: { rootDir: "examples/alexis-doe", batchCount: 1 } })
```

## Keyword trends (optional)

Drop a `config/keywords.json` (`{"interest": [...], "title_roles": [...]}`) to override the default
pre-filter vocabulary, then `ajoa-kit trend-snapshot` writes an aggregate, keyword-only per-ISO-week
record to `results/trends.ndjson` (no JD/PII). `make trends-data` pushes that snapshot to the `data`
branch, which re-triggers the Pages deploy to bundle it **same-origin** into the published site (so
the live charts load reliably — no cross-origin runtime fetch). Local dev and forks fall back to
fetching the `data` branch directly, overridable with `?base=<raw-url>`; the real trends are never
committed to the source `ui/` (see [ui/README.md](../ui/README.md)).

## Writing style (optional)

Drop a git-ignored `config/style.json` with a `tone` string and/or paths to your own CV /
cover-letter samples; `ajoa-kit style --json` emits the resolved directives to pass as the tailor
workflow's `style` arg (a sample wins over the tone, which wins over a neutral default). Style shapes
voice, not content — the evidence library still supplies the facts.
