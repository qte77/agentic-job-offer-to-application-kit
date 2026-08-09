# Agent Learnings

Append-only log of cross-session patterns and their fixes, per the project's compound-learning rule:
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

## A thin page may be a disclosure widget, not a render problem

**Pattern:** A careers/JD page returns only titles. The reflex — learned from a page that really was
JS-rendered — is to escalate the fetch tier to patchright. But when the content sits behind an
accordion / tab / "show more", **every non-interactive tier reports the same thin page, including a
full patchright render with `wait_until: networkidle`.** Waiting longer never helps: Radix (and
friends) mount panel children only on open, so the text is not in the DOM at all. Four attempts were
spent on Lobby AI's careers page, and the diagnosis written down after them ("the JD content is
JS-rendered") was wrong in a way that would have produced a fifth.

**Fix:** Before concluding a page is thin, grep the *served HTML* for `data-state="closed"`,
`aria-expanded="false"`, or an empty `hidden` panel. If present, drive the page rather than
re-fetching it — `RenderOptions.actions` with `click` / `click_text`, then a short `wait_ms`:

```python
RenderOptions(
    actions=(
        RenderAction(verb="click_text", text="<role title>"),
        RenderAction(verb="wait_ms", ms=1000),
    )
)
```

Rendering is not interacting. This is the same rule the unattended-execution guidance states for UI
e2e ("click buttons, dropdowns and other interactive elements") — it applies to ingest too.

## Stage workflows are name-invocable from `.claude/workflows/`

**Pattern:** Long `Workflow({ scriptPath: '.claude/workflows/cc-workflow-*.js', … })` invocations.

**Fix:** Since the workflows live in `.claude/workflows/`, invoke them by their `meta.name`:
`Workflow({ name: 'relevance' | 'tailor-offer' | 'evidence-library', args: { … } })`.
