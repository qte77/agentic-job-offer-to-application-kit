# Plan 012 — Tiered auto-open + browser prefill for application URLs (#417)

**Status: SHIPPED, SCOPE REDUCED (2026-09-01).** Item 1 shipped (#420); item 3, tier 1
`open-offers`, shipped (#421). **Tiers 2 and 3 are deferred by owner decision** — see "Scope
change" below. This arc's active scope is now complete; #417 stays open, scoped to tier 1 only.

## Scope change (2026-09-01) — tiers 2 and 3 deferred

After item 1 shipped, the owner asked how tier 1 actually delivers a page to the human, since
`render_session` is headless. The honest answer surfaced a problem that applies beyond tier 1:

- **Tier 1** doesn't use `render_session` at all — it uses stdlib `webbrowser.open(url)`, which
  hands the URL to the user's own already-running default browser (the same mechanism as clicking
  a link). Zero automation footprint on the target site; this is unaffected by anything below and
  proceeds as planned.
- **Tiers 2 and 3**, by contrast, *do* need `render_session` to interact with the page — and a
  stealth-Patchright headless browser navigating and manipulating a real ATS form's DOM (even
  read-only field-location in tier 2, before any fill) is itself a form of automated access to that
  page, carrying a real bot-detection / account-flagging risk to the candidate — separate from and
  in addition to the "can a human even watch it happen" problem tier 3 already had (Phase B was
  never resolved — no owner sign-off on a headed-browser change to `polyfetch-scrape`).

**Decision: tiers 2 and 3 are deferred, not built this arc.** Items 2 ( `config/candidate.json` —
its only consumer was tier 3), 4 (tier 2), 5 (tier 3 dry-run), 6 (pre-staged `polyfetch-scrape`
diff), 7 (the Phase B owner decision), and 8 (headed-mode wiring) are all deferred as a set — see
the remaining-work table. #417 stays open, scoped down to tier 1 only for now; re-opening tiers 2/3
needs a fresh design that doesn't route page-interaction through an automated headless session, or
an explicit owner call that the bot-detection/ban risk is acceptable.

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

**Active scope (post scope-change):**

1. **This doc + handoff + `docs/research.md` fix** — SHIPPED, PR #420. 2026-09-01 re-verification
   note; two Greenhouse URLs (`developers.` → `docs.greenhouse.io`); Workable uncertainty →
   confirmed-gated.
