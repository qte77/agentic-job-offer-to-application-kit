# Architecture — agentic-job-offer-to-application-kit

A generic pipeline (config → Python engine → results) with LLM/agent phases. Claude Code is the
on-demand orchestrator (Workflow-tool scripts), but the phases are described agent-agnostically so
other coding agents can drive them.

The repo follows a four-layer separation — backend / CLI / orchestration / UI, one-way imports
only — per [ADR-0001](decisions/0001-backend-cli-ui-separation.md). Ingest source ToS/ToU tiers are
governed by [ADR-0002](decisions/0002-source-tos-tiers.md).

## Pipeline

```mermaid
flowchart TD
  ext[("ATS / feed / aggregator APIs<br/>public no-auth GET")] -->|fetch| poly[("polyfetch-scrape<br/>httpx → curl_cffi → headless")]
  seed["config/seed.json<br/>(+ default-seed.json)"] --> ingest["ingest.py<br/>adapters · pre-filter · dedupe"]
  kw["config/keywords.json"] -. vocab .-> ingest
  poly --> ingest
  ingest --> raw["results/jobs-raw.json<br/>active pull"]
  ingest -->|"--merge"| corpus["results/corpus.json<br/>incremental corpus #164"]
  corpus --> digest["results/daily-summary.md<br/>local-only #175"]
  raw --> chunk["chunk.py"] --> batches["results/batches/*.json"]
  ev["results/evidence-library.json<br/>Stage 1"] --> rel["cc-workflow-relevance.js<br/>parallel LLM screen"]
  batches --> rel --> short["results/LANE/shortlist (json + md)"]
  short --> tailor["cc-workflow-tailor-offer.js<br/>per-offer tailor"]
  ev --> tailor --> offers["results/offers/SLUG/*.md<br/>+ ats-check"]
  corpus --> trends["trend-snapshot.py<br/>keyword-only, by first_seen"]
  raw -. fallback .-> trends
  trends --> ndjson["results/trends.ndjson<br/>week + counts"]
  trends --> dndjson["results/trends-daily.ndjson<br/>date + counts"]
  ndjson -->|aggregate only| dbranch["data branch"] --> ui["ui/ dashboard"]
  dndjson -->|aggregate only| dbranch
```

