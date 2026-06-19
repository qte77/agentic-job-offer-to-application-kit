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
  → cc-workflow-tailor-offer.js   (per-offer tailor pass)
  → results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md
```

Run-once upstream: `cc-workflow-evidence-library.js` → `results/evidence-library.json`.

Side branch (any time after ingest): `ajoa-kit trend-snapshot` reads `results/jobs-raw.json` →
aggregate keyword-only `results/trends.ndjson` (per ISO week; counts of the config-driven vocabulary).

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

Five configurable lanes scored by the relevance screen. The default set (each with a focus and an
honest gap note) is the `LANES` array in `cc-workflow-evidence-library.js` — the single source of
truth — written into the evidence library.

## Repo structure

```text
agentic-job-offer-to-application-kit/
├── README.md / AGENTS.md / CHANGELOG.md / SECURITY.md / LICENSE
├── docs/
│   ├── architecture.md / roadmap.md / userstory.md / research.md
│   └── workflows/
│       ├── cc-workflow-evidence-library.js   # Stage 1 (built)
│       ├── cc-workflow-relevance.js          # Stage 2 screen (built)
│       └── cc-workflow-tailor-offer.js       # Stage 3 tailor (built)
├── src/ajoa_kit/               # engine: ingest, chunk, persist_scored, persist_offer, ats_check,
│                               #   style, prefill, slug_probe, settings, __main__ (CLI)
├── scripts/ingest.sh           # thin env shim -> ajoa-kit ingest (borrows polyfetch's uv env via POLYFETCH_DIR)
├── config/                     # your inputs — git-ignored except the tracked default-seed.json
│                               #   default-seed.json (shipped sources) · your seed.json overrides it
├── tests/                      # value-add suite (pre-filter, canonical_url, dedup, adapters)
├── examples/alexis-doe/        # self-contained example mirroring config/ + results/ (committed)
├── results/                    # generated outputs — git-ignored, dir kept via .gitkeep
│                               #   evidence-library.json, jobs-raw.json, batches/, <lane>/shortlist.*, offers/<slug>/
├── pyproject.toml / uv.lock    # uv project; ruff + pyright + complexipy + pytest + scriv config
└── .github/                    # codeql + dependabot + ci + lint-md-links + CODEOWNERS (SHA-pinned)
```

## Data layout

The authoritative list of git-ignored, never-committed paths (so no PII is ever committed) — the
single source of truth that AGENTS.md, README.md, and SECURITY.md link to:

- `config/` — inputs you author (`seed.json`, optional `style.json` / `keywords.json`); git-ignored
  **except** the tracked, PII-free `config/default-seed.json` (the shipped, ToS-vetted default
  source list of public board slugs). Your `config/seed.json` overrides it when present; absent it,
  ingest falls back to the default.
- `results/` — everything generated (`jobs-raw.json`, `trends.ndjson`, `<lane>/shortlist.*`,
  `offers/<slug>/`); git-ignored (dir kept via `.gitkeep`).
- `library/`, `input/` — additional generated/working directories; git-ignored.
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
  `cc-workflow-evidence-library.js`; `cc-workflow-relevance.js`; `cc-workflow-tailor-offer.js` Stage-3
  tailor pack (match/CV/cover-letter/gap-report/prefill-pack); `ajoa-kit ats-check` parse-safety (#9);
  style/tone tailoring (#16); cited delivery safety note (research.md §Delivery, #8); structured board
  catalog (#10); runtime-configurable pre-filter keywords (`config/keywords.json`, #31);
  `ajoa-kit trend-snapshot` → keyword-only `results/trends.ndjson` (#11 PR-A); the reusable
  `run-with-keywords` workflow (#79); baseline gates (ruff, pyright, complexipy, pytest,
  CodeQL/Dependabot/CI, markdownlint+lychee).
- **Designed:** locale-aware document conventions (#12); the trends dashboard UI (#11 PR-B / #71,
  keyword-only — the `pseudonymize-text` PII gate (#52) is now belt-and-suspenders).
- **Dropped (YAGNI):** team mode, dual modes, validation ceremony, slide decks.
