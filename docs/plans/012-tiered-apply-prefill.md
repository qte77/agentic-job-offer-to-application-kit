# Plan 012 — Tiered auto-open + browser prefill for application URLs (#417)

**Status: IN PROGRESS (2026-09-01).** Phase A item 1 (this doc + `research.md` re-verification)
ships first. Items 2–5 follow as separate PRs; Phase B is a single owner decision gating Phase C.
See the remaining-work table below for live state.

## Context

Issue #417 asks for three tiers of browser assistance on a shortlisted offer's application page,
built on `polyfetch-scrape`'s `render_session` (not a hand-rolled Playwright driver): **tier 1**
open the offer URL in a tab, **tier 2** locate/highlight the form's fields, **tier 3** script
actual values into fields — never submit. `docs/research.md`'s 2026-09-01 addendum is the project
owner's own dated, scoped exception to the otherwise-absolute "never drive a browser autofill
extension" rule, narrowed to exactly this: fill-without-submit, gated per action, never a batch
"do it for everyone" mode.

Two gating steps the issue and `research.md` both demand before any tier-3 code, done this session:

- **Re-verified all 8 primary sources** cited in `research.md` §Delivery (Greenhouse, Ashby, Lever,
  Workable API+ToS docs; LinkedIn/Indeed automation clauses) against their live current text. **All
  8 claims still hold.** Two doc facts changed (fixed in this PR, not a re-think): Greenhouse's
  docs URLs redirect `developers.` → `docs.greenhouse.io` (content unchanged); Workable's
  application-question schema — noted "unconfirmed" — is now confirmed to need `r_jobs` Bearer
  auth (401 without), same gated pattern as Ashby. Nothing found bears on the fill-without-submit
  addendum either way — no platform has ToS/bot-detection language specific to scripted
  field-filling as opposed to submission or scraping.
- **Read the addendum in full**; its hard constraints are pulled forward into Invariants below.

Two load-bearing technical facts verified directly at source (not a secondhand plan note):

- `render_session` (`polyfetch-scrape/src/polyfetch_scrape/render_session.py`, `RenderSession.__enter__`)
  hardcodes `self._browser = self._pw.chromium.launch(headless=True)` — no parameter overrides it
  today.
- There is **no structured, machine-readable candidate profile anywhere in this repo**
  (`prefill.py`'s `GENERIC_FIELDS` is a field *schema* — name/label/type — carrying no values;
  `values` there means option labels for selects). Real values need a new git-ignored
  `config/*.json`, matching `location.json`/`style.json`/`manual-jds.json` (`.gitignore` ignores
  `config/` at any depth; `default-seed.json` stays tracked only because it's already
  committed — git never untracks a tracked file — so a new `candidate.json` is safely ignored by
  the existing rule, no gitignore edit needed).

An advisor review corrected the initial tier-3 design: a headless-only "fill it, screenshot it,
close it, human retypes everything in their own browser" flow satisfies none of the addendum's
"human reviews *and submits*" intent — the labor saved would be zero. The real design threads a
`headless` seam through `render_session` (a small, pre-stageable `polyfetch-scrape` change) so a
human can watch the fill happen and submit from that same window. That is a cross-repo,
owner-gated decision — Phase B.

## Decision: CLI-only trigger (ratified, not deferred)

Issue #417 flagged "CLI vs UI-triggered action" as needing a real decision. Evidence collected
this session settles it:

- `ui/` is **100% static** — every network call in `ui/src/*.js` is a same-origin `fetch()` of a
  local JSON file; zero calls to any backend/localhost API. ADR-0001 states Layer 4 "does **not**
  ship in the wheel" and Layer 1 "MUST NOT... assume `scripts/` or `.claude/workflows/` exist" —
  one-way import rule.
- No precedent anywhere in this repo for a UI element triggering a backend/local action.
- `render_session` is headless regardless — even a UI button click would need a companion local
  server to invoke a script the user can't see differently than a CLI run would show them. A UI
  trigger buys nothing tier 1's existing `<a target="_blank">` (`ui/src/shortlist.js`) doesn't
  already give for free.

**Decision: CLI subcommands only, matching the existing Layer-2 pattern.** No companion server, no
UI changes.

## Invariants (every tier, non-negotiable per the addendum)

- No code path may ever call `.click()`/`.press("Enter")` on a submit control, or anything that
  could advance a form toward submission.
