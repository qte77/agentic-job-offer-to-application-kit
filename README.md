# agentic-job-offer-to-application-kit

> Align a candidate's project portfolio to job offers and generate tailored,
> ATS-safe application materials — orchestrated with Claude Code dynamic workflows.

**Status: concept / design stage** (not built). Inspired by the
`agentic-market-research-to-gtm` pattern, modernized: the orchestration engine is
the **Claude Code Workflow tool** (deterministic, resumable JS workflows), not
Makefile / AGENTS-prose. It produces application *artifacts* (CV, cover letter,
gap report) — it does not submit applications.

## What it does (two stages)

1. **Evidence library** (build once) — mine a candidate's project portfolio into
   an adversarially-verified, lane-tagged "brag document": skill clusters, master
   CV bullets, per-project bullets, and a positioning paragraph per target lane
   (lanes are configurable). Structured data — the retrieval index for tailoring.
2. **Per-offer tailoring** (repeat, cheap) — ingest a job description (feed / API
   / paste), parse it into requirements, match against the library, and emit a
   tailored CV + cover letter + honest gap report — ATS-safe and locale-aware.

## Execution model

The Stage-1 workflow (`docs/workflows/evidence-library.js`) is the **Claude Code
reference implementation**, run via the Workflow tool —
`Workflow({ scriptPath: 'docs/workflows/evidence-library.js', args: { ... } })` —
resumable and cached by run id. The phased pipeline is described agent-agnostically
in the docs, so other coding agents can implement it with their own primitives.
Inputs (workspace root, account, lanes, locale) come from `args` / config, not
hardcoded. Not `make` / `node`.

## Docs

- [docs/plans/two-stage-tailoring.md](docs/plans/two-stage-tailoring.md) — approach, stages, lanes, templates, ATS, decisions
- [docs/architecture.md](docs/architecture.md) — repo structure, components, execution model
- [docs/research.md](docs/research.md) — research dimensions the design relies on
- [docs/workflows/evidence-library.js](docs/workflows/evidence-library.js) — Stage-1 dynamic workflow (functional; Claude Code reference implementation)

## Built on

- **Native Claude Code web tools** (WebSearch / WebFetch) — discovery + simple fetches
- an HTTP scraping toolkit (e.g. **polyfetch-scrape**) — **fallback for, or
  replacement of, WebFetch** when it hits 403 / JS SPAs / header walls
  (browser-impersonation + headless tiers); also the feed/API-first ingester
- a Claude Code skills source (e.g. **claude-code-plugins**) — incl. deep-research
  for per-company intel
- the **Claude Code Workflow tool** — orchestration

## Running polyfetch without installing it

The ingester ([`polyfetch-scrape`](https://github.com/qte77/polyfetch-scrape)) does not need to be installed into this repo or
added to its environment — invoke it ad-hoc from its own clone with
`uv run --directory`:

```bash
uv run --directory <path-to-polyfetch-scrape> \
  python -c "from polyfetch_scrape import fetch; r = fetch('https://example.com'); print(r.status, r.backend, len(r.body))"
```

`uv run --directory <dir>` runs in that repo's own environment, so polyfetch's
dependencies stay out of this project (for a sibling checkout, `../polyfetch-scrape`).
Useful for one-off feed / API probes during ingestion.

## Scope (KISS / DRY / YAGNI)

In: two workflows, a thin web-access wrapper, composable templates. Out
(deliberately): team mode, dual concise/detailed modes, validation-loop ceremony,
slide decks. Reuse existing tools and skills; don't rebuild.
