# Plan 011 — Pack-coverage policy + deterministic output-eval + tailor-voice/mitigation + dashboard 404s

## Context

Pack generation is **fully manual today** — a human picks one shortlist row and runs the tailor
Workflow for that single `offerId`; there is **no selection logic and no coverage guarantee** (no
`tailor-set` exists). This plan makes the pipeline **hands-off + self-verifying**:
a **config-driven pack policy** ("cover all score>=N, cap M, these lanes, one per company") + a
**deterministic coverage reconciler** that guarantees every selected JD gets a full pack; a
**deterministic output-eval layer** (grounding + honesty) so packs self-verify offline; the
**tailor prompt** updated to bake the agreed **synergy-forward / growth-as-intent voice** + a
**private mitigation/prep layer** (strengths outward, honest gap-closing private); a **hotspot
refactor** of `persist_offer.py` (churn 352 / dup 12 / `jd_truncation_warning` at the complexity-10
ceiling) that also becomes the DRY seam the new checks plug into; and the **dashboard console/network
404 cleanup** the e2e surfaced.

## Constraints
- **Strict TDD**: failing tests modelling desired behaviour first, then code to green.
- **Non-trivial tests only**: test pure modules (parsers/checkers/reconciler decision core); NOT thin
  CLI handlers, trivial getters, or the network/Workflow orchestrators.
- **Strict lint/typing/sec**: ruff (ANN/D-google/C90/TRY/S/B, line ≤100), pyright, complexipy ≤10,
  bandit-safe; pydantic models in `models.py` (ADR-0003). `make check` green each slice.
- **Voice/honesty invariant**: outward docs (CV/cover/match) = strengths-forward, no weakness content;
  mitigation/prep + eval findings are **private** (`gap-report.md`, sidecars) — never employer-facing.
- **No pydantic model for the pack itself** (plan 007) — pack stays schema-in-JS; new keys OPTIONAL.

## Source map (reuse, don't rebuild — verified 2026-08-22)

**Tailor Workflow** `.claude/workflows/cc-workflow-tailor-offer.js` — `meta` L39-49; args/inputs L52-79;
`SOURCES` grounding block L74-79; `matchSchema` (`must_haves:{requirement,covered,evidence,resources}`)
L90-118; CV agent (hard-codes ATS rules) L147-161; cover L162-173; gap L174-185; critique loop L188-248;
prefill L250-274; **return keys** `slug·lane·offer_id·match·must_haves·cv·cover_letter·gap_report·prefill_pack`
L277-287. Relevance RESULT (`score` int 0-5, `verdict`) `cc-workflow-relevance.js` L68-98.

**Selection inputs (greenfield — compose these):**
- `persist_scored.load_shortlist(path)` L67-74 → `list[ScoredItem]`; per-lane `results/<lane>/shortlist.json`.
- `ScoredItem` `models.py:115-145` (`score:int|float|None`, `extra="allow"`).
- `persist_offer._load_offer_index(results_dir)` L275-285 → {JD id → offer dir} via `offers/*/meta.json`.
- **Missing-pack set = ids in `load_shortlist(score>=N)` minus `_load_offer_index` keys.**
- Reconciler shape template: `refresh.py` (pure `is_delisted`/`classify`/`mark` L40-85 + thin `main`
  L126-160 + `--lane/--delete/--dry-run` `__main__.py:250-261`).

**Pack write** `persist_offer.py` — `safe_slug` L46-64; `write_pack` L180-256 (`ARTIFACTS` L35-41 = the 5
`.md`); optional **sidecars** (the extension idiom): `coverage-report.md` L207-210, `cv-ats-check.md`
L213-220, `cv-stuffing-check.md` L224-231, `jd-truncation-check.md` L236-242 (`jd_truncation_warning`
L98-141, **complexity 10**), `lane-grounding-check.md` L245-251 (`lane_angle_warning` L144-177 =
never-guess grounding template). `main` L328-348.

**Eval gates (pure siblings to mirror):** `ats_check.parse_safety_warnings` L34-54; `stuffing.stuffing_warnings`
L80-92; `coverage.coverage_summary(must_haves, gap_report)` L66-91 (`_row` L52-63). Tests:
`tests/test_ats_check.py`, `test_stuffing.py`, `test_coverage.py`, `test_persist_offer.py` (sidecar wiring).

**Config/CLI:** `AppSettings` `settings.py:17-46` (`AJOA_` env, `config_dir`/`results_dir`); loader idiom
`ingest.load_lanes` L55-72 / `load_manual_jds` L97-129 (absent-file-inert, malformed→loud); subcommand reg
`__main__.py` handler L54-58 + subparser L232-237 + dispatch L392-393; `--json` emitter precedent `_lanes`
L90-103. Models home `models.py` (ADR-0003).