2. **Tier 1 — `ajoa-kit open-offers`** (`src/ajoa_kit/open_offers.py`) — SHIPPED, PR #421.
   `--min-score`/`--lanes` (reuses `PackPolicy`/`select()`), reads `.url` off `ScoredItem` from
   `shortlist.json` directly, opens each via stdlib `webbrowser.open(url)` — **not**
   `render_session` (headless, can't show a human anything) — a deliberate, documented deviation
   from #417's "all tiers via polyfetch" framing. `selected_urls()` is unit-tested;
   `webbrowser.open` itself is untested (no display in this devcontainer).

**Deferred (see "Scope change" above for why) — kept here only as a record of what was designed,
not a queue to resume without a fresh decision:**

- ~~`config/candidate.json` scaffold~~ — `CandidateProfile` pydantic model, loader mirroring
  `pack_plan.load_policy()`, `quickstart.md` doc. Deferred: sole consumer (tier 3) deferred.
- ~~Tier 2 — `ajoa-kit locate-fields <offer-id>`~~ — via `render_session`, locate fields by
  label/placeholder text (Greenhouse schema-diff first, generic heuristics after), highlight +
  `s.shot()`, write `tier2-locate.png` + `locate-report.md`. Deferred: headless page-interaction
  itself carries bot-detection/ban risk, even read-only.
- ~~Tier 3 dry-run — `ajoa-kit fill-offer <offer-id>`~~ — single offer, `press_sequentially` +
  `page.select_option`, `fill-report.md` + screenshot, headless-only with a `headed: bool` seam for
  later. Deferred: same risk as tier 2, plus the headed-browser question below was never resolved.
- ~~Pre-staged `polyfetch-scrape` diff~~ (`headless: bool = True` param on `RenderSession`) —
  deferred, not drafted; moot while tier 3 is deferred.
- ~~Owner decision: headed vs. dry-run-only~~ — superseded by deferring tier 3 outright.
- ~~Headed-mode wiring / full three-tier e2e / closing #417~~ — depends on all of the above.

## Doc-impact audit (checked against current file content, not assumed)

| Doc | Update | What |
|---|---|---|
| `CHANGELOG.md` (scriv) | item 3 only | Behaviour-changing → `make changelog_new` fragment. Item 1 is pure docs, exempt. Items 2/4/5/8 deferred with their tiers. |
| `README.md` | yes, narrower | §How: one sentence naming `open-offers` only (not 3 subcommands). Constraints line: no change needed — tier 1 has no bearing on the automated-submission boundary. |
| `CONTRIBUTING.md` | yes, narrower | §CLI subcommands table: 1 new row (`open-offers`). No `candidate`/`locate-fields`/`fill-offer` rows while deferred. |
| `docs/architecture.md` | yes, narrower | §User flow mermaid: tier 1 as an optional assist step between GATE 4 and manual submit (drop the tier 2/3 framing). §Repo structure: add `open_offers.py` only. §Built vs designed: one bullet once item 3 ships. No `CandidateProfile` data-contract row while deferred. |
| `docs/roadmap.md` | yes | "Arc-012 (plan 012, tier 1 only)" under **Next**/**Shipped**; tiers 2/3 + items 9–10 → **Later**, with the bot-detection/headed-browser reasoning from "Scope change" above. |
| `docs/userstory.md` | yes, narrower | New **US9** — tier 1 auto-open only (drop the tier 2/3 framing that was planned). |
| `docs/quickstart.md` | no | Was for `candidate.json` — deferred with tier 3. |
| ADRs | no new ADR | Unchanged. |

## Issues

- **#417** stays open, **scoped down to tier 1** for now; comment progress per merged PR; record
  both the CLI-only decision and the tier-2/3 deferral there (already done, see below). Do not
  close #417 on tier 1 alone — it still describes the fuller three-tier feature, now partially
  deferred rather than complete.
- No new follow-on issues filed for tiers 2/3, items 9, or 10 — #417 itself, plus this plan's
  "Scope change" section and remaining-work table, are the tracking record; a fresh design (not
  routing tier 2/3 through an automated headless session) would need its own plan before any of
  this reopens.
- Checked for overlap with existing open issues (`gh issue list --search "prefill OR autofill OR
  browser OR apply-url"`): only #417 is relevant; #365/#366 (pack-drift) and #341 (polyfetch-scrape
  docs publish) are unrelated.

## Remaining-work table (exactly one; source of truth for what's open)

| # | Item | Gate | Done-when |
|---|---|---|---|
| 1 | This plan + handoff + `research.md` re-verification fix | agent | **Shipped** — PR #420 merged |
| 2 | `config/candidate.json` scaffold | owner (deferred) | Its only consumer (tier 3) is deferred (see "Scope change") — not built |
| 3 | Tier 1 — `open-offers` CLI | agent | **Shipped** — PR #421 merged; `selected_urls()` unit-tested; PR notes the `webbrowser` deviation + untestable-headless caveat |
| 4 | Tier 2 — `locate-fields` CLI | owner (deferred) | Headless page-interaction carries bot-detection/ban risk even read-only; needs a fresh design or an explicit owner risk call before this reopens |
| 5 | Tier 3 dry-run — `fill-offer` CLI | owner (deferred) | Same as item 4, plus never resolved item 7 |
| 6 | Pre-staged `polyfetch-scrape` diff (`headless` param) | owner (deferred) | Moot while tier 3 is deferred; not drafted |
| 7 | Owner decision: headed vs. dry-run-only | owner (deferred) | Superseded — tier 3 itself is deferred, not just this sub-decision |
| 8 | Wire tier-3 headed mode | owner (deferred) | Depends on 5/6/7, all deferred |
| 9 | File-upload fields (`set_input_files`) | owner (deferred) | Moot while tier 3 is deferred |
| 10 | Custom per-offer Q&A auto-fill | owner (deferred) | Moot while tier 2/3 are deferred |

## Testing

- **Unit (TDD, `make check`):** the selection→URL join (tier 1) as a pure function. That's the
  only unit-testable surface remaining in this arc's active scope.
- No e2e in this arc's active scope — the local-fixture-forms e2e plan (plain + controlled-input,
  served on `localhost` via the polyfetch venv-borrow, the devcontainer Playwright-cache `mkdir -p`
  gotcha) was for tiers 2/3 and is deferred with them.

## Git workflow

New branch per topic (one per numbered Phase-A item); commits by topic; push, PR, squash-merge
only on green; delete both remote and local branch after merge. Subagents doing implementation
work use a git worktree (`isolation: "worktree"`), one per topic branch.
