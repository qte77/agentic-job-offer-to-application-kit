# agentic-job-offer-to-application-kit

> Turn a candidate portfolio into tailored, ATS-safe job applications — feed/API-first, no
> scraping, no automated submission.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-informational)](CHANGELOG.md)
[![CodeQL](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/codeql.yaml/badge.svg)](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/codeql.yaml)
[![CodeFactor](https://www.codefactor.io/repository/github/qte77/agentic-job-offer-to-application-kit/badge)](https://www.codefactor.io/repository/github/qte77/agentic-job-offer-to-application-kit)
[![CI](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/ci.yaml/badge.svg)](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/ci.yaml)
[![Lint MD and Links](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/lint-md-links.yml/badge.svg)](https://github.com/qte77/agentic-job-offer-to-application-kit/actions/workflows/lint-md-links.yml)

## What

A **generic** pipeline (a small Python engine + LLM/agent phases). **Claude Code** is the
on-demand orchestrator via Workflow-tool scripts, but the phases are documented
agent-agnostically so any coding agent can drive them.

1. **Evidence library** (build once) — mine a portfolio into a verified, lane-tagged brag document.
2. **Ingest → relevance** (per search) — pull job descriptions (JDs) from public applicant
   tracking systems (ATS) + feeds, **pre-filter** cheaply, then LLM-screen against your lanes → a scored shortlist.
3. **Tailor** (per offer) — match → CV + cover letter + gap report, with an `ats-check` parse-safety
   pass, writing-style/tone matching, and a human-review prefill pack (see docs/research.md §Delivery).

Five configurable **position lanes** (CxO/fractional · founding engineer · senior IC engineering ·
cloud/DevOps/platform · architect) — see
[docs/architecture.md §Position lanes](docs/architecture.md#position-lanes). Cost model: cheap
pre-filter → LLM relevance → tailor only the shortlist.

<details>
<summary>Screenshot — shortlist (first offer expanded to its tailored CV + cover letter)</summary>

<br />

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/images/dashboard-shortlist-dark.png" />
  <img alt="ajoa-kit dashboard — shortlist with the first offer expanded to its tailored CV and cover letter" src="assets/images/dashboard-shortlist-light.png" />
</picture>

</details>

<details>
<summary>Screenshot — market keyword trends (default 3-month window)</summary>

<br />

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/images/dashboard-market-dark.png" />
  <img alt="ajoa-kit dashboard — job-market keyword trends over the default 3-month window" src="assets/images/dashboard-market-light.png" />
</picture>

</details>

## How

Try the **[live demo](https://qte77.github.io/agentic-job-offer-to-application-kit/)** (synthetic
shortlist · live market trends, bundled same-origin from the `data` branch at deploy), or run it
locally: **[docs/quickstart.md](docs/quickstart.md)** is the narrated walkthrough (author your
sources, screen the bundled synthetic example with no fetch, then tailor — ingest → chunk → relevance
→ tailor → ats-check — plus the keyword-trends and writing-style options), and
**[CONTRIBUTING.md §Commands](CONTRIBUTING.md#commands)** is the command reference (run, dev, and
release; the Makefile is the source of truth).

**Constraints:** no automated submission, no scraping — public no-auth GET only, with a
human-reviewed prefill pack (see [docs/research.md §Delivery](docs/research.md#delivery)); no PII in
the repo (see [docs/architecture.md §Data layout](docs/architecture.md#data-layout)).

## Why

Job search is noisy: hundreds of postings, each needing a tailored CV and cover letter with an
honest framing of gaps. This kit aligns one portfolio to many offers — screen for fit, then
tailor — using only public, no-auth data and keeping a human in the loop for submission.

## Refs

- [docs/architecture.md](docs/architecture.md) — pipeline, components, execution model
- [docs/quickstart.md](docs/quickstart.md) — full run workflow + optional features
- [docs/roadmap.md](docs/roadmap.md) — what's built, what's next, what's deferred
- [docs/userstory.md](docs/userstory.md) — user stories with acceptance criteria
- [docs/research.md](docs/research.md) — fetching, ATS, and positioning research
- Decisions (ADRs): [ADR-0001 layering](docs/decisions/0001-backend-cli-ui-separation.md) · [ADR-0002 source ToS tiers](docs/decisions/0002-source-tos-tiers.md)
- [examples/alexis-doe/](examples/alexis-doe/) — synthetic end-to-end example
- [CONTRIBUTING.md](CONTRIBUTING.md) — command reference (run/dev/release), setup, testing, and PRs
- [AGENTS.md](AGENTS.md) — operating rules for AI coding agents
- [SECURITY.md](SECURITY.md) — vulnerability disclosure policy

## License

Apache-2.0 © 2026 qte77. See [LICENSE](LICENSE) and [NOTICE](NOTICE) (third-party components — vendored Chart.js + marked, MIT).