**Dashboard:** `ui/src/companies.js` `loadRealCompanies` (unconditional `fetch` at `app.js` `init`) →
`companies.json` 404. Vendored `ui/public/vendor/chart.umd.min.js` + `marked.esm.min.js` carry a trailing
`//# sourceMappingURL=…map` → two more 404s. Bundling: `scripts/build_ui_shortlist.py` /
`build_ui_companies.py` + `make preview` (Makefile). e2e: `scripts/ui_e2e.py`.

## Slices (each a topic branch; TDD; `make check` green before PR)

### Slice A — `chore/tailor-prompt-voice-mitigation` (prompt only, no CLI)
Update `.claude/workflows/cc-workflow-tailor-offer.js`: (1) bake **voice** into the CV/cover/match agent
prompts (value-prop named · synergy-led · weaknesses reframed as deliberate growth-exposure · outward
never lists weaknesses); (2) reinforce the **honesty boundary** (never claim uncovered=covered; never
invent); (3) extend the **gap agent + `matchSchema.must_haves`** to emit, per uncovered must-have, a
**mitigation** (honest reframe + smallest real action, tied to the portfolio plan) and a **suggestion**
(next step) — written into `gap_report` + the `resources` field (both PRIVATE). Add a "Top-3 prep actions"
digest to `gap_report`. New keys OPTIONAL. No unit tests (JS Workflow prompt; validated by Slice B/C output
checks + a live tailor smoke). Docs: changelog + note in architecture (voice/mitigation now workflow-encoded).

### Slice B — `feat/pack-coverage-policy` (the user knob + guarantee)
- `models.py`: `PackPolicy` `{min_score:int=5, max_packs:int=0, lanes:list[str]=[], per_company_cap:int=0, dedup:str="role_x_company"}`.
- New `src/ajoa_kit/pack_plan.py` (pure core + thin `main`): `load_policy(config_dir)` (mirror
  `load_lanes`; `config/pack-policy.json` absent→default `PackPolicy()`); `select(shortlist_rows, policy)`
  → ordered target ids (score>=min, lane filter, dedup role×company, per-company cap, max cap);
  `missing(targets, offer_index)` → ids lacking a pack; `main(...)` composes `load_shortlist`(all lanes) +
  `_load_offer_index`, writes the **work list** `results/pack-plan.json` = `[{offer_id,lane,score}]`
  (ready to feed the tailor Workflow) + a human summary ("covered X/Y; missing: …").
  **Guarantee** = orchestrator loops `pack-plan` → tailor Workflow per missing id → `persist-offer` until
  `missing == []` (idempotent; skip existing).
- CLI `ajoa-kit pack-plan`: `--min-score --max-packs --lanes --json --dry-run` overriding policy.
- **Tests** (`tests/test_pack_plan.py`): `select` (score filter, dedup, per-company cap, max cap, lane
  filter, stable order); `missing` (diff vs offer index). NOT the thin `main`/CLI.
- **ADR-0005** `docs/decisions/0005-pack-coverage-policy.md`: policy contract, coverage guarantee, config+CLI
  precedence, no-pydantic-pack-model constraint.

### Slice C — `feat/pack-output-eval` (self-verify) + persist_offer hotspot refactor
- **Refactor first (quality-only, behaviour-identical):** extract the warning-sidecar family in
  `persist_offer.write_pack` into a **check registry + `_emit_check(name, fn, pack, results_dir)`** loop;
  reduce `jd_truncation_warning` (complexity 10) by extracting a helper. Regression-pinned by the 22
  `test_persist_offer.py` tests (no new tests unless extraction exposes a real unit).
- **New deterministic checks (pure siblings):** `src/ajoa_kit/grounding.py` →
  `grounding_warnings(cv_md, evidence_library:dict) -> list[str]` (flag CV claims unsupported by
  `headline/positioningSummary/skillClusters/masterCvBullets/perProject/<lane>Angle`; read via
  `results_dir/"evidence-library.json"` like `lane_angle_warning`, never-guess). Honesty:
  `honesty_warnings(must_haves) -> list[str]` (uncovered marked covered; covered w/ null evidence) — in
  `coverage.py` or new `honesty.py`. Wire both as registry entries → `cv-grounding-check.md`,
  `honesty-check.md` sidecars.
- **Tests** (`tests/test_grounding.py`; honesty in `test_coverage.py`): mirror `test_stuffing.py`.
  Fixture: `examples/alexis-doe/results/evidence-library.json`.

### Slice D — `fix/dashboard-console-404s` (clean console + network; e2e hardening)
- `companies.json` 404 (**PAGE-caused**, seen headless) → bundle an empty `[]` `companies.json` in
  `make preview` + gh-pages deploy (`scripts/build_ui_companies.py` / Makefile); `loadRealCompanies`
  handles empty. Remote also 404s `shortlist.json` — **expected** (published site falls back to synthetic
  `demo.json`); leave it.