Everything under `results/` stays private (git-ignored locally; a private GHA artifact across runs);
only the aggregate `week + counts` trends cross to the public `data` branch — see
[Systems & data boundaries](#systems--data-boundaries).

Run-once upstream: `cc-workflow-evidence-library.js` → `results/evidence-library.json`.

Side branch (any time after ingest): `ajoa-kit trend-snapshot` reads `results/corpus.json` when present
(bucketing by each JD's `first_seen`), else falls back to `results/jobs-raw.json` (`posted_at`) →
aggregate keyword-only `results/trends.ndjson` (per ISO week) **and** `results/trends-daily.ndjson` (per
day). Weekly is **rolled up from the daily buckets** (`weekly_from_daily`), so the two series can't
disagree; counts are the config-driven vocabulary — no JD content.

**Two-stage trim (cost model):** cheap deterministic pre-filter → LLM relevance screen →
expensive tailoring only on the shortlist.

## User flow

```mermaid
flowchart TD
  ev["Build evidence library<br/>(Stage 1 workflow)"] --> g1{"GATE 1<br/>review evidence-library.json"}
  g1 --> cfg["Author config/seed.json<br/>(+ style / keywords)"]
  cfg --> ing["ajoa-kit ingest (--merge)"] --> chu["ajoa-kit chunk"]
  chu --> rel["relevance workflow (LLM screen)"]
  rel --> g2{"GATE 2<br/>persist + review shortlist"}
  g2 --> pick["pick an offer to tailor"] --> tai["tailor workflow (LLM)"]
  tai --> g3{"GATE 3<br/>review CV / cover / gap / ats-check"}
  g3 --> g4{"GATE 4<br/>fill prefill-pack by hand"}
  g4 --> sub["manual submit on the ATS site"]
  ing -. any time .-> tr["trend-snapshot → data branch → dashboard"]
```

The pipeline is **human-gated at four points** and ends in a manual submission — no automation crosses
into actually applying (see [research.md §Delivery](research.md#delivery)).

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

## Data contracts

What crosses each boundary, and whether it is validated. Only `AppSettings` and the trends contracts
(`WeekCounts` / `DayCounts`) are pydantic today; the L3 workflows validate `agent()` outputs with inline JSON Schema, but that guarantee
is **lost when Python reads the result file back**. The future direction — pydantic parse-on-read at
every cross-layer boundary — is [ADR-0003](decisions/0003-data-contract-enforcement.md) (designed, not
built).

| Contract | Defined at | Typed? | Producer → consumer | Artifact |
|---|---|---|---|---|
| JD record | `ingest.record()` | dict — untyped | adapters → corpus / chunk / trends | `results/jobs-raw.json` |
| Corpus record | `corpus.merge_corpus` | dict + `first_seen` / `last_seen` / `content_hash` | ingest `--merge` → trends / next run | `results/corpus.json` |
| Daily digest | `corpus.summarize_changes` + `render_daily_summary` | dict → markdown | ingest `--merge` → human | `results/daily-summary.md` (local-only) |
| Trends week | `trend_snapshot.WeekCounts` | **pydantic** (write-side) | trend-snapshot → dashboard | `results/trends.ndjson` |
| Trends day | `trend_snapshot.DayCounts` | **pydantic** (write-side) | trend-snapshot → dashboard (#187) | `results/trends-daily.ndjson` |
| Batches + manifest | `chunk.main` | dict — untyped | chunk → relevance | `results/batches/*.json` |
| Shortlist | relevance.js schema / `persist_scored` | JSON-Schema (JS) → dict (Py) | relevance → persist → dashboard | `results/LANE/shortlist.json` / `.md` |
| Offer pack | tailor.js schema / `persist_offer` | JSON-Schema (JS) → dict (Py) | tailor → persist | `results/offers/SLUG/*.md` |
| `must_haves` | tailor.js / `coverage.py` | JSON-Schema (JS) → dict (Py) | tailor → coverage | `coverage-report.md` |
| Evidence library `LIB` | `cc-workflow-evidence-library.js` | JSON-Schema (JS) | Stage 1 → relevance / tailor | `results/evidence-library.json` |
| App settings | `settings.AppSettings` | **pydantic-settings** | every entry point | — (env / cwd) |
| seed / keywords / style | `ingest.load_sources` / `load_keywords`, `style.StyleBrief` | untyped / `@dataclass` | human → ingest / tailor | `config/*.json` |

**Typed today:** `AppSettings`, `WeekCounts` (write). **JS-schema'd at the `agent()` boundary but
untyped on Python re-read:** shortlist, offer pack, `must_haves`, evidence library. **Untyped:** the
JD/corpus records (the highest-volume boundary), batches, and the config files. ADR-0003 ranks the
hardening: `JobRecord` → `ScoredResult` (+ lane-membership check) → shared `must_haves` model →
config-entry models → a single `config/lanes.json`.

## Patterns

- **Pure core, injected `today`** — `corpus.merge_corpus` / `summarize_changes` take the date as an
  argument (the caller passes `date.today()`), so L1 is deterministic and testable; no `datetime.now()`.
- **Lazy `polyfetch_scrape` import** — `ingest.get_json` / `get_bytes` import the fetch stack *inside*
  the function, so the pure logic (and its tests) import offline.
- **Warn-and-continue** — `ingest.collect` wraps each source pull; one bad source lands in `failures`
  and never aborts the run.
- **Dispatch tables** — `ingest.ATS` / `ingest.AGGREGATORS` map a source-type string to its adapter;
  `load_sources` drives them from the seed.
- **Config-overridable vocabulary** — `ingest.load_keywords` reads `config/keywords.json` or falls back
  to module constants; `trend_snapshot` reuses it.
- **Upsert-by-key** — `corpus.merge_corpus` (by JD `id`, four states) and `trend_snapshot.upsert_week`
  (by ISO week) replace in place while preserving the rest.
- **Record factory** — `ingest.record()` is the single fixed-shape dict every adapter emits
  (`canonical_url` applied at construction).
- **Run-scoped artifacts** — `results/` is git-ignored and handed between steps (and across CI runs) as
  a private GHA artifact, never inlined into the orchestrator.
- **Defensive `args` parse** — each L3 workflow script `JSON.parse`s `args` when the Workflow tool
  passes it as a string.
- **Pydantic for published / config contracts** — `WeekCounts` (keeps JD content out of the trends feed
  by construction) and `AppSettings`.

## Systems & data boundaries

**External systems:** `polyfetch-scrape` (the fetch stack, borrowed via `uv run --directory`, never
vendored); public no-auth ATS / feed / aggregator endpoints (read-only GET); GitHub Actions (CI + the
daily `ingest-daily` cron); the orphan `data` branch; gh-pages (the dashboard).

**Data / PII boundary** (paths in [Data layout](#data-layout)):

- `config/` and `results/` are git-ignored — your inputs and every generated artifact stay off `main`.
- The corpus crosses runs only as a **private GHA artifact**; the local-only `daily-summary.md` (#175)
  names companies/titles and is never uploaded or pushed.
- Only the aggregate, keyword-only `week + counts` trends reach the **`data` branch** — `make
  trends-data` builds a one-file tree (just `trends.ndjson`), so nothing else can ride along.
- **No automated submission** — the pipeline ends at a human-reviewed prefill pack; there is no
  auto-submit path.

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
├── src/ajoa_kit/               # engine: ingest, corpus, chunk, persist_scored, persist_offer, ats_check,
│                               #   style, prefill, slug_probe, settings, __main__ (CLI)
├── scripts/ingest.sh           # thin env shim -> ajoa-kit ingest (borrows polyfetch's uv env via POLYFETCH_DIR)
├── config/                     # your inputs — git-ignored except the tracked default-seed.json
│                               #   default-seed.json (shipped sources) · your seed.json overrides it
├── tests/                      # value-add suite (pre-filter, canonical_url, dedup, adapters)
├── examples/alexis-doe/        # self-contained example mirroring config/ + results/ (committed)
├── results/                    # generated outputs — git-ignored, dir kept via .gitkeep
│                               #   evidence-library.json, jobs-raw.json, corpus.json, batches/, <lane>/shortlist.*, offers/<slug>/
├── pyproject.toml / uv.lock    # uv project; ruff + pyright + complexipy + pytest + scriv config
└── .github/                    # codeql + dependabot + ci + lint-md-links + issue-triage + ingest-daily + CODEOWNERS (SHA-pinned)
```

## Data layout

The authoritative list of git-ignored, never-committed paths (so no PII is ever committed) — the
single source of truth that AGENTS.md, README.md, and SECURITY.md link to:

- `config/` — inputs you author (`seed.json`, optional `style.json` / `keywords.json`); git-ignored
  **except** the tracked, PII-free `config/default-seed.json` (the shipped, ToS-vetted default
  source list of public board slugs; tiers per [ADR-0002](decisions/0002-source-tos-tiers.md)). Your
  `config/seed.json` overrides it when present; absent it,
  ingest falls back to the default.
- `results/` — everything generated (`jobs-raw.json`, `corpus.json`, `daily-summary.md`,
  `trends.ndjson`, `<lane>/shortlist.*`, `offers/<slug>/`); git-ignored (dir kept via `.gitkeep`). The
  `daily-summary.md` digest (#175) names companies/titles → **local-only**, never a CI artifact or branch.
- `library/`, `input/` — additional generated/working directories; git-ignored.
- `examples/alexis-doe/` — a committed, self-contained example mirroring `config/` + `results/`.

## Boundary failure policy

| Boundary | Policy |
|---|---|
| ATS/feed fetch (per source) | wrap-continue (one source down ≠ run fails) |
| JD parse (per record) | wrap-continue (skip malformed) — typing planned in [ADR-0003](decisions/0003-data-contract-enforcement.md) |
| config load (seed) | fail-loud (missing/invalid config stops the run) |
| evidence-library load (relevance) | fail-loud (clear "run Stage 1 first") |

## Built vs designed

- **Built:** `src/ajoa_kit/` engine; `AppSettings` config + `ajoa-kit` CLI (ADR-0001 L1/L2);
  `cc-workflow-evidence-library.js`; `cc-workflow-relevance.js`; `cc-workflow-tailor-offer.js` Stage-3
  tailor pack (match/CV/cover-letter/gap-report/prefill-pack + optional coverage-report on JD
  must-have coverage, #55); `ajoa-kit ats-check` parse-safety (#9);
  style/tone tailoring (#16); cited delivery safety note (research.md §Delivery, #8); structured board
  catalog (#10) with ToS/ToU tiers (ADR-0002, #95); runtime-configurable pre-filter keywords (`config/keywords.json`, #31);
  `ajoa-kit trend-snapshot` → keyword-only `results/trends.ndjson` (#11 PR-A) rendered by the two-tab
  no-build `ui/` dashboard (#11 PR-B, vendored Chart.js — synthetic Tab A + aggregate `{week,counts}`
  Tab B); the reusable `run-with-keywords` workflow (#79); baseline gates (ruff, pyright, complexipy,
  pytest, CodeQL/Dependabot/CI, markdownlint+lychee).
- **Built (dashboard UX + CI):** trends bundled **same-origin** at deploy (Pages re-deploys on
  `data`-branch pushes — no cross-origin fetch); expandable shortlist rows → tailored CV + cover
  letter; a market-trends time-frame picker; Repo/Issues header links; `make preview` serves a
  throwaway copy keeping real data out of the source `ui/`; AI issue-triage CI (`issue-triage.yaml`,
  SHA-pinned, GitHub Models, zero-secret).
- **Designed:** locale-aware document conventions (#12); `pseudonymize-text` PII gate (#52,
  belt-and-suspenders for the live dashboard data feed). #71 Vite intentionally not adopted (no-build).
- **Dropped (YAGNI):** team mode, dual modes, validation ceremony, slide decks.
