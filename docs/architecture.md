# Architecture — agentic-job-offer-to-application-kit

A generic pipeline (config → Python engine → results) with LLM/agent phases. Claude Code is the
on-demand orchestrator (Workflow-tool scripts), but the phases are described agent-agnostically so
other coding agents can drive them.

The repo follows a four-layer separation — backend / CLI / orchestration / UI, one-way imports
only — per [ADR-0001](decisions/0001-backend-cli-ui-separation.md).

## Pipeline

```text
config/seed.json
  → src/ajoa_kit/ingest.py   (ATS/feed adapters → word-boundary pre-filter → dedupe)
  → results/jobs-raw.json
  → src/ajoa_kit/chunk.py    → results/batches/ + manifest.json
  → docs/workflows/cc-workflow-relevance.js   (parallel LLM lane-screen)
  → results/<lane>/shortlist.{json,md}
  → [Stage 3, designed] cc-workflow-tailor-offer.js → results/offers/<slug>/
```

Run-once upstream: `cc-workflow-evidence-library.js` → `results/evidence-library.json`.

**Two-stage trim (cost model):** cheap deterministic pre-filter → LLM relevance screen →
expensive tailoring only on the shortlist.

## Three mechanics that define it

1. **Orchestration = Claude Code Workflow tool, not make/node.** Workflows run via
   `Workflow({ scriptPath: 'docs/workflows/cc-workflow-*.js', args })`, resumable and cached by run
   id; subagents are inline `agent()` calls — no `.claude/agents/*.md`, no team mode. The `.js`
   scripts are the reference implementation; the phases are documented agent-agnostically.
2. **The evidence library is structured data.** `cc-workflow-evidence-library.js` returns the `LIB`
   object (skill clusters, master CV bullets, per-lane angles, gaps) written to
   `results/evidence-library.json` — the retrieval source of truth the relevance and tailor steps read.
3. **A web-access layer wraps polyfetch.** `src/ajoa_kit/ingest.py` fetches via `polyfetch-scrape`
   (httpx → curl_cffi → headless), invoked with `uv run --directory $POLYFETCH_DIR` — never vendored.
   Feed/API-first, no-auth, GET only; each record carries `fetched_backend` for tier monitoring.

## Position lanes

Five configurable lanes scored by the relevance screen: CxO/fractional, founding engineer, senior IC
engineering, cloud/DevOps/platform, architect. Lanes live in the evidence library.

## Repo structure

```text
agentic-job-offer-to-application-kit/
├── README.md / AGENTS.md / CHANGELOG.md / CODEOWNERS / LICENSE
├── docs/
│   ├── architecture.md / roadmap.md / userstory.md / research.md
│   └── workflows/
│       ├── cc-workflow-evidence-library.js   # Stage 1 (built)
│       ├── cc-workflow-relevance.js          # Stage 2 screen (built)
│       └── cc-workflow-tailor-offer.js       # Stage 3 (designed)
├── src/ajoa_kit/               # engine: ingest, chunk, persist_scored, slug_probe, settings, __main__ (CLI)
├── scripts/ingest.sh           # thin env shim -> ajoa-kit ingest (borrows polyfetch's uv env via POLYFETCH_DIR)
├── config/                     # your inputs — git-ignored, dir kept via .gitkeep
│                               #   seed.json + future portfolio/work-history/lanes/locale/writing-samples
├── tests/                      # value-add suite (pre-filter, canonical_url, dedup, adapters)
├── examples/alexis-doe/        # self-contained example mirroring config/ + results/ (committed)
├── results/                    # generated outputs — git-ignored, dir kept via .gitkeep
│                               #   evidence-library.json, jobs-raw.json, batches/, <lane>/shortlist.*, offers/<slug>/
├── pyproject.toml / uv.lock    # uv project; ruff + pytest config
└── .github/                    # codeql + dependabot + ci (SHA-pinned)
```

## Data layout — two folders

- `config/` — inputs you author; git-ignored (dir kept via `.gitkeep`). Copy a starting `seed.json`
  from `examples/alexis-doe/config/`.
- `results/` — everything generated; git-ignored (dir kept via `.gitkeep`), so no PII is ever committed.
- `examples/alexis-doe/` — a committed, self-contained example mirroring `config/` + `results/`.

## Boundary failure policy

| Boundary | Policy |
|---|---|
| ATS/feed fetch (per source) | wrap-continue (one source down ≠ run fails) |
| JD parse (per record) | wrap-continue (skip malformed) — hardening tracked in issues |
| config load (seed) | fail-loud (missing/invalid config stops the run) |
| evidence-library load (relevance) | fail-loud (clear "run Stage 1 first") |

## Built vs designed

- **Built:** `src/ajoa_kit/` engine; `AppSettings` config + `ajoa-kit` CLI (ADR-0001 L1/L2);
  `cc-workflow-evidence-library.js`; `cc-workflow-relevance.js`; baseline gates (ruff, pytest,
  CodeQL/Dependabot/CI).
- **Designed:** `cc-workflow-tailor-offer.js`, ats-check, templates, locale config, trends dashboard,
  style/tone tailoring from user CV + cover-letter samples (#16).
- **Dropped (YAGNI):** team mode, dual modes, validation ceremony, slide decks.
