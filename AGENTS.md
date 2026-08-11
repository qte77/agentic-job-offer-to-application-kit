# AGENTS.md

Behavioural rules for AI coding agents working in this repo. A rulebook, not a knowledge
base — operational recipes and machine-specific quirks belong in local memory, not here.
Recurring mistakes and their promoted fixes are logged in
[AGENT_LEARNINGS.md](AGENT_LEARNINGS.md) (the compound-learning log).

## Principles

- **KISS / DRY / YAGNI / AHA** — simplest thing that works; single source of truth; build
  only what is asked; prefer duplication over the wrong abstraction (extract at the third use).

## Constraints

- **Never delete existing code unless asked.**
- **Pin every Actions `uses:` to a full-length commit SHA** (never a tag).
- **Architecture (ADR-0001).** New code follows the four-layer model — L1 lib / L2 CLI / L3 JS
  workflows / L4 ui, one-way imports only — see
  [docs/decisions/0001-backend-cli-ui-separation.md](docs/decisions/0001-backend-cli-ui-separation.md).
  Orchestration runs via the Claude Code Workflow tool (inline `agent()` subagents, no team mode); see
  [docs/architecture.md §Three mechanics](docs/architecture.md#three-mechanics-that-define-it).
- **No PII in the repo.** See [docs/architecture.md §Data layout](docs/architecture.md#data-layout)
  for the authoritative git-ignored paths.
- **No automated submission; read-only public GET only.** A human reviews and submits. See
  [docs/research.md §Delivery](docs/research.md#delivery) for the safe/unsafe boundary.
- **Source ToS tiers (ADR-0002).** New/changed ingest sources must be ToS/ToU-tiered (OK/CAUTION/
  BLOCKED) and reachability-verified before shipping in `config/default-seed.json`
  `feeds`/`ats`/`aggregators` — see
  [docs/decisions/0002-source-tos-tiers.md](docs/decisions/0002-source-tos-tiers.md).
- **Python**: target `pydantic` for structured config/models (no `TypedDict` / `dataclass`);
  keep pure logic importable without the network layer (lazy-import `polyfetch_scrape`).
- **Parse on read, not only on write.** Structured data re-entering Python across a layer boundary
  is parsed into its model at the read, never consumed as a raw `json.loads(...).get(...)` — a
  contract enforced only on the write side rots silently at the next hop. Untyped boundaries that
  predate this rule are ranked in
  [ADR-0003](docs/decisions/0003-data-contract-enforcement.md); extend a model rather than adding a
  bespoke `.get()` beside it.
- **Network-touching subcommands** (`ingest` / `probe` / `refresh` / `verify-sources` /
  `discover`) import the fetch layer from the sibling
  [polyfetch-scrape](https://github.com/qte77/polyfetch-scrape) checkout — run them via the
  venv-borrow (see [CONTRIBUTING §Polyfetch venv-borrow](CONTRIBUTING.md#polyfetch-venv-borrow));
  never add it as a hard dependency.

## Quality gates

- `make check` (ruff lint + `ruff format --check` + `pyright` + `complexipy` + offline `pytest`) must
  pass — the same gate CI runs.
- `make docs_lint` (markdownlint + lychee) — locally, and enforced in CI via the `lint-md-links` workflow.
- Tests earn their place: non-trivial, value-add only — no import/constant/trivial-slice tests.
- New behaviour follows TDD (red → green); ported behaviour is pinned with regression tests.

## Quality thresholds (self-review before opening a PR)

- Context completeness >= 8/10 · Clarity >= 7/10 · No incoherence with existing patterns.

## Progress reporting

- Report multi-step work as a `[ ]` / `[x]` checklist so state stays glanceable; no percentage meters.
