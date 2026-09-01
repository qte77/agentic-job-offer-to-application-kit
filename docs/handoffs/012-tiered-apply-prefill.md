# Handoff 012 — Tiered auto-open + browser prefill for application URLs (#417)

**CLOSED, SCOPE REDUCED (2026-09-01).** This arc's active work is done — see
[`docs/plans/012-tiered-apply-prefill.md`](../plans/012-tiered-apply-prefill.md) for the final
`Status` line, the "Scope change" section (why tiers 2/3 were deferred), and the remaining-work
table. This file is kept as the historical pointer; there is no live "resume here" section.
**Do not resume tiers 2/3 from this file** — re-opening them needs a fresh design, not a
continuation of what's below (which describes the original, since-superseded full-scope plan).

## What shipped, for a reader who wasn't there

- **#420** — plan 012 + this handoff + a `docs/research.md` fix: re-verified all 8 primary sources
  in §Delivery against their live current text (all still hold); fixed two stale doc facts
  (Greenhouse docs-URL redirect, Workable's application-question schema upgraded from
  "unconfirmed" to "confirmed employer-key-gated"). Also ratified the issue's open "CLI vs
  UI-triggered" question as **CLI-only** (`ui/` is fully static, no backend precedent anywhere,
  and `render_session` is headless regardless so a UI button couldn't show a human anything a CLI
  run doesn't already).
- **#421** — tier 1, `ajoa-kit open-offers`: reuses `pack_plan.select()`/`PackPolicy` for
  selection, reads `.url` off the in-memory `ScoredItem`s (since `pack-plan.json` drops that
  field), and opens each via stdlib `webbrowser.open()` — deliberately **not** `render_session`,
  which is hardcoded headless and would show the human nothing. `selected_urls()` is unit-tested;
  `webbrowser.open` itself is untested (no display in this devcontainer).

## Why tiers 2 and 3 were deferred (the scope change)

After #420/#421 shipped, the owner asked how tier 1 actually delivers a page to a human given
`render_session`'s headless design. Answering that surfaced a problem beyond tier 1: tiers 2
(locate/highlight fields) and 3 (fill fields) both *do* need `render_session` to interact with the
page, and a stealth-Patchright headless browser navigating/manipulating a real ATS form's DOM —
even read-only field-location, before any fill — is itself a form of automated access carrying a
real bot-detection / account-flagging risk to the candidate. That risk, compounded with tier 3's
Phase B never having gotten owner sign-off on a headed-browser `polyfetch-scrape` change (so a
human couldn't even watch/submit from the session that filled it), led the owner to defer both
outright rather than build them. `config/candidate.json` (item 2, tier 3's only consumer) and the
pre-staged `polyfetch-scrape` diff (item 6) were never built as a result — the in-flight subagent
building item 2 was stopped mid-implementation with nothing pushed and no PR opened; its worktree
and local branch were removed.

## If tiers 2/3 are ever revisited

Start from `docs/plans/012-tiered-apply-prefill.md`'s "Scope change" section and its Deferred
list — those preserve the original design (source map, invariants, the `press_sequentially`-not-
`fill()` gotcha, the Greenhouse-schema-diff idea) as a record, not a spec to resume verbatim. A
fresh design needs to either avoid routing tier 2/3 page-interaction through an automated headless
session, or get an explicit, informed owner call that the bot-detection/ban risk is acceptable —
neither exists today.
