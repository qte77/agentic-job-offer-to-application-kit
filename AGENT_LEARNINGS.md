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

## Fetch escalation has three tiers, not two — render, then *drive*

**Pattern:** A careers/JD page yields only role titles. The reflex is to escalate to the browser
tier, and when that still yields only titles, to conclude the fetch cannot get the content. Both
halves of that reflex are wrong: rendering can be **necessary but not sufficient**. Measured on
Lobby AI's `/careers`, which cost four attempts:

| Tier | HTML | Text | Role bodies |
|---|---|---|---|
| `httpx` (no JS) | 3 298 | 1 067 | no — and **no accordion markup either** |
| `patchright`, `wait_until: networkidle` | 13 503 | 1 665 | no — panels present but `hidden=""` and empty |
| `patchright` + two `click_text` actions | 27 371 | **6 313** | yes, both |

Rendering quadrupled the HTML and still looked like a failure, because the JD text sits behind a
Radix accordion and Radix mounts panel children only on open. Waiting longer never helps.

**The trap is that the diagnosis is invisible from the cheap tier.** The static HTML contains zero
occurrences of `aria-expanded`, `data-state="closed"` or `hidden=""` — the app is client-rendered,
so the disclosure markup does not exist until React hydrates. You cannot tell an accordion page from
a genuinely thin one without rendering it first.

**Fix:** when a rendered page is still thin, grep the **rendered** DOM (not the served HTML) for
`data-state="closed"` / `aria-expanded="false"` / an empty `hidden` panel, then drive it —
`RenderOptions.actions`, `click_text` per trigger, a short `wait_ms` after each:

```python
RenderOptions(
    actions=(
        RenderAction(verb="click_text", text="<role title>"),
        RenderAction(verb="wait_ms", ms=1000),
    )
)
```

Rendering is not interacting. This is the rule the unattended-execution guidance already states for
UI e2e ("click buttons, dropdowns and other interactive elements") — it applies to ingest too.

**And the meta-lesson, which cost more than the technique did:** the blocked tool (patchright's
Chromium was missing) prevented the observation that would have discriminated the two hypotheses, so
an untested inference — "the JD content is JS-rendered", reasoned by analogy to another site — got
written into the research file as a finding. It was half true, which is the worst kind: it survived
review and set up a fifth failed attempt. **When the verifying tool is unavailable, record the
question as open, not the guess as the answer** — the same hedge the sibling research file applies
to its own ABSENT verdicts. Restoring the tool cost 177 MB and two minutes.

## A shadowing env token reads as a revoked account

**Pattern:** `gh` resolves credentials `GH_TOKEN` → `GITHUB_TOKEN` → the stored `hosts.yml` token,
so unsetting *one* env var just falls through to the other. A devcontainer's injected `GITHUB_TOKEN`
is an installation token: reads succeed, writes fail `403 Resource not accessible by integration`.
Every signal then points at the wrong culprit — writes that worked an hour ago stop working,
`gh auth status` shows a valid `gho_` token with `repo` scope, and `repos/…/permissions` reports
`admin: true` (that is the *user's* role, not the token's grant). The plausible diagnosis — "the
account lost write access, the owner must re-auth" — is wrong, and acting on it sends a human to
fix a credential that is fine. Cost on 2026-08-10: two failed writes plus a wrong diagnosis
committed into a plan.

**Fix:** Unset **both** on every `gh` and `git push`:

```bash
env -u GH_TOKEN -u GITHUB_TOKEN gh pr merge <n> --squash --admin
```

The tell is `Active account: false` on the stored token in `gh auth status` — check that line, not
the scope list, before concluding anything about permissions. Generally: when a write 403s but reads
pass, suspect *which* credential is being used before suspecting what it is allowed to do.

## Stage workflows are name-invocable from `.claude/workflows/`

**Pattern:** Long `Workflow({ scriptPath: '.claude/workflows/cc-workflow-*.js', … })` invocations.

**Fix:** Since the workflows live in `.claude/workflows/`, invoke them by their `meta.name`:
`Workflow({ name: 'relevance' | 'tailor-offer' | 'evidence-library', args: { … } })`.
