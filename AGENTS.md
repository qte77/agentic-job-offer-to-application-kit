# AGENTS.md

Behavioural rules for AI coding agents working in this repo. A rulebook, not a knowledge
base — operational recipes and machine-specific quirks belong in local memory, not here.

## Principles

- **KISS / DRY / YAGNI / AHA** — simplest thing that works; single source of truth; build
  only what is asked; prefer duplication over the wrong abstraction (extract at the third use).

## Constraints

- **Never delete existing code unless asked.**
- **Pin every Actions `uses:` to a full-length commit SHA** (never a tag).
- **No PII in the repo.** Only `config/*.example.*` templates are committed; real config and
  everything under `results/` / `library/` / `input/` is git-ignored.
- **No automated submission.** The pipeline produces artifacts for a human to review and
  submit; it uses only public, no-auth, read-only (GET) endpoints.
- **Python**: target `pydantic` for structured config/models (no `TypedDict` / `dataclass`)
  when settings land; keep pure logic importable without the network layer (lazy-import
  `polyfetch_scrape`).

## Quality gates

- `uv run ruff check .` and `uv run ruff format --check .` must pass (config in `pyproject.toml`).
- `uv run pytest -m "not network"` must pass. Tests earn their place: non-trivial, value-add
  only — no import/constant/trivial-slice tests.
- New behaviour follows TDD (red → green); ported behaviour is pinned with regression tests.

## Quality thresholds (self-review before opening a PR)

- Context completeness >= 8/10 · Clarity >= 7/10 · No incoherence with existing patterns.
