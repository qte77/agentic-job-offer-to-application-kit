# Handoff 013 — Triage 13 open issues

**CLOSED (2026-09-01).** Nothing to resume — see
[`docs/plans/013-issue-triage.md`](../plans/013-issue-triage.md) for the full per-issue findings
table and source map. This file is kept only as the historical pointer.

## What shipped, for a reader who wasn't there

- Read all 13 issues in full (two parallel research passes) and cross-checked each against current
  shipped code, not just the issue text. **None were stale, done, or duplicates** — every one still
  describes a real gap; this was triage/documentation, not a backlog cleanup.
- Left each issue a comment recording the specific finding (what's already shipped vs. still open,
  any scope corrections, any cross-issue dependency confirmed or ruled out) — see plan 013's table
  for exactly what each comment said.
- `#341` relabeled — dropped `documentation`/`good first issue`; its docs half is fully shipped, and
  the remaining `make doctor` preflight work is a real Makefile feature with a security-relevant
  gotcha (don't trust a sandboxed `patchright install`'s exit code alone), not a docs task.
- `#332` closed, with the owner's explicit affirmation that ADR-0004's existing "never publish
  discovery output" boundary already answers its question — not a default, an explicit
  AskUserQuestion call.
- `docs/roadmap.md` §Later gained a one-line entry for `#269` (open, deliberately deferred, but had
  no roadmap presence despite that).

## If picking up any of the 13 issues next

Don't re-research from scratch — plan 013's table has the current-code finding and file-level touch
points for each. Sequencing to respect: `#366` needs `#365` shipped first (source retention before
drift-checking against it); `#390` needs `#389` shipped first (plugin extraction before packaging).
`#390` also carries one unresolved flag worth checking with the owner before scoping real work: this
session's own available-skills listing showed skill descriptions verbatim-matching this repo's three
Workflow scripts, suggesting something may already skill-wrap this pipeline outside this repo's
tree — location and scope unconfirmed.

## Touch points (current state)

| Path | State |
|---|---|
| `docs/roadmap.md` | Exists; this session added one **Later** line for #269 — no other structural change |
| `src/ajoa_kit/persist_offer.py` | Exists; `write_pack()` still writes no source/provenance (relevant to #365/#366) |
| `.claude/workflows/cc-workflow-relevance.js` | Exists; still never aggregates `location_flagged_count`/`tenure_flagged_count` into its return object (relevant to #370); already carries the `⚠️ RESUME:` header comment (relevant to #344's doc half) |
| `Makefile` | Exists; still no `doctor` target (relevant to #341) and no `relevance`/hand-off-automation targets (relevant to #342) |
| `src/ajoa_kit/grounding.py`, `src/ajoa_kit/coverage.py` | Exist; already pure/cheap-to-extract (relevant to #389) |
| `docs/decisions/0004-discovery-source-tiers.md` | Exists; already documents the #331 phase-2 gate and the #332 publishing boundary — read before re-deriving either |
