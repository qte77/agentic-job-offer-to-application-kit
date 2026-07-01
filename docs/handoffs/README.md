# Handoffs

A **handoff** (`NNN-slug.md`) is the "resume here" entry doc for a work session — read it first. Its
matching plan (`docs/plans/NNN-slug.md`) holds the detailed spec. Split of concern: the handoff is
*pointer + current state*; the plan is *intent + design*.

## Structure

Sections shared by every handoff: **State** (branch/sync) · **Done** · **Resume here (in order)** ·
**Per-slice recipe** · **Gotchas** · **Touch points (current state)**.

## The Touch points rule

Every handoff carries a `## Touch points (current state)` table so a resuming agent verifies known
anchors instead of re-mapping the codebase:

- List **paths + the current signature/state + existence facts** (e.g. "`tests/test_chunk.py` does
  not exist yet").
- Keep *target* signatures and algorithm in the plan — don't duplicate them here (DRY).
- **No line numbers** — they drift, and stale info is worse than missing. Anchor on names, verify
  before editing.

See [`002-refresh-completion-lane-check.md`](002-refresh-completion-lane-check.md) for a worked example.