- Tier 3 acts on **exactly one offer per invocation** — no `--all`, no `--min-score`/`--lanes`
  batch flags. The CLI invocation itself *is* the per-action human trigger.
- Tier 3 fills **text + select fields only** this arc (`page.fill`/`press_sequentially` +
  `page.select_option`, matching the addendum's named verbs). File uploads (`set_input_files`) and
  free-text per-offer Q&A values (prose-only in `prefill-pack.md` today, no structured source) are
  explicitly deferred — located/highlighted (tier 2), never auto-filled.
- Controlled-input forms (React/Vue/Svelte — common on Greenhouse/Ashby/Lever/Workable) need
  `page.locator(...).press_sequentially(value, delay=25)`, **not** `s.fill()` — `s.fill()` sets the
  DOM value directly and silently leaves framework state (and the eventual submitted payload)
  stale (`polyfetch-scrape/docs/scripting.md` §"Framework-controlled inputs").
- e2e tests run only against **local synthetic fixture forms**, never a real employer's live
  application page.

## Source map (reuse, don't rebuild — verified 2026-09-01)

**CLI dispatch pattern** `src/ajoa_kit/__main__.py` — `_verb(args)` wrapper (lazy-imports
polyfetch-dependent code) + `sub.add_parser(...)` + `.set_defaults(func=_verb)`; `AppSettings()` is
constructed inside each L1 module's `main()`, not in `__main__.py`.

**Settings** `src/ajoa_kit/settings.py` — `AppSettings.config_dir` (default `config/`, env
`AJOA_CONFIG_DIR`); no new field needed, `candidate.json` lives under it.

**Config-loader pattern to mirror** `src/ajoa_kit/pack_plan.py` `load_policy()` — absent file →
model default, present file → `Model.model_validate(json.loads(...))`.

**Pydantic models** `src/ajoa_kit/models.py` — add `CandidateProfile` here (`PackPolicy` and
`ScoredItem` are the existing neighbors).

**Selection surface to reuse** `src/ajoa_kit/pack_plan.py` `select(shortlist_rows, policy)` —
filters/sorts `ScoredItem`s. **`pack-plan.json`'s on-disk output drops `.url`** (stripped in
`main()`) — tiers 1/2/3 must call `select()` as a library function and read `.url` off the
in-memory `ScoredItem`s before that stripping, or read `results/<lane>/shortlist.json` directly.

**Offer-index (has-a-pack check)** `src/ajoa_kit/persist_offer.py` `_load_offer_index()` —
`pack_plan.missing()` targets offers **without** a pack; tiers 2/3 need the inverse — intersect
`select()`'s output **with** the offer index, not exclude.

**Field schema (Greenhouse)** `src/ajoa_kit/prefill.py` — `GENERIC_FIELDS` (schema only, no
values), `fetch_greenhouse_questions()`/`parse_greenhouse_questions()` — reuse for tier 2's
Greenhouse schema-diff.

**Pack directory layout** `src/ajoa_kit/persist_offer.py` `write_pack()` —
`results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md` + `meta.json`
(`{id, slug}`).

**Rendered PDFs (future file-upload use)** `src/ajoa_kit/render_pdf.py` — opt-in, manual
(`ajoa-kit render-pdf <file>`), not run automatically; deferred item 9 depends on this existing
first.

**`render_session` (headless-hardcoded)**
`../polyfetch-scrape/src/polyfetch_scrape/render_session.py` — `RenderSession.__init__`/
`render_session()`, no `headless` param; public surface `click`/`click_text`/`fill`/`submit`/
`wait_for_selector`/`wait_for_function`/`wait_ms`/`shot`, plus `.page`.

**Scripting gotchas** `../polyfetch-scrape/docs/scripting.md` — controlled-input fill gotcha,
`evaluate` isolated-world gotcha, screenshots-as-ground-truth.

**UI tier-1 precedent** `ui/src/shortlist.js` — `<a href="${it.url}" target="_blank">` — confirms
`url` as the canonical field name, browser-only.

**Quickstart doc pattern to extend** `docs/quickstart.md` §"Location + work-authorization
advisory" (`config/location.json`) — mirror this section's shape for `config/candidate.json`.

**Headless-browser e2e pattern** repo memory `reference-headless-browser-ui-checks.md` — `uv run
--directory ../polyfetch-scrape python <script>`, capture `page.on("console")`, screenshots as
ground truth, not `page.evaluate` on page-owned globals.