- Sourcemap 404s (`chart.umd.min.js.map`, `marked.esm.js.map`) are **DevTools-only** — chromium fetches
  `.map` files *only when DevTools is open*, so a **headless e2e never sees them** (verified 2026-08-22: the
  network-layer capture showed only `companies.json`). They still appear in a human's open console, so fix
  by stripping the trailing `//# sourceMappingURL=` line from the two vendored files, and **verify with a
  STATIC check** (grep the vendored files) — NOT an e2e network assert.
- **Harden `scripts/ui_e2e.py`**: capture the **page network layer** (`page.on("response")`) and assert
  **zero unexpected PAGE 404s** (i.e. `companies.json` gone after the fix; whitelist remote `shortlist.json`).
  Add `make ui_e2e`. Stop any leftover preview server. No Python unit tests (scripts/static assets).
  - **Driver caveat (verified 2026-08-22):** polyfetch's `render_session` hardcodes `headless=True` and runs
    `goto` inside `__enter__` (can't attach a response log before nav; container `/dev/shm` OOM'd the renderer
    on reload). So drive patchright directly — reuse polyfetch's `context_kwargs`/`attach_capture`, add
    `--disable-dev-shm-usage`, and attach `page.on("response")` **before** goto. A working reference driver was
    left at `results/ui-e2e/_run.py` (git-ignored) to adapt.
  - Minor appearance (optional polish): on mobile the shortlist table's right columns (Lane/Score/Verdict)
    clip inside `.table-wrap` (scrolls within the container; no document overflow) — acceptable, worth a glance.

### Retrofit (data op, not a PR) — private mitigation layer on the 32 existing packs
Subagent pass per pack: append "Gap Mitigation & Prep" to `gap-report.md` + enrich `coverage-report.md`
resources, grounded in that pack's gaps + the portfolio plan + evidence library. **Verify no outward doc
changed** (diff shows only gap-report/coverage-report; re-run `ats-check`). All under git-ignored `results/`.

## Docs & issues
- **changelog.d/** fragment per slice (scriv `### Added`/`### Changed`/`### Fixed`, author `93844790+qte77`).
- **README**: `pack-plan` + `config/pack-policy.json` + new checks; the two new subcommands' `--help`.
- **architecture.md**: pack-selection/coverage flow + eval sidecars + voice/mitigation-in-workflow.
- **ADR-0005** (Slice B). **roadmap.md**: shipped bullets. **userstory.md**: add "cover all score-5s
  automatically" story if it fits the format.
- **URL/env/CLI check**: document `config/pack-policy.json`, `AJOA_*`, every new flag in README + quickstart + `--help`.
- **Issues**: FRs for pack-coverage-policy + output-eval; the earlier `evidence-guard` + `apply-kit` FRs; a
  **deferred-BAML FR** ("evaluate BAML at the portable-runner/product milestone" — records *why deferred now*:
  Claude-Code orchestration needs no API keys/DSL; BAML fits the direct-API product path). All gated on a valid token.

## Git workflow
Topic branches: `chore/tailor-prompt-voice-mitigation` · `feat/pack-coverage-policy` · `feat/pack-output-eval`
· `fix/dashboard-console-404s`. Per branch: `make check` (+ `make ui_e2e` for D) green → commit **authored
qte77** (Co-Authored-By) → push → open PR → **squash-merge ONLY if all CI + tests pass** → delete merged
local+remote branch. **AUTH-GATED**: needs a valid token (`gh auth login`; dntywntme's is invalid) — until
then, local work + `make check` proceed and stop at "ready to push".

## Verification (end-to-end)
1. `make check` green after each slice (ruff/format/pyright/complexipy≤10/pytest cov≥80).
2. `uv run pytest tests/test_pack_plan.py tests/test_grounding.py tests/test_coverage.py -v`.
3. Live: `ajoa-kit pack-plan --min-score 5 --json` → `results/pack-plan.json` lists exactly the score-5
   shortlist ids lacking `results/offers/<slug>/`; after tailoring the loop, a re-run reports `missing: []`.
4. Tailor smoke: one offer → pack carries private mitigation/prep in gap-report only; `cv-grounding-check.md`
   /`honesty-check.md` absent on a clean pack, present+accurate on a seeded-bad one.
5. `make ui_e2e`: dashboard local+remote show **zero unexpected 404s** (console AND network); interactions pass.
6. `make docs_lint` (CI) green.
7. After re-auth: 4 PRs, squash-merged only on green, stale branches deleted; FR issues filed.

## Gates (fail-closed)
- **Voice/PII**: outward docs never carry weaknesses; mitigation/eval findings private; nothing under `results/` committed.
- **Coverage guarantee**: `pack-plan` re-run must report `missing: []` before "done".
- **Green-only merge**: no squash without green `make check` + e2e (+ CI when a valid token exists).
- **Auth**: push/PR/issues blocked until `gh auth login` succeeds.
