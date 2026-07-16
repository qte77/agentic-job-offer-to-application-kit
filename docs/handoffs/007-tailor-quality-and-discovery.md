# Handoff 007 — tailor-quality (#272 · #274) + discovery (#292)

**State (2026-07-13): SHIPPED.** All three slices merged — S1 #272 (#317) · S2 #274 (#318) · S3 #292
(#319); all three issues CLOSED; `main` @ `f73b97c`. Plan (with the full symbol-level source map):
[docs/plans/007-tailor-quality-and-discovery.md](../plans/007-tailor-quality-and-discovery.md).

## Done

Plan 006 shipped (Companies tab UX, hiring geo-by-field series, `parse_geo` normalization). A
2026-07-12 adversarial distillation (`results/adversarial-hn-launch.md`, git-ignored) set the steer:
**#272/#274 are worth building; #292 is de-prioritized** (personal-tool utility, not a differentiator)
→ scoped to **one source, local-only**. Scope was KISS-reviewed with the user: **#272 full** (critique
phase + deterministic stuffing detector), **#274** as specced, **#292 minimal** (exactly one OK-tier
source). All three issues are already OPEN — each PR `Closes` its own.

## Resume here (in order — one PR per slice)

**All three slices are shipped (see State above) — nothing to resume.** What landed, and two
deviations from the original spec worth noting:

1. **S1 (#272) ✅ shipped #317** — `feat/tailor-critique`. Optional `args.critique`
   draft→critique→revise phase in the tailor workflow (JS glue, **verified live** — but via
   `Workflow({scriptPath})`, NOT `{name}`; the name-registry serves a stale session-start snapshot)
   **+** the pure `stuffing.py` detector, surfaced as an optional `cv-stuffing-check.md` persist
   artifact. Docs: CHANGELOG + script header + CONTRIBUTING §Pipeline.
2. **S2 (#274) ✅ shipped #318** — `feat/gap-report-upskilling`. **Deviation:** resources ride on the
   **match** pass's `must_haves` (matchSchema + prompt), not the gap agent — `coverage_summary` already
   consumes `must_haves`, so this is one source with no brittle requirement-text merge. Rendered as a
   Resources column (Python, TDD `tests/test_coverage.py`). No new switch. CHANGELOG.
3. **S3 (#292) ✅ shipped #319** — `feat/company-discovery`. New L1 `discover.py`
   (`normalize_company`/`extract_companies`/`emerging_signal`, pure) + network glue (reuses
   `sources.get_json`) + `ajoa-kit discover` verb + a `"discovery"` key in `config/default-seed.json`
   (**source = yc-oss `companies/hiring.json`**) + **ADR-0004** (source tiering; `0003` was taken).
   Output **local `results/emerging-companies.json`, never published** (verified git-ignored). Docs:
   CHANGELOG + CONTRIBUTING CLI table + `__main__` usage + architecture (Built + Data layout) + ADR.
   Phase-2 (slug wiring) deferred per ADR-0004 + the distillation caveat.

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
| `docs/decisions/0004-discovery-source-tiers.md` | **shipped** (renumbered from 0003 — that number was taken) — S3 source tiering; yc-oss OK, official YC API CAUTION, YC WaaS BLOCKED, newsletters deferred. |
| `results/evidence-library.json` | per-user grounding corpus (git-ignored); the #272 critic validates CV/cover lines against it. Example: `examples/alexis-doe/results/evidence-library.json`. |
| GitHub issues | `#272`/`#274`/`#292` **CLOSED** (#317/#318/#319 respectively); `#284` (S3 consumer) was closed earlier by #294. |

## Post-0.7.0 addendum (2026-07-14) — state + open threads

007 shipped; the session then cut **release v0.7.0** (bump→tag→publish; 17 fragments collected) and did
follow-ups: `#321` discover actionable output + tailor polish · `#322` AGENTS.md `[ ]/[x]` reporting rule ·
`#323` marked plans 004/006 shipped · `#327` recorded discovery-source research verdicts in the seed
(`_blocked`/`_deferred`, `_kind: "discovery"`). `main` @ `0602d79`, clean, v0.7.0 published; dashboard e2e
green (screenshots archived to a private Artifact).

**Open threads — nothing blocking, none urgent:**

1. **#193 adopt reusable release workflows** — BLOCKED on external `qte77/.github#33` (still OPEN; owner is
   GitHub-watching it). On merge: adopt bump/tag/publish as thin `uses:` callers, **SHA-pinned**, guardrails
   intact (never-delete-tags / idempotent / scriv). Recipe in the issue.
2. **Discovery phase-2 = HN "Who is hiring?" Algolia API** — the sole recorded lead (seed `_deferred`
   `_kind:discovery` + ADR-0004). Public/no-auth/broader-than-YC, but needs free-text (regex/LLM) extraction
   → a real slice, only if `yc-oss` proves too narrow. `yc-oss` stays the single live source.
3. **Governance (unfiled): publish per-company hiring on gh-pages** — local-only by design. Reversing it needs
   a new ADR + a **separate** published allowlist, and ONLY the yc-oss public/self-declared slice is
   defensible — **never** the scraped `results/hiring-companies.ndjson`. Decide if worth an issue.
4. **Deferred issues:** `#269` posted_at survivorship series · `#275` md→PDF spike (cheapest to retire — a
   short dependency-weight spike → go/won't-do).
5. **Dependabot:** two open PRs (github-actions + uv python-deps). Review/merge per each PR's own CI (MAJOR
   complexipy/ruff/pyright bumps can red the gate).

**Release gotchas learnt this session:** verify edited `.claude/workflows/*.js` via `Workflow({scriptPath})`
not `{name}` (stale snapshot); collected `CHANGELOG.md` re-lints fragments (MD038 trap); `publish-release.yaml`
is manual-dispatch; `config/` is git-ignored → `git add -f` the seed. (All in local memory.)