**Devcontainer gotcha** repo memory `reference-devcontainer-playwright-cache-symlink.md` —
`mkdir -p` the `~/.cache/ms-playwright` symlink target before `patchright install` after a
container restart.

## Work breakdown

**Phase A — agent-only, front-loaded (5 PRs, in order):**

1. **This doc + handoff + `docs/research.md` fix**: 2026-09-01 re-verification note; two Greenhouse
   URLs (`developers.` → `docs.greenhouse.io`); Workable uncertainty → confirmed-gated. Ships
   first, closes the issue's step 1 visibly.
2. **`config/candidate.json` scaffold**: `CandidateProfile` pydantic model (first_name, last_name,
   email, phone, linkedin, website — mirrors `GENERIC_FIELDS`'s text fields, file-upload fields
   excluded per invariants); a loader mirroring `pack_plan.load_policy()`; document in
   `quickstart.md` beside `location.json`. TDD: model validation only.
3. **Tier 1 — `ajoa-kit open-offers`** (`src/ajoa_kit/open_offers.py`): `--min-score`/`--lanes`
   (reuses `PackPolicy`/`select()`), reads `.url` off `ScoredItem` from `shortlist.json` directly,
   opens each via stdlib `webbrowser.open(url)` — **not** `render_session` (headless, can't show a
   human anything). Flag this deviation explicitly in the PR body. TDD the selection→URL join as a
   pure function; `webbrowser.open` itself is untestable in this devcontainer (no display).
4. **Tier 2 — `ajoa-kit locate-fields <offer-id>`** (`src/ajoa_kit/locate_fields.py`): offers that
   already have a pack (`select()` ∩ `_load_offer_index()`). Via `render_session`: locate fields by
   label/placeholder text; for Greenhouse offers, diff against `fetch_greenhouse_questions()`'s
   live schema first, generic heuristics after. Highlight via locator style mutation + `s.shot()`.
   Writes `results/offers/<slug>/tier2-locate.png` + `locate-report.md`. Read-only, no fill. e2e
   against local fixtures.
5. **Tier 3 dry-run — `ajoa-kit fill-offer <offer-id>`** (`src/ajoa_kit/fill_offer.py`): single
   offer only, no batch flags. Reads `config/candidate.json`, reuses tier 2's field-locate logic,
   fills text via `press_sequentially` and selects via `page.select_option` — never `s.fill()`.
   Writes `fill-report.md` + final screenshot. Ships headless-only (functional, testable);
   structured so a `headed: bool` seam threads in later without a rewrite. e2e proves
   `press_sequentially` correctly fills the React-controlled fixture where `s.fill()` would
   silently leave it stale.

   Also pre-stage (draft locally, **do not push**) the `polyfetch-scrape` diff: add
   `headless: bool = True` to `RenderSession.__init__` and `render_session()`, threaded to
   `self._pw.chromium.launch(headless=headless)` — the only change needed there; the
   "wait for the human before closing" logic (an `input()` prompt before the `with` block exits)
   lives entirely in `fill_offer.py`.

**Phase B — ONE owner sitting (the actual gate):**

Present the pre-staged `polyfetch-scrape` diff and this tradeoff:

- **Headed (recommended default):** push the polyfetch-scrape PR, wire `ajoa-kit fill-offer <id>
  --headed` to open a visible window, fill fields, and wait for a human keypress before closing —
  the human reviews *and submits* in that same window.
- **Stay dry-run-only:** no cross-repo change; `fill-offer` remains a verification tool only
  (screenshot + report), human re-does the fill by hand using the report as reference.

**Phase C — activation (only if headed is chosen):**

1. Push the polyfetch-scrape PR, bump the pin once merged, wire `--headed` in `fill_offer.py`,
   full e2e across all three tiers against local fixtures, close out #417.

## Doc-impact audit (checked against current file content, not assumed)

