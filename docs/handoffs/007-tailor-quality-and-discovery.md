# Handoff 007 — tailor-quality (#272 · #274) + discovery (#292)

**State (2026-07-12):** `main` green at `1de5faa`. Plan (with the full symbol-level source map —
**read it; don't re-map the codebase**):
[docs/plans/007-tailor-quality-and-discovery.md](../plans/007-tailor-quality-and-discovery.md).

## Done

Plan 006 shipped (Companies tab UX, hiring geo-by-field series, `parse_geo` normalization). A
2026-07-12 adversarial distillation (`results/adversarial-hn-launch.md`, git-ignored) set the steer:
**#272/#274 are worth building; #292 is de-prioritized** (personal-tool utility, not a differentiator)
→ scoped to **one source, local-only**. Scope was KISS-reviewed with the user: **#272 full** (critique
phase + deterministic stuffing detector), **#274** as specced, **#292 minimal** (exactly one OK-tier
source). All three issues are already OPEN — each PR `Closes` its own.

## Resume here (in order — one PR per slice)

1. **S1 (#272)** — `feat/tailor-critique`, TDD the Python only. Add the optional `args.critique`
   draft→critique→revise phase to the tailor workflow (JS glue, **verified live** via a real
   `Workflow({name:'tailor-offer'})` run — no unit test) **+** a new pure `stuffing.py` detector
   (red→green) surfaced as an optional `cv-stuffing-check.md` persist artifact. Docs: CHANGELOG +
   script header + CONTRIBUTING §Pipeline.
2. **S2 (#274)** — `feat/gap-report-upskilling`. Extend the gap agent to emit `resources` per uncovered
   must-have (glue) + render them in `coverage_summary` (Python, TDD `tests/test_coverage.py`). No new
   switch. CHANGELOG.
3. **S3 (#292)** — `feat/company-discovery`, TDD the module. New L1 `discover.py`
   (`normalize_company`/`extract_companies`/`emerging_signal`, pure) + network glue (lazy polyfetch) +
   `ajoa-kit discover` verb + a `"discovery"` key (ONE OK-tier source) in `config/default-seed.json` +
   ADR-0003 (source tiering). Output **local `results/emerging-companies.json`, never published**.
   Docs: CHANGELOG + CONTRIBUTING CLI table + `__main__` usage + architecture (Built + Data layout) + ADR.

## Per-slice recipe

Branch off fresh `main` → **TDD red→green for the pure Python only** (glue/prompt is verified live, not
unit-tested) → implement → mutators (`ruff --fix`/format) → **gate LAST** (`make check` +
`markdownlint-cli2 --no-globs` on changed md + `actionlint` on changed workflows) → commit by topic
(`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN` push (`gh auth setup-git` once) → PR (`Closes #NNN`,
cross-ref `#284` with "for #284") → `gh pr checks <n> --watch` → `gh pr merge <n> --squash --admin
--delete-branch` on green → prune local + `git remote prune origin`.

## Gotchas (this environment)

- All `gh`/`git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN` (bare `gh` 401s).
- **Assume strict lint/typing/sec:** ruff incl. **`S`/bandit**, `ruff format`, pyright, `complexipy ≤10`.
  The `×` multiplication sign trips RUF001/2/3 — use `x`; the `·` middle dot is fine.
- **Tailor workflow is L3 glue, verified live** — don't unit-test `agent()`/prompts; TDD only the
  extracted pure Python (`stuffing.py`, the `coverage_summary` extension, `discover.py`).
- **S3 boundary is structural:** discovery names companies → business data → local `results/` only; the
  `make trends-data` fail-closed allowlist refuses it on the `data` branch anyway. Never add to `TRENDS_PUBLISH`.
- **S3 ToS:** the one source must be OK-tier + reachability-verified (ADR-0002) before shipping; read-only
  public GET only; YC Work-at-a-Startup is login-walled → excluded.
- `make changelog_new` needs `mkdir -p changelog.d` first if the dir is empty; `lint/links` runs whole-repo
  lychee (reproduce locally before assuming a red is yours).

## Touch points (current state — verify, don't re-map; line-level detail is in the plan)

| Path | Current state |
|---|---|
| `.claude/workflows/cc-workflow-tailor-offer.js` | 3-phase tailor workflow (Match/Tailor/Prefill, 5 `agent()`); add optional critique phase after Tailor (S1); extend the gap agent (S2). Invoked via the Workflow tool only. |
| `src/ajoa_kit/stuffing.py` · `tests/test_stuffing.py` | **do not exist yet** — the new S1 pure detector + its TDD. |
| `src/ajoa_kit/ats_check.py` | shipped `parse_safety_warnings` (pure) — the sibling pattern `stuffing.py` mirrors. |
| `src/ajoa_kit/persist_offer.py` | shipped `ARTIFACTS` + optional side artifacts (`coverage-report.md`/`cv-ats-check.md`/`meta.json`, kept OUT of `ARTIFACTS`); add `cv-stuffing-check.md` (S1). |
| `src/ajoa_kit/coverage.py` · `tests/test_coverage.py` | shipped `coverage_summary` (pure, defensive) + its tests; extend to render `resources` (S2). |
| `src/ajoa_kit/discover.py` · `tests/test_discover.py` | **do not exist yet** — the new S3 module + its TDD. |
| `src/ajoa_kit/__main__.py` | CLI dispatcher; add a `discover` verb mirroring `_probe`/`_companies_snapshot` (lazy-import) (S3). |
| `config/default-seed.json` | `feeds`/`ats`/`aggregators` loaded; a new `"discovery"` key is ignored by the ingest loader → add ONE OK-tier source there (S3). |
| `src/ajoa_kit/sources.py` · `slug_probe.py` · `normalize.py` · `companies.py` | shipped — reuse: lazy-polyfetch fetch glue + SSRF guard (`sources.py`), name→slug probe (`slug_probe.py`), `company` record field (`normalize.record`), `parse_geo`/`_CITY_ALIASES` normalizer pattern (`companies.py`) as the `normalize_company` model + corpus join. |
| `docs/decisions/0003-discovery-source-tiers.md` | **does not exist yet** — new ADR for S3 source tiering (or amend ADR-0002). |
| `results/evidence-library.json` | per-user grounding corpus (git-ignored); the #272 critic validates CV/cover lines against it. Example: `examples/alexis-doe/results/evidence-library.json`. |
| GitHub issues | `#272`/`#274`/`#292` OPEN (each PR closes its own); `#284` is the S3 consumer (cross-ref "for #284"). |
