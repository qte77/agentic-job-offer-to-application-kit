# Handoff 011 — Pack-coverage policy + output-eval + tailor-voice/mitigation + dashboard 404s

**CLOSED (2026-09-01).** All 4 slices + the retrofit + the coverage guarantee shipped. Nothing to
resume — see [`docs/plans/011-pack-coverage-and-output-eval.md`](../plans/011-pack-coverage-and-output-eval.md)
for the final `Status: SHIPPED` state, the per-slice PR numbers, and the closed-gate verification
checklist. This file is kept only as the historical pointer; there is no live "resume here" section.

## What shipped, for a reader who wasn't there

- **Slice A** (#408): voice + honesty baked into the tailor Workflow prompt; `must_haves` gained
  `mitigation`/`suggestion`; `gap_report` gained a "Top-3 prep actions" digest. Two live smoke runs
  were unknowingly executed against a stale session-start workflow snapshot before a third run
  against the actual edited file confirmed it working — see `AGENT_LEARNINGS.md` for the trap.
- **Slice C** (#409): `persist_offer`'s 4 sidecar checks refactored into a registry first
  (behaviour-identical), then `grounding.py` (CV-number grounding) and `coverage.honesty_warnings`
  added and wired in, calibrated against the real 34-pack corpus.
- **Slice B** (#410): `PackPolicy` + `pack_plan.py` (`select`/`missing`/`main`) + `ajoa-kit pack-plan`
  CLI + ADR-0005 — the config-driven selection policy and the missing-pack work-list reporter.
- **Slice D** (#411): `companies.json` always bundled (empty when no corpus) instead of the write
  being skipped; vendored-lib sourcemap comments stripped; `ui_e2e.py` now asserts zero unexpected
  network 404s and seeds a real-shaped `shortlist.json` locally.
- **Retrofit** (data op, 34 packs, not a PR): private "Gap Mitigation & Prep" appended to every
  existing pack's `gap-report.md`/`coverage-report.md`, hash-verified byte-identical elsewhere.
- **Coverage gate closed**: the 4 score-5 offers `pack-plan` found missing a pack were tailored and
  persisted through the new prompt; `pack-plan --min-score 5 --json` now reports `missing: []`.

## Loose ends outside this plan's scope

- FR issues #389 (`evidence-guard`), #390 (`apply-kit`), #393 (deferred-BAML spike) remain open —
  they were never in plan 011's scope and are their own future arcs.
- Issue #388 (a pre-existing, unrelated "cut release v0.9.0" tracker) is still open, blocked on a
  known broken reusable bump workflow (`qte77/.github#41`) — a maintainer timing decision, not
  something this arc's work should have triggered unilaterally.