| Doc | Update | What |
|---|---|---|
| `CHANGELOG.md` (scriv) | items 2–5 (+8) | Each behaviour-changing → `make changelog_new` fragment. Item 1 is pure docs, exempt. |
| `README.md` | yes | §How: optional-config paragraph for `candidate.json` (mirrors `location.json`/`tenure.json`/`manual-jds.json`); one sentence naming the 3 new subcommands; Constraints line gets a clause cross-referencing the addendum. |
| `CONTRIBUTING.md` | yes | §CLI subcommands table: 3 new rows. §Pipeline: one optional line after `render-pdf`. §Environment: no new row (no new env var). |
| `docs/architecture.md` | yes | §Data contracts: new `CandidateProfile` row. §User flow mermaid: tiers as an optional assist step between GATE 4 and manual submit. §Repo structure: add the 3 new modules. §Built vs designed: bullets once shipped. §Data/PII boundary line: same cross-reference clause. |
| `docs/roadmap.md` | yes | "Arc-012 (plan 012)" under **Next** now; **Shipped** as phases close; items 9–10 → **Later**. |
| `docs/userstory.md` | yes | New **US9** — tiered browser assist. |
| `docs/quickstart.md` | yes | New optional subsection mirroring §"Location + work-authorization advisory". |
| ADRs | no new ADR | Extends ADR-0001's existing Layer-2 pattern; doesn't set a new rule. |

No new URL, no new env var, 3 new CLI switches (`open-offers`, `locate-fields`, `fill-offer`) —
all land in `CONTRIBUTING.md`'s subcommand table, the single source of truth other docs link to.

## Issues

- **#417** stays open through Phase A/B; comment progress per merged PR; record the CLI-only
  decision there at PR-1 time. Close only once Phase C resolves, or the owner picks dry-run-only
  at the Phase B gate (close with a comment stating that scope).
- File two follow-on issues at the end of Phase A for items 9 (file-upload fields) and 10 (custom
  per-offer Q&A auto-fill), referencing #417 and this plan.
- Checked for overlap with existing open issues (`gh issue list --search "prefill OR autofill OR
  browser OR apply-url"`): only #417 is relevant; #365/#366 (pack-drift) and #341 (polyfetch-scrape
  docs publish) are unrelated.

## Remaining-work table (exactly one; source of truth for what's open)

| # | Item | Gate | Done-when |
|---|---|---|---|
| 1 | This plan + handoff + `research.md` re-verification fix | agent | PR merged with the three doc edits |
| 2 | `config/candidate.json` scaffold (model + loader + quickstart doc) | agent | PR merged; model unit-tested; quickstart documents it |
| 3 | Tier 1 — `open-offers` CLI | agent | PR merged; selection/url-join unit-tested; PR notes the `webbrowser` deviation + untestable-headless caveat |
| 4 | Tier 2 — `locate-fields` CLI | agent | PR merged; e2e passes against both local fixture forms; artifacts land under `results/offers/<slug>/` |
| 5 | Tier 3 dry-run — `fill-offer` CLI (headless, single-offer, text+select only) | agent | PR merged; e2e proves `press_sequentially` succeeds where `fill()` would silently fail |
| 6 | Pre-staged `polyfetch-scrape` diff (`headless` param) | agent, pre-staged only | Diff drafted + validated locally; **not pushed** until item 7 resolves |
| 7 | Owner decision: headed vs. dry-run-only | owner | Decided at the Phase-B sitting; recommended default = headed |
| 8 | Wire tier-3 headed mode | agent (conditional on 7 = headed) | `fill-offer <id> --headed` opens a visible window, fills, waits for human keypress, never auto-closes-then-discards |
| 9 | File-upload fields (`set_input_files`) | owner (deferred) | Follow-on issue filed; out of this arc |
| 10 | Custom per-offer Q&A auto-fill | owner (deferred) | Follow-on issue filed; tier 2 locates/highlights only, this arc |

## Testing

- **Unit (TDD, `make check`):** `CandidateProfile` validation; selection→URL join (tier 1);
  field-matching heuristic (tier 2, pure function over field descriptors, no browser);
  profile→field-name→value mapping (tier 3). All offline-importable (lazy-import
  `polyfetch_scrape`).
- **e2e (outside `make check`, run manually via the polyfetch venv-borrow):** two local synthetic
  fixtures under `tests/fixtures/forms/` — a plain HTML form and a controlled-input variant (a
  minimal hand-rolled `oninput`-bound JS state, not real React — proves the `press_sequentially`
  vs `fill` gap without a framework dependency) — served via stdlib `http.server` on `localhost`
  (not `127.0.0.1`). Run tier 2 and tier 3 against both; tier 1 e2e is limited to the
  selection/URL logic (no display in this devcontainer). Remember the devcontainer
  Playwright-cache `mkdir -p` gotcha before `patchright install`.

## Git workflow

New branch per topic (one per numbered Phase-A item); commits by topic; push, PR, squash-merge
only on green; delete both remote and local branch after merge. Subagents doing implementation
work use a git worktree (`isolation: "worktree"`), one per topic branch.
