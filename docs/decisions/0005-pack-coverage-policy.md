# ADR-0005 — Pack-coverage policy

**Status:** Accepted (2026-08-31)

**Relates to:** [ADR-0003](0003-data-contract-enforcement.md) (pydantic-at-the-boundary
convention `PackPolicy` follows; the "no shared `must_haves` model yet" backlog item this ADR
deliberately does not pick up); [plan 011](../plans/011-pack-coverage-and-output-eval.md) Slice B.

## Context

Pack generation is fully manual: a human picks one shortlist row and runs the tailor Workflow for
that single `offerId`. There is no selection logic and no coverage guarantee — nothing catches a
score-5 row that never got tailored, and nothing bounds how many packs a run produces. As the
shortlist corpus grows across lanes, "did every strong match get a pack" became a question a human
had to answer by memory.

## Decision

**A config-driven selection policy, plus a pure reconciler — no new orchestration engine.**

1. **`PackPolicy`** (`models.py`, pydantic, ADR-0003 home): `min_score`, `max_packs`, `lanes`,
   `per_company_cap`, `dedup`. All fields default to "select everything, no caps" except
   `min_score` (5) and `dedup` (`"role_x_company"`) — the policy is opinionated out of the box, not
   inert like `LocationPolicy`/`SeniorityPolicy`.
2. **`pack_plan.py`**: a pure decision core (`select`, `missing`) plus a thin `main` — mirrors the
   `refresh.py` split (pure reconciler + thin CLI entry) already established in this codebase.
   `select` filters (score, lane) → sorts (score descending, stable) → dedups (policy-gated) → caps
   (per-company, then total). `missing` diffs the selected targets against
   `persist_offer._load_offer_index`.
3. **Config + CLI precedence**: `config/pack-policy.json` (absent → `PackPolicy()` defaults, same
   inert-file precedent as `config/lanes.json`) is the base; `ajoa-kit pack-plan`'s
   `--min-score`/`--max-packs`/`--lanes` flags override it per invocation. CLI wins because a
   one-off run ("just the ml lane this time") should never require editing a file.
4. **The coverage guarantee is external to this module.** `pack-plan` only *reports* the missing-id
   work list (`results/pack-plan.json` = `[{offer_id, lane, score}]`) — it does not itself invoke
   the tailor Workflow (an LLM pipeline, not a CLI verb) or `persist-offer`. The guarantee is an
   orchestrator loop: `pack-plan` → tailor Workflow per missing id → `persist-offer` → re-run
   `pack-plan` until `missing == []`. Idempotent by construction: a target with a pack on disk is
   never in `missing` again, so re-running the loop after a partial run only tailors what's left.
5. **No pydantic model for the pack itself** (carried over from plan 007's decision, reaffirmed
   here). `pack_plan` only reads `ScoredItem` (already typed, ADR-0003) and the untyped offer-index
   dict `persist_offer` already produces — it never touches `must_haves` or the pack JSON. Typing
   the pack stays ADR-0003's own backlog item, not something this policy work should absorb as a
   side effect.

## Consequences

- One new config surface (`config/pack-policy.json`, git-ignored like every other `config/*.json`
  policy file) and one new CLI verb (`ajoa-kit pack-plan`).
- `pack-plan` is read-only with respect to the shortlist/offer corpus — it writes only
  `results/pack-plan.json`, a disposable work list, never a shortlist or pack file. Safe to run
  repeatedly, including against a corpus with no policy file at all.
- The dedup/per-company-cap knobs assume `title`/`company` are populated on `ScoredItem` — rows
  missing either simply never collide, which is the safe direction (never drops a row that might
  be genuinely unique).
- **Testability:** `select`/`missing`/`load_policy` are pure and unit-tested
  (`tests/test_pack_plan.py`); `main`/the CLI handler are thin orchestration and untested, per the
  project's "non-trivial tests only" convention (mirrors `refresh.py`'s split).

## Out of scope (own follow-on slices)

- The orchestrator loop itself (pack-plan → tailor → persist-offer → re-check) — a usage pattern
  documented in this ADR and the plan, not new code; a future slice could script it if manual
  looping proves tedious.
- A `dedup` strategy beyond `"role_x_company"` — the field is a string for forward compatibility,
  but only one strategy exists today (YAGNI; add a second when a real need appears).
- Typing the pack/`must_haves` shape — ADR-0003's own backlog, untouched here.

## References

- [ADR-0003](0003-data-contract-enforcement.md) — pydantic-at-the-boundary convention.
- [plan 011](../plans/011-pack-coverage-and-output-eval.md) — Slice B source map + verification.
- `src/ajoa_kit/refresh.py` — the pure-reconciler + thin-`main` shape this mirrors.
