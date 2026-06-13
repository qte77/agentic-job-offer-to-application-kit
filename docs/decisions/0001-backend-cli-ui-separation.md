# ADR-0001 — Backend / CLI / orchestration / UI separation

**Status:** Accepted (2026-06-13)

**Relates to:**
Mirrors `analyze-stock-kpi`
[ADR-0007](https://github.com/qte77/analyze-stock-kpi/blob/main/docs/decisions/0007-package-vs-infrastructure-boundary.md)
(three-scope distribution model + one-way import rule) — adopted here
with the same wording so the two sibling repos share one separation
schema. Predecessor pipeline: `../2026-06-job-research/HANDOFF.md`
(the `scripts/{ingest,chunk,persist_scored,probe_slugs}.py` this repo
productizes; filed issues #4–#12). First ADR in this repo — establishes
`docs/decisions/`.

## Context

The kit productizes the job-research pipeline
(ingest → chunk → relevance → tailor) into an installable tool. Today:

- `src/ajoa_kit/{ingest,chunk,persist_scored,slug_probe}.py` — each
  anchored by a hardcoded `ROOT = Path(__file__).resolve().parents[2]`.
- No `__main__.py`, no `[project.scripts]` entry point — modules are
  invoked ad hoc (`python -m ajoa_kit.<module>`) or via `scripts/ingest.sh`.
- LLM orchestration lives in `docs/workflows/cc-workflow-*.js`, run via
  the Workflow tool — a tier distinct from any conventional CLI.
- No `docs/decisions/`; no UI surface.

As the CLI, a trends dashboard (#11), the Stage-3 tailoring workflow
(#8), and more adapters land, "what belongs where?" needs a rule before
drift sets in — the same risk `analyze-stock-kpi` ADR-0007 addressed.
A downstream user who installs the kit should get the library + CLI —
not the Workflow JS scripts, not a dashboard, not anyone's job data.

## Decision

The repository splits into **four layers** with one direction rule.
The first three map onto ADR-0007's three scopes; the fourth
(orchestration) is unique to this repo's agentic tier.

### Layer 1 — Backend / library (`src/ajoa_kit/`)

Pure importable logic; ships in the wheel. Imports `polyfetch_scrape`
**lazily inside functions** (already the case) so the logic is importable
and testable without the network. Configuration moves from the hardcoded
`ROOT` constant to `AppSettings(BaseSettings)` (pydantic-settings) with
env-overridable `config/` and `results/` paths.

Examples: `ingest.py`, `chunk.py`, `persist_scored.py`, `slug_probe.py`,
a future `settings.py`, the structured sources catalog (#10).

### Layer 2 — CLI (`src/ajoa_kit/__main__.py` + `[project.scripts] ajoa-kit`)

An `argparse` dispatcher (`main()`) routing `ingest` / `chunk` /
`persist` / `probe` subcommands to the matching Layer 1 module — each
delegates to the library with explicit args, and `AppSettings` supplies
the env-overridable paths. (Subcommand dispatch uses `argparse`, not
`BaseSettings(cli_parse_args=True)` — the latter is for settings-driven
flags, not routing.) `scripts/ingest.sh` reduces to a thin env shim
(borrows polyfetch's `uv` env so `polyfetch_scrape` imports, and anchors
`AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` to the repo root so paths resolve
from any CWD); `Makefile` targets map to subcommands. Ships in the wheel.

### Layer 3 — LLM orchestration (`docs/workflows/cc-workflow-*.js`)

The agentic fan-out tier, run via the Workflow tool — **separate from
the conventional CLI** (Layer 2). Repo infrastructure; does **not** ship
in the wheel. Carries the Stage-2/3 workflows: relevance screen
(#7, built), `cc-workflow-tailor-offer.js` (#8, designed — per-offer
pack, **pre-fill + human submit only, NO auto-apply**), ats-check (#9),
locale templates (#12); cc-workflow naming + batch-args convention (#4).

### Layer 4 — UI (`ui/`)

Static Chart.js SPA (trends dashboard, #11) consuming a public `data`
branch JSON; EyeRest-themed (see Brand below). Forks the
`analyze-stock-kpi` `ui/` scaffold — DOM-free, data-shape-agnostic
`lib/`. Does **not** ship in the wheel.

### Rule — Direction (one-way only)

- **Layers 2 / 3 / 4 MAY import from Layer 1.** The CLI, the Workflow
  scripts, and the UI all consume the library API.
- **Layer 1 MUST NOT** import from the CLI / orchestration / UI, MUST
  NOT assume `scripts/` or `docs/workflows/` exist, and MUST NOT read or
  write the `data` branch. The `data` branch is consumed only by Layer 4.

### HARD GATE — PII (kit-specific; no `analyze-stock-kpi` analogue)

Job data is third-party PII. **No job data reaches a public `data`
branch or the UI without pseudonymization** (`pseudonymize-text`,
roadmap "Later"). Layer 4 consumes only pseudonymized corpora. Real
applicant PII (name/contact/work-history) stays out of the repo —
uncommitted `config/`, injected at run time.

### Brand

The UI uses the EyeRest tokens from `qte77/qte77/brand/DESIGN.md`
(zero-blue, warm amber) referenced by pointer — same source as the
`analyze-stock-kpi` dashboard. Never a blue accent.

## Consequences

- Backend becomes config-driven and offline-testable (no `ROOT` magic).
  `AppSettings` is the seam the job-research sourcing model
  (SEED/DEFAULT_SEED/aggregator tiers, `config/default-seed.json`,
  URL-first dedup) plugs into later — productized per issue, not forked
  from job-research WIP (that repo is read-only).
- A real entry point (`ajoa-kit`) replaces ad-hoc module invocation.
- New runtime deps: `pydantic` + `pydantic-settings` (today only
  `defusedxml`). Aligns with the kit convention "pydantic for settings".
- UI work is gated behind PII pseudonymization.
- The `cc-workflow-*.js` tier is explicitly **not** the CLI — keeps the
  two from being conflated as the kit grows.

## Out of scope (own follow-on PRs)

- The UI build (#11) — after the scrape scaffold + PII gate.
- Extracting a shared UI library package — wait for a 3rd consumer (AHA).

## References

- `analyze-stock-kpi` ADR-0007 — three-scope model + one-way import rule.
- `../2026-06-job-research/HANDOFF.md` — predecessor pipeline + sourcing
  model + Stage-3 tailoring design.
- Kit issues #4 (cc-workflow naming), #5 (ingest adapters), #6 (slug
  probe), #7 (relevance), #8 (delivery pre-fill), #9 (ats-check),
  #10 (sources catalog), #11 (trends dashboard), #12 (locale).
