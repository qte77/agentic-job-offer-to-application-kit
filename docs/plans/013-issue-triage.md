# Plan 013 — Triage 13 open issues (#414, #393, #390, #389, #370, #366, #365, #346, #344, #342, #341, #332, #331)

**Status: SHIPPED (2026-09-01).**

## Context

A batch of 13 open issues — several weeks old, zero comments — needed triage: which are
stale/superseded/duplicate vs. still genuinely open, and which current shipped code already quietly
resolves. Two research passes read every issue body in full and cross-checked each against the
*current* source (not just the issue text, which can predate later shipped work).

**Headline finding: none of the 13 were stale, done, or duplicates.** This repo's tracker was
already well kept — every issue still describes a real gap. So this plan is not a backlog cleanup;
it's (a) a comment per issue recording what the research found, so the next reader doesn't
re-derive it, (b) two things that came back genuinely wrong (a stale label on #341, a missing
roadmap entry for #269), and (c) the one real decision that needed the owner, not an agent (#332).

**This plan does not implement any of the 13 issues' underlying feature work** (drift checks, the
`make doctor` preflight, the resume guard, the hand-off automation, etc.) — triage only. Each stays
exactly as open/actionable as the table below says.

## Findings + source map (per issue — what a future session implementing one needs, so it doesn't re-map)

| # | What it asks | Current-code finding | Touch points for future implementation |
|---|---|---|---|
| #365 | `persist-offer` packs keep no source (no `result.json`, no `generated_from` stamp) | Confirmed absent. Prerequisite for #366. | `src/ajoa_kit/persist_offer.py` `write_pack()` (writes the 5 artifacts + sidecars + `meta.json:{id,slug}` — no source retention today) |
| #366 | Drift check: re-render a pack from its source, diff against disk | No such logic exists; blocked on #365 | Same file, `_load_offer_index()`; needs #365's source-retention shipped first |
| #414 | Detect `evidence-library.json` drift (`gapNarrative` and other fields reword across rebuilds) | Confirmed absent; distinct from #365/#366 (library-vs-library, not tailor-result-vs-pack) | `cc-workflow-evidence-library.js`'s `LIB` JSON-Schema (no version/hash field); `src/ajoa_kit/grounding.py` (one-directional CV-vs-library only, not library-vs-library) |
| #390 | Package the pipeline as a distributable "apply-kit" plugin | No in-repo plugin-packaging mechanism found. **Unresolved flag**: this session's own available-skills listing carries `evidence-library`/`relevance`/`tailor-offer` skills whose descriptions verbatim-match this repo's three Workflow scripts — unconfirmed whether something already skill-wraps this pipeline outside this repo's tree | `docs/decisions/0001-backend-cli-ui-separation.md` (four-layer model — a plugin would be a distribution channel for L3, orthogonal to the ADR, not conflicting) |
| #389 | Extract an evidence-grounding gate as a standalone plugin | `grounding.py`/`coverage.honesty_warnings` already pure, cheap to lift; the keep/downgrade/drop pass is an inline prompt in the evidence-library Workflow script, needs generalizing | `src/ajoa_kit/grounding.py`, `src/ajoa_kit/coverage.py` (`honesty_warnings`), `.claude/workflows/cc-workflow-evidence-library.js` (the "Mine & verify" phase's inline prompt) |
| #393 | Spike: evaluate BAML at the "portable-runner milestone" | Self-deferred; "portable-runner milestone" is nowhere in `docs/roadmap.md` — purely aspirational, independent of #389/#390 | — (no code exists to touch; gated on a milestone that doesn't exist yet) |
| #341 | Docs: publish polyfetch-scrape source/setup + `make doctor` preflight | Docs half fully shipped (`docs/quickstart.md`, `CONTRIBUTING.md`, `AGENTS.md` all carry it). `make doctor` half fully unbuilt | `Makefile` (no `doctor` target); upstream primitive is `polyfetch doctor [--fix]` (`../polyfetch-scrape/USING.md`) — must verify the actual browser binary on disk, not trust `patchright install`'s exit code alone (owner's 2026-08-09 comment on the issue) |
| #370 | `location_flagged_count` computed but never surfaced | Confirmed, and wider than filed: the JS Workflow script drops the count before persist ever sees it. A parallel `tenure_flagged_count` (shipped after this issue, commit b964578) has the identical bug | `.claude/workflows/cc-workflow-relevance.js` (`return { kept, dropped, byLane, batchesProcessed, relevant }` — never aggregates either flagged count); `src/ajoa_kit/persist_scored.py` (summary line never mentions it either) |
| #346 | Post-merge refresh hint + corpus-snapshot staleness stamps | Both halves confirmed unshipped; distinct concern from #365/#366 | `src/ajoa_kit/ingest.py` (`_update_corpus`, no refresh hint); `src/ajoa_kit/persist_offer.py` (`meta.json` has no snapshot-date field) |
| #344 | Guard resume against a recomputed delta; document resume semantics | Doc half shipped (commit a111b18, the `⚠️ RESUME:` header). Guard half open — not a drop-in, the script has no filesystem access, needs a design call on where a guard lives | `.claude/workflows/cc-workflow-relevance.js` (header comment already there); candidate: a run-id stamp in `results/batches/manifest.json` |
| #342 | Automate the Workflow-to-persist hand-off | Confirmed fully manual (`docs/quickstart.md` says so outright); `pack-plan`/ADR-0005 automates *which* offer needs a pack, not the hand-off itself | `Makefile` (no `make relevance` helper, no `persist --from-last-run`); `docs/quickstart.md` Stage 2/3 sequences |
| #332 | Publish a per-company hiring view on gh-pages? (needs ADR) | ADR-0004 already bars publishing any discovery output, predating this issue by 3 days | **Resolved this plan** — owner affirmed the existing boundary; closed, no future implementation needed |
| #331 | Discovery phase-2: HN "Who is hiring?" Algolia API | ADR-0004 already records this as the sole phase-2 lead — bookkeeping, not new work. Its stated gate ("only if phase-1 proves out") is stale — a second discovery source (startups.gallery) already shipped since | `docs/decisions/0004-discovery-source-tiers.md` (Consequences section); real remaining blocker is HN's free-text-extraction cost, not a source-count gate |
| #269 | Optional `posted_at` backfill trend series | Already confirmed the one legitimately deferred item; had no `docs/roadmap.md` **Later** entry despite being open+deferred | `docs/roadmap.md` §Later (this plan adds the missing entry) |

