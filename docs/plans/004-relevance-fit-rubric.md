# Plan 004 — #271 relevance fit rubric (LEAN): explainable rationale + deadline & deal-breaker flags

**Status: SHIPPED** — implemented in #271 (#280). Approved 2026-07-08 (lean); scope expanded 2026-07-09
to type `deadline`/`deal_breaker` on `ScoredItem` + carry `ScoredItem` end-to-end (ADR-0003). Handoff:
[docs/handoffs/004-relevance-fit-rubric.md](../handoffs/004-relevance-fit-rubric.md). A cloud
(Ultraplan) session may further refine this — if so, reconcile against the owner-approved version
before executing; otherwise this lean plan is canonical.

## Context

The relevance screen (`cc-workflow-relevance.js`) emits one opaque `score` + a free-text `rationale`
per JD. At GATE 2 (shortlist review) a human can't see *why* a JD scored well, nor spot a hard
mismatch or a looming application deadline at a glance. Inspired by
[MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) and our own
`../agentic-market-research-to-gtm` `results-validator` (criteria-driven scoring).

**Scope reconciled to LEAN (KISS/YAGNI):** enrich the `rationale` to name the fit dimensions in prose,
and add only the two **human-actionable** structured fields — `deadline` and `deal_breaker`. **Dropped
from scope:** the 5 numeric sub-scores (display-only until a consumer/tuning exists → YAGNI) and the
config-driven tunability. Purely **additive annotations** — the `score`, verdict, and drop behaviour
are **unchanged**. `ScoredItem` needs **no change** (`extra="allow"`, #197, round-trips the two fields).

## Changes (L3 workflow glue + L2 render + typed `ScoredItem` pipeline)

1. **`.claude/workflows/cc-workflow-relevance.js`** (glue — verified live, no JS tests):
   - `RESULT.items.properties` (schema at lines 57–81): add `deadline: { type: 'string' }` and
     `deal_breaker: { type: 'string' }` — **optional** (NOT added to `required`; "" = none).
   - `gatePrompt` scoring instruction (line 95): (a) instruct the `rationale` to explicitly name the
     fit across skill / experience / culture-location / progression / motivation (prose, not numbers);
     (b) set `deadline` to the JD's stated application deadline if present (else ""); (c) set
     `deal_breaker` to a one-phrase hard concern the human should weigh (else ""). Leave `score`,
     `verdict`, and the DROP rules (lines 91–93) untouched.
2. **`src/ajoa_kit/persist_scored.py::write_lane`** (lines 67–84; module logic → TDD): surface the two
   fields in `shortlist.md` (JSON already carries them via `extra="allow"`):
   - append to the `tag`: `· due <deadline>` and `· deal-breaker` when set;
   - add a `- deal-breaker: <text>` bullet when set. Keep the function ≤10 complexity (extract a tiny
     `_flags(item) -> str` helper if needed).
3. **`src/ajoa_kit/models.py::ScoredItem`** — add typed `deadline`/`deal_breaker` (`str = ""`); the
   persist/merge/refresh pipeline now carries `ScoredItem` end-to-end (attribute access, `model_dump`
   only at the JSON write), with a shared `load_shortlist` validating on-disk re-reads. `extra="allow"`
   stays (#197). Pulls forward part of ADR-0003 backlog item 2.

## Source map (verified via Explore 2026-07-08 — re-verify before editing)

- **`.claude/workflows/cc-workflow-relevance.js`**: `RESULT` schema **57–81** (`items.properties`:
  `id/title/company/best_lane`(enum `LANES`)`/score`(int)`/verdict`(enum `shortlist|maybe`)`/rationale/url`;
  `required: id,best_lane,score,verdict,rationale`; sibling `dropped_count`/`dropped_reason_sample`).
  `gatePrompt` **83–96** (evidence-library injection **84–86**; scoring instruction **95** ← edit;
  hardcoded DROP rules **91–93**). `LANES` from `cfg.lanes` else fallback **49–51**. Config via `args`
  **34** (`cfg = JSON.parse(args)`). Aggregation **102–122** (`parallel(... {schema: RESULT})`,
  `.filter(Boolean)`, flatMap `relevant`, sort by `score`; returns
  `{kept,dropped,byLane,batchesProcessed,relevant}`; **no file writes** — persisted by `ajoa-kit persist`).
- **`src/ajoa_kit/models.py::ScoredItem`** **34–59**: `model_config = ConfigDict(extra="allow")` (#197);
  fields `id/title/company/best_lane/score(int|float|None)/verdict/rationale/url/stale/last_checked`;
  no validators beyond `score` coercion.
- **`src/ajoa_kit/persist_scored.py`**: `load_result` **30–43** (regex-unwraps `{"result": …}`);
  `parse_relevant` **46–64** (`ScoredItem.model_validate(raw).model_dump()`; `ValidationError`→drop+count);
  `write_lane` **67–84** (writes `shortlist.json` full dump + `shortlist.md`; the md uses an **explicit**
  `tag`/bullet template — `tag = f"{score}/{verdict}" + (" · stale" …)`, bullets = title@company / url /
  rationale ← edit here); `main` **141–177** (validates `best_lane` vs `load_lanes`).
- **Tests `tests/test_persist_scored.py`**: `_item(jid, lane, score, **kw)` (kw injects extra fields),
  `_run(tmp_path, monkeypatch, result, merge=)` (sets `AJOA_RESULTS_DIR`, writes `result.json`, calls
  `persist_scored.main(src=…)`); `test_unknown_result_field_survives_round_trip` **67–78** = the exact
  round-trip template to extend.
- **Deferred phase-2 refs** (config-tunability): `load_lanes` (`ingest.py` **38–70**,
  file-overrides-`DEFAULT_LANES`); `sources.load_sources` (**317–336**, user-file-else-tracked-default);
  `AppSettings.config_dir` (`settings.py` **35–38**, `AJOA_` prefix); `--json` emit `__main__.py::_lanes`
  **73–86** + `style.py::main`; sibling `config/validation_criteria.md` (dimensions/thresholds/
  hard-stop-vs-warning) as the criteria-file template.

## TDD sequence (strict; non-trivial module logic only)

1. **`tests/test_persist_scored.py`** red→green (extend `_item`/`_run`):
   (a) round-trip — `_item(..., deadline="2026-07-31", deal_breaker="on-site NYC only")` → assert both
   survive into `jobs-scored.json` **and** `results/<lane>/shortlist.json`;
   (b) render — after persist, read `shortlist.md` and assert `due 2026-07-31` + `deal-breaker` appear
   in the tag and the `- deal-breaker:` bullet renders (red until `write_lane` updated).
2. JS schema/prompt = glue (no JS harness in repo) — verified live + `RESULT` enforces shape at runtime.
3. Optional: extend the offline-e2e (#165) canned relevance result with the two fields to exercise the
   deterministic persist path without an LLM.

## Doc / switch / issue impact (audit)

- **Switches:** **none** — the rubric lives in the workflow; no new URL / env / CLI. Nothing to document.
- **CHANGELOG:** `Changed` fragment (relevance output carries explainable rationale + `deadline` /
  `deal_breaker`, surfaced in `shortlist.md`).
- **architecture.md:** one-line note on the Shortlist contract row (relevance RESULT gains `deadline` +
  `deal_breaker`, riding via `ScoredItem extra="allow"`).
- **README / roadmap / userstory:** no change (internal enrichment; no new user step or headline).
- **Issues:** the implementation PR uses `Closes #271`. Deferred **numeric sub-scores + config-driven
  tunability** → follow-up on #271 (or split to a new issue). #272 (critique loop) unaffected.

## Security / lint / typing

No new secret/PII/external surface (relevance output already in git-ignored `results/`; the two fields
are model-generated annotations, never inputs to a fetch/exec — no injection). Gate: `ruff` +
`ruff format` + `pyright` + `complexipy` (`write_lane` ≤10) + offline `pytest`; `markdownlint-cli2` on
changed md; security read per diff.

## Execution + verification

New branch `feat/relevance-rubric` off `main` → commit by topic (tests · persist render · JS workflow ·
docs+fragment) → mutators then **gate LAST** → PR `Closes #271` → `gh pr checks --watch` → squash-merge
on green → prune branch. Verify: `make check` green (round-trip + render); optionally drive one real
`cc-workflow-relevance.js` run via the Workflow tool to confirm the fields populate + render.

## Out of scope (deferred — follow-up on #271 or new issue)

Numeric per-dimension sub-scores; config-driven criteria (`config/relevance-criteria.json` +
`DEFAULT_CRITERIA` + `load_criteria` + pydantic model + `ajoa-kit criteria --json` → `args.criteria`,
per the `validation_criteria.md` pattern) for tunable weights / verdict thresholds / deal-breaker rules.
