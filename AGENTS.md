# AGENTS.md

Behavioural rules for AI coding agents working in this repo. A rulebook, not a knowledge
base — operational recipes and machine-specific quirks belong in local memory, not here.

## Principles

- **KISS / DRY / YAGNI / AHA** — simplest thing that works; single source of truth; build
  only what is asked; prefer duplication over the wrong abstraction (extract at the third use).

## Constraints

- **Never delete existing code unless asked.**
- **Pin every Actions `uses:` to a full-length commit SHA** (never a tag).
- **No PII in the repo.** See [docs/architecture.md §Data layout](docs/architecture.md#data-layout)
  for the authoritative git-ignored paths.
- **No automated submission; read-only public GET only.** A human reviews and submits. See
  [docs/research.md §Delivery](docs/research.md#delivery) for the safe/unsafe boundary.
- **Python**: target `pydantic` for structured config/models (no `TypedDict` / `dataclass`);
  keep pure logic importable without the network layer (lazy-import `polyfetch_scrape`).

## Quality gates

- `make check` (ruff lint + `ruff format --check` + `pyright` + `complexipy` + offline `pytest`) must
  pass — the same gate CI runs.
- `make docs-lint` (markdownlint + lychee) — locally, and enforced in CI via the `lint-md-links` workflow.
- Tests earn their place: non-trivial, value-add only — no import/constant/trivial-slice tests.
- New behaviour follows TDD (red → green); ported behaviour is pinned with regression tests.

## Quality thresholds (self-review before opening a PR)

- Context completeness >= 8/10 · Clarity >= 7/10 · No incoherence with existing patterns.