## Execution

- One `gh issue comment` per issue above (except #332, resolved by closing instead), each citing
  the specific finding — not generic "still relevant" filler.
- `gh issue edit 341` — drop the `documentation` and `good first issue` labels (verified exact
  label names via `gh issue view 341 --json labels` before editing); remaining work is a real
  Makefile feature with a security-relevant gotcha, not a docs edit.
- `gh issue close 332` with a comment affirming ADR-0004's existing boundary — owner's explicit
  call (AskUserQuestion), not a default.
- `docs/roadmap.md`: one line added under **Later** for #269, matching the existing entries' style.

## Verification

- `gh issue view <n>` after each comment to confirm it posted; `gh issue view 341 --json labels`
  after the relabel; `gh issue view 332 --json state` to confirm closed.
- `markdownlint-cli2 --no-globs docs/roadmap.md` + `lychee docs/roadmap.md` before pushing.
- Final `gh issue list --state open` sweep — confirm all 13 show the expected state (12 open with a
  new comment, #332 closed), nothing else accidentally touched.

## Handoff

The session handoff for this arc, merged in from the former `docs/handoffs/` folder (one file per arc). Historical: this arc is closed.

**CLOSED (2026-09-01).** Nothing to resume — see
[`docs/plans/013-issue-triage.md`](013-issue-triage.md) for the full per-issue findings
table and source map. This file is kept only as the historical pointer.

### What shipped, for a reader who wasn't there

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

### If picking up any of the 13 issues next

Don't re-research from scratch — plan 013's table has the current-code finding and file-level touch
points for each. Sequencing to respect: `#366` needs `#365` shipped first (source retention before
drift-checking against it); `#390` needs `#389` shipped first (plugin extraction before packaging).
`#390` also carries one unresolved flag worth checking with the owner before scoping real work: this
session's own available-skills listing showed skill descriptions verbatim-matching this repo's three
Workflow scripts, suggesting something may already skill-wrap this pipeline outside this repo's
tree — location and scope unconfirmed.

### Touch points (current state)

| Path | State |
|---|---|
| `docs/roadmap.md` | Exists; this session added one **Later** line for #269 — no other structural change |
| `src/ajoa_kit/persist_offer.py` | Exists; `write_pack()` still writes no source/provenance (relevant to #365/#366) |
| `.claude/workflows/cc-workflow-relevance.js` | Exists; still never aggregates `location_flagged_count`/`tenure_flagged_count` into its return object (relevant to #370); already carries the `⚠️ RESUME:` header comment (relevant to #344's doc half) |
| `Makefile` | Exists; still no `doctor` target (relevant to #341) and no `relevance`/hand-off-automation targets (relevant to #342) |
| `src/ajoa_kit/grounding.py`, `src/ajoa_kit/coverage.py` | Exist; already pure/cheap-to-extract (relevant to #389) |
| `docs/decisions/0004-discovery-source-tiers.md` | Exists; already documents the #331 phase-2 gate and the #332 publishing boundary — read before re-deriving either |
