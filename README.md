# agentic-job-offer-to-application-kit

> Turn a candidate portfolio into tailored, ATS-safe job applications — feed/API-first, no
> scraping, no automated submission.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![CI](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/ci.yaml/badge.svg)](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/ci.yaml)
[![CodeQL](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/codeql.yaml/badge.svg)](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/codeql.yaml)

<!-- A screenshot/diagram belongs here once there is a visual surface (e.g. the trends dashboard). -->

## Why

Job search is noisy: hundreds of postings, each needing a tailored CV and cover letter with an
honest framing of gaps. This kit aligns one portfolio to many offers — screen for fit, then
tailor — using only public, no-auth data and keeping a human in the loop for submission.

## What

A **generic** pipeline (a small Python engine + LLM/agent phases). **Claude Code** is the
on-demand orchestrator via Workflow-tool scripts, but the phases are documented
agent-agnostically so any coding agent can drive them.

1. **Evidence library** (build once) — mine a portfolio into a verified, lane-tagged brag document.
2. **Ingest → relevance** (per search) — pull job descriptions (JDs) from public applicant
   tracking systems (ATS) + feeds, **pre-filter** cheaply, then LLM-screen against your lanes → a scored shortlist.
3. **Tailor** (per offer) — match → CV + cover letter + gap report, with an `ats-check` parse-safety
   pass, writing-style/tone matching, and a human-review prefill pack (see docs/research.md §Delivery).

Five configurable **position lanes**: CxO/fractional · founding engineer · senior IC engineering ·
cloud/DevOps/platform · architect (configurable defaults — see the `LANES` array in
`cc-workflow-evidence-library.js`). Cost model: cheap pre-filter → LLM relevance → tailor only the shortlist.

## How

Dev loop: `make help` · `make check` (lint + types + complexity + tests) · `make docs-lint`.

### Run your own search

```bash
make install                                          # sync the dev env (uv)
# create config/seed.json with your sources, e.g.:
#   {"feeds": [], "ats": [{"ats": "greenhouse", "slug": "acme", "company": "Acme", "lane": "engineering"}]}
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

Each step is also a CLI subcommand — `uv run ajoa-kit {ingest,chunk,persist,persist-offer,ats-check,style,prefill-fields,probe}`
(the `make` targets wrap the ingest/chunk/persist ones); `config/` and `results/` locations are
env-overridable via `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR`.

Build the evidence library once, upstream, via the Stage-1 Workflow
(`docs/workflows/cc-workflow-evidence-library.js`) → `results/evidence-library.json`.

### Try the example (no fetch)

The synthetic [`examples/alexis-doe/`](examples/alexis-doe/) workspace ships a pre-built evidence
library + batches, so run the relevance screen straight against it — no `make ingest`/`make chunk`:

```text
Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
           args: { rootDir: "examples/alexis-doe", batchCount: 1 } })
```

**Constraints:** no automated submission, no scraping — public no-auth GET only, with a
human-reviewed prefill pack (see [docs/research.md §Delivery](docs/research.md#delivery)); no PII in
the repo (see [docs/architecture.md §Data layout](docs/architecture.md#data-layout)).

## Docs

- [docs/architecture.md](docs/architecture.md) — pipeline, components, execution model
- [docs/roadmap.md](docs/roadmap.md) — what's built, what's next, what's deferred
- [docs/userstory.md](docs/userstory.md) — user stories with acceptance criteria
- [docs/research.md](docs/research.md) — fetching, ATS, and positioning research
- [examples/alexis-doe/](examples/alexis-doe/) — synthetic end-to-end example
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to set up, test, and open a PR
- [AGENTS.md](AGENTS.md) — operating rules for AI coding agents
- [SECURITY.md](SECURITY.md) — vulnerability disclosure policy

## License

Apache-2.0 © 2026 qte77. See [LICENSE](LICENSE).
