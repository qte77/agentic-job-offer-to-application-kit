# Quickstart

The full run workflow and optional features. For the one-line overview see the
[README](../README.md#how); for the pipeline internals see [architecture.md](architecture.md); for
the exact commands (dev, run, and release) see [CONTRIBUTING.md §Commands](../CONTRIBUTING.md#commands).

## Install

Prerequisite: [uv](https://docs.astral.sh/uv/) (it provisions Python ≥ 3.11). Then:

```bash
git clone https://github.com/qte77/agentic-job-offer-to-application-kit
cd agentic-job-offer-to-application-kit
make install-uv   # install uv (skip if already installed)
make install      # sync the dev environment (uv)
make preview      # serve the dashboard at http://localhost:8000
```

`make help` lists every target; [CONTRIBUTING.md §Commands](../CONTRIBUTING.md#commands) documents
them in full.

## Run your own search

Run the pipeline (ingest → chunk → relevance → persist → tailor → persist-offer →
ats-check) with the commands in [CONTRIBUTING.md §Commands](../CONTRIBUTING.md#commands) — the
Makefile is the source of truth, and the CLI flags plus the `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` /
`POLYFETCH_DIR` overrides are tabulated there. What you author first is the **source list**:

The kit ships a tracked default (`config/default-seed.json`) and runs out of the box. To use your
own, create `config/seed.json` (git-ignored); it overrides the default, e.g.:

```json
{"feeds": [], "ats": [{"ats": "greenhouse", "slug": "acme", "company": "Acme", "lane": "engineering"}],
 "aggregators": [{"name": "arbeitnow"}, {"name": "themuse"}]}
```

Broad no-auth aggregators are ToS-tiered in [ADR-0002](decisions/0002-source-tos-tiers.md). Build the
evidence library once, upstream, via the Stage-1 Workflow
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
pre-filter vocabulary. `trend-snapshot` then writes an aggregate, keyword-only per-ISO-week record to
`results/trends.ndjson` (no JD/PII), and pushing it to the `data` branch re-triggers the Pages deploy
to bundle it **same-origin** into the published site (so the live charts load reliably — no
cross-origin runtime fetch) — commands in
[CONTRIBUTING.md §Trends data branch](../CONTRIBUTING.md#trends-data-branch). Local dev and forks
fall back to fetching the `data` branch directly, overridable with `?base=<raw-url>`; the real trends
are never committed to the source `ui/` (see [ui/README.md](../ui/README.md)).

## Writing style (optional)

Drop a git-ignored `config/style.json` with a `tone` string and/or paths to your own CV /
cover-letter samples; `ajoa-kit style --json` emits the resolved directives to pass as the tailor
workflow's `style` arg (a sample wins over the tone, which wins over a neutral default). Style shapes
voice, not content — the evidence library still supplies the facts.
