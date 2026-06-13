# AGENTS.md

Behavioural rules for AI coding agents working in this repo. A rulebook, not a knowledge
base — operational recipes and machine-specific quirks belong in local memory, not here.

## Principles

- **KISS / DRY / YAGNI / AHA** — simplest thing that works; single source of truth; build
  only what is asked; prefer duplication over the wrong abstraction (extract at the third use).

## Constraints

- **Never delete existing code unless asked.**
- **Pin every Actions `uses:` to a full-length commit SHA** (never a tag).
- **No PII in the repo.** Real config (`config/`) and all generated data (`results/`, `library/`,
  `input/`) are git-ignored; only the synthetic `examples/` workspace and the `config/`/`results/`
  `.gitkeep` placeholders are committed.
- **No automated submission.** The pipeline produces artifacts for a human to review and
  submit; it uses only public, no-auth, read-only (GET) endpoints.
- **Python**: target `pydantic` for structured config/models (no `TypedDict` / `dataclass`)
  when settings land; keep pure logic importable without the network layer (lazy-import
  `polyfetch_scrape`).

## Quality gates

- `make check` (ruff lint + `ruff format --check` + offline `pytest`) must pass — the same gate CI runs.
- `make docs-lint` (markdownlint + lychee) for docs, locally.
- Tests earn their place: non-trivial, value-add only — no import/constant/trivial-slice tests.
- New behaviour follows TDD (red → green); ported behaviour is pinned with regression tests.

## Quality thresholds (self-review before opening a PR)

- Context completeness >= 8/10 · Clarity >= 7/10 · No incoherence with existing patterns.
