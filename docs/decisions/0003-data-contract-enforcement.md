# ADR-0003 — Data-contract enforcement across layers

**Status:** Accepted (2026-06-23)

**Relates to:** [ADR-0001](0001-backend-cli-ui-separation.md) (the four-layer split + one-way imports
whose boundaries this ADR types); the parse boundaries in
[architecture.md §Boundary failure policy](../architecture.md#boundary-failure-policy); the kit's
"pydantic for structured config/models" rule (AGENTS.md). Issue #158.

## Context

Data crosses the four layers (ADR-0001) mostly as **raw dicts / `json.loads` + `.get()`**, with
typed contracts only at a few spots. A map of the current surfaces:

### Typed today

- `AppSettings` (`settings.py`) — pydantic-settings; env-overridable path config.
- `WeekCounts` / `DayCounts` / `MonthCounts` (`models.py`) — pydantic, but validated on the
  **write** side only; the read side uses raw `json.loads(...).get(...)`.
- JS inline **JSON Schema** objects in `cc-workflow-*.js` (`RESULT`, `LIB`, the tailor `matchSchema`/
  `strField`) — validate each `agent()` **output** at the moment it is produced.

### Untyped (raw dict; .get() with fallbacks)

- `record()` (`ingest.py`) → `jobs-raw.json` — the canonical JD shape is a plain dict and
  `base.update(kw)` accepts anything. Highest-volume boundary; every downstream stage depends on it.
- `jobs-raw.json` read by `chunk` / `trend_snapshot`; `results/batches/manifest.json` (hand-built;
  `batchCount` passed by hand).
- The relevance result entering Python (`persist_scored.load_result` / `write_shortlists`) — the JS
  `RESULT` guarantee is **lost the moment the file is read back** in Python (largely resolved — items
  are typed `ScoredItem` parse-on-read through persist + merge/refresh, #271; a `ScoredResult`
  envelope for the top-level result remains).
- The tailor pack entering Python (`persist_offer`) — hand-rolled string-presence checks in
  `render()`; `must_haves` is JS-schema'd but Python-untyped (`coverage.py` uses `.get()`).
- `config/{seed,keywords,style}.json` — raw `json.loads` + `.get()`; `style` even used a
  `@dataclass`, not pydantic (since resolved — `models.StyleBrief` is pydantic, #257).
- **Lane keys live in three places** (`cc-workflow-evidence-library.js` objects,
  `cc-workflow-relevance.js` keys, `persist_scored.py` `best_lane` directory) with no shared
  contract; Python never checks `best_lane` against a canonical set.

### Constraints

- **pydantic is the mandated tool** for structured config/models (AGENTS.md; ADR-0001 Consequences).
- The L3 `.js` workflows run in the Claude Code Workflow **sandbox** — no filesystem, no npm
  `import` at runtime — so a TS/JS validation library (Zod/Valibot/convict) **cannot be imported**
  into them. Their only in-script validation primitive is inline **JSON Schema** (already in use).
- ADR-0001 one-way imports: L1 is the shared library, so contracts belong in L1 and are consumed
  upward.

## Decision

A direction, not an implementation — each item below is a future slice (ranked in Consequences):

1. **Python (L1): pydantic models at every cross-layer boundary, validated on read.** Define L1
   models for the JD record, the relevance result, the tailor pack + `must_haves`, and the
   config-file entries; parse-on-read when a JSON artifact re-enters Python (not just on write).
   Extends the existing convention (`AppSettings`, `WeekCounts`).
2. **JS (L3): keep inline JSON Schema for agent outputs; add light `args` validation.** No new
   dependency — JSON Schema is what the sandbox supports. Optionally give each workflow a small
   schema check on its `args` (today `args` is `JSON.parse`d but unvalidated).
3. **Cross-language: JSON Schema as the lingua franca; one shared config for genuinely shared data.**
   Where the same shape crosses Python↔JS (notably the lanes), make a single source — e.g.
   `config/lanes.json` validated by a pydantic model on the Python side and passed to the workflows
   via `args.lanes` (`evidence-library.js` already reads `cfg.lanes`; `relevance.js` would derive its
   keys from it). Removes the 3-place lane duplication at runtime without coupling the sandboxed
   scripts.
4. **Rejected — a JS/TS validation library (Zod/Valibot/convict).** It cannot run inside the
   sandboxed workflow scripts, and adding a Node toolchain (`package.json`/`node_modules`/build) to a
   Python + vanilla-JS repo is disproportionate (YAGNI). Validation in any parent orchestrator stays
   pydantic (Python).

## Consequences

- **Prioritized backlog** (each a future slice; file as an issue when picked up), highest ROI first:
  1. **`JobRecord` pydantic model** for `record()` / `jobs-raw.json` — highest volume; `record()`
     returns it (`.model_dump()` to serialize); `chunk` + `trend_snapshot` parse-on-read.
  2. **Re-validate the relevance `RESULT`** in `persist_scored.load_result` (a `ScoredResult` /
     `ScoredItem` model) so the JS guarantee survives the file hop; also check `best_lane` ∈ lanes.
     **Largely shipped:** items are typed `ScoredItem` parse-on-read (#197) and carried end-to-end
     through persist + the merge/refresh re-reads (#271); the `best_lane` ∈ lanes check landed (#195).
     A `ScoredResult` wrapper for the top-level envelope (`dropped_count` etc.) remains.
  3. **A shared `must_haves` model** for the tailor result + `coverage.py` (today JS-schema'd,
     Python-untyped).
  4. **Config-entry models** for `seed` / `keywords` / `style` (the raw `.get()` loads). `style` is
     done — `models.StyleBrief` is pydantic (#257); `seed` / `keywords` parse-on-read remain.
  5. **Lanes single source** (`config/lanes.json` + pydantic + `args.lanes`) — resolves the 3-place
     duplication and the "configurable lanes" wording in `architecture.md`. **Shipped (#195).**
- No new runtime dependency (pydantic already present; JSON Schema is just data).
- Gives the "JD parse (per record) — wrap-continue, hardening tracked in issues" line in
  [architecture.md §Boundary failure policy](../architecture.md#boundary-failure-policy) a concrete
  typing plan.
- **Testability:** each model earns value-add round-trip / validation tests when its slice lands (per
  the TDD rule) — not before (YAGNI).

## Out of scope (own follow-on slices)

- Implementing any of the backlog models above.
- Non-contract hardening (robots/rate-limit enforcement, etc.).

## References

- [ADR-0001](0001-backend-cli-ui-separation.md) — four-layer split + one-way imports.
- [architecture.md §Boundary failure policy](../architecture.md#boundary-failure-policy) — the parse
  boundaries this ADR plans to type.
- Issue #158 — the research request this ADR answers.
