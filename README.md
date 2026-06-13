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
3. **Tailor** (per offer) — CV + cover letter + gap report + human-review prefill pack. *Designed; see docs.*

Five configurable **position lanes**: CxO/fractional · founding engineer · senior IC engineering ·
cloud/DevOps/platform · architect. Cost model: cheap pre-filter → LLM relevance → tailor only the shortlist.

## How

```bash
cp examples/alexis-doe/config/seed.json config/seed.json   # your target companies / feeds
POLYFETCH_DIR=../polyfetch-scrape scripts/ingest.sh     # -> results/jobs-raw.json
uv run python -m ajoa_kit.chunk                         # -> results/batches/ + manifest.json
# relevance (Claude Code Workflow tool); batchCount = results/batches/manifest.json .batch_count:
#   Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
#              args: { rootDir: ".", batchCount: <N> } })
uv run python -m ajoa_kit.persist_scored <output.json> # -> results/<lane>/shortlist.*
```

Runnable synthetic example: [`examples/alexis-doe/`](examples/alexis-doe/).
Develop with `uv run ruff check .` and `uv run pytest -m "not network"`.

**Constraints:** no automated submission (human-reviewed prefill pack, inside platform Terms of
Use/Service); no scraping (public no-auth GET only); no PII in the repo (real config and
`results/` are git-ignored).

## Docs

- [docs/architecture.md](docs/architecture.md) — pipeline, components, execution model
- [docs/roadmap.md](docs/roadmap.md) — what's built, what's next, what's deferred
- [docs/userstory.md](docs/userstory.md) — user stories with acceptance criteria
- [docs/research.md](docs/research.md) — fetching, ATS, and positioning research
- [examples/alexis-doe/](examples/alexis-doe/) — synthetic end-to-end example

## License

Apache-2.0 © 2026 qte77. See [LICENSE](LICENSE).
