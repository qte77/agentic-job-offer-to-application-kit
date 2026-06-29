# Agent Learnings

Append-only log of cross-session patterns and their fixes, per the compound-learning rule
([.claude/rules/compound-learning.md](.claude/rules/compound-learning.md) / AGENTS.md):
1st occurrence → fix inline; **2nd → record here**; 3rd → promote to `.claude/rules/`; recurring
workflow → extract to a skill. Each entry: **Pattern** (what recurs) · **Fix** (what to do).

---

## Running the pipeline for a real candidate (not the synthetic example)

**Pattern:** The documented `make ingest` / `make chunk` / `make persist` write to the kit's own
`results/` — but real candidate data must never enter the kit repo (PII boundary; AGENTS.md).

**Fix:** Run against a scratch / sibling workspace via the `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR`
overrides, borrowing the polyfetch venv for the network steps:

```bash
AJOA_CONFIG_DIR=<scratch>/config AJOA_RESULTS_DIR=<scratch>/results \
  PYTHONPATH=<kit>/src uv run --directory ../polyfetch-scrape \
  --with pydantic --with pydantic-settings python -m ajoa_kit ingest
```

Stage the candidate's evidence library as `<scratch>/results/evidence-library.json`; all outputs stay
in scratch / the sibling repo, never the kit tree.

## Stage workflows are name-invocable from `.claude/workflows/`

**Pattern:** Long `Workflow({ scriptPath: '.claude/workflows/cc-workflow-*.js', … })` invocations.

**Fix:** Since the workflows live in `.claude/workflows/`, invoke them by their `meta.name`:
`Workflow({ name: 'relevance' | 'tailor-offer' | 'evidence-library', args: { … } })`.
