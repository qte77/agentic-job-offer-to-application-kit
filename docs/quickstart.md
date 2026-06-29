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
make preview      # serve the dashboard at http://localhost:8000 (override: PORT=9000 make preview)
```

`make help` lists every target; [CONTRIBUTING.md §Commands](../CONTRIBUTING.md#commands) documents
them in full.

## Run your own search

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (provisions Python ≥ 3.11), **Claude Code** (its
Workflow tool runs the relevance/tailor phases), and a `polyfetch-scrape` checkout beside this repo at
`../polyfetch-scrape` (the network-fetch layer `make ingest` / `probe` borrow). The Makefile is the
command source of truth (`make help`); the CLI flags and the `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` /
`POLYFETCH_DIR` overrides are tabulated in [CONTRIBUTING.md](../CONTRIBUTING.md#commands) for
contributors. What you author first is the **source list**:

The kit ships a tracked default (`config/default-seed.json`) and runs out of the box. To use your
own, create `config/seed.json` (git-ignored); it overrides the default, e.g.:

```json
{"feeds": [], "ats": [{"ats": "greenhouse", "slug": "acme", "company": "Acme", "lane": "engineering"}],
 "aggregators": [{"name": "arbeitnow"}, {"name": "themuse"}]}
```

Broad no-auth aggregators are ToS-tiered in [ADR-0002](decisions/0002-source-tos-tiers.md).

Then run the pipeline — Stage 1 builds your evidence library **once**; Stages 2–3 run per search. The
`Workflow({…})` blocks run inside a Claude Code session, and **you save each Workflow's returned JSON
to the file the next `make` / `ajoa-kit` step reads** (that hand-off is manual):

```text
# Stage 1 (once) — save the returned object to results/evidence-library.json:
Workflow({ scriptPath: "docs/workflows/cc-workflow-evidence-library.js",
           args: { workspaceRoot: "/path/to/portfolio", account: "you" } })

# Stage 2 (per search) — ingest -> chunk -> relevance -> persist:
POLYFETCH_DIR=../polyfetch-scrape make ingest        # -> results/jobs-raw.json
make chunk                                           # -> results/batches/ (+ manifest.json)
# relevance: batchCount = results/batches/manifest.json .batch_count; save the result, then persist:
Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
           args: { rootDir: ".", batchCount: <N> } })
make persist FILE=<relevance-output.json>            # -> results/<lane>/shortlist.*

# Stage 3 (per offer) — pick an offer id from a shortlist, then tailor -> persist-offer -> ats-check:
Workflow({ scriptPath: "docs/workflows/cc-workflow-tailor-offer.js",
           args: { rootDir: ".", lane: "engineering", offerId: "<id>" } })
uv run ajoa-kit persist-offer <tailor-output.json>   # -> results/offers/<slug>/*.md
uv run ajoa-kit ats-check results/offers/<slug>/cv.md
```

## Incremental / daily ingest (optional)

`ajoa-kit ingest --merge` additionally folds each pull into a running `results/corpus.json` — a
4-state dedup-merge (new / changed / unchanged / delisted) that stamps `first_seen` / `last_seen` per
JD, so the keyword trends bucket by when a role *first appeared* rather than the run date. The
scheduled `.github/workflows/ingest-daily.yaml` (06:00 UTC + manual `workflow_dispatch`) runs this
daily, keeping the corpus as a private cross-run artifact (no PII on any branch) and pushing only the
aggregate keyword trends to the `data` branch. `--merge` leaves `results/jobs-raw.json` unchanged.

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
