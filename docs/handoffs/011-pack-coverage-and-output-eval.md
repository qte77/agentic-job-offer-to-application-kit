# Handoff 011 — Pack-coverage policy + output-eval + tailor-voice/mitigation + dashboard 404s

Read the spec first: [`docs/plans/011-pack-coverage-and-output-eval.md`](../plans/011-pack-coverage-and-output-eval.md)
(intent + design + `file:line` source map). This doc is *pointer + current state*.

## State
- Branch: work each slice on its own topic branch (see Per-slice recipe). The tree currently also holds
  unrelated in-flight topics (discovery-adapters, shortlist-ordering, verify-sources, UI-badge) — keep
  Plan 011 commits separate from those.
- `gh` auth: **dntywntme token is invalid** → push/PR/issues blocked until `! gh auth login -h github.com`.
  Commits are authored **qte77** regardless of the pushing token.
- `make check` is green on the current tree (267 tests). `docs_lint` (markdownlint-cli2) runs in CI only.

## Done
- Nothing in Plan 011 is implemented yet. The plan + this handoff are the only 011 artifacts.
- Prereqs that already exist and are reused (do not rebuild): `persist_scored.load_shortlist`,
  `persist_offer._load_offer_index` + the `write_pack` sidecar idiom, `ats_check`/`stuffing`/`coverage`
  pure checkers, the `ingest.load_lanes`/`load_manual_jds` config-loader idiom, `refresh.py` reconciler shape.

## Resume here (in order)
1. **Slice A** `chore/tailor-prompt-voice-mitigation` — voice + honesty + private mitigation/prep in the
   tailor Workflow prompt (`must_haves` gains mitigation/suggestion; gap-report gains a Top-3 prep digest).
2. **Slice C** `feat/pack-output-eval` — refactor `persist_offer` sidecars into a check-registry FIRST
   (behaviour-identical, pinned by existing tests), then add `grounding_warnings` + `honesty_warnings` as
   registry entries. (Do C before/with B so the eval seam exists.)
3. **Slice B** `feat/pack-coverage-policy` — `PackPolicy` model + `pack_plan.py` (`select`/`missing`/`main`) +
   `ajoa-kit pack-plan` CLI + `config/pack-policy.json` loader + **ADR-0005**.
4. **Slice D** `fix/dashboard-console-404s` — empty `companies.json` bundle + strip vendored sourcemap
   comments + harden `scripts/ui_e2e.py` to assert zero unexpected network 404s + `make ui_e2e`.
5. **Retrofit** the 32 existing packs' private mitigation layer (data op on git-ignored `results/`, not a PR).
6. **Docs + issues + git-land** each slice (see plan) once a valid token exists.

## Per-slice recipe
- Branch off the default branch; keep the diff to that slice's files only.
- **TDD**: write the failing pure-function tests first, then implement to green. Tests only for the pure
  modules (`select`/`missing`, `grounding_warnings`, `honesty_warnings`) — not thin CLI/handlers/orchestrators.
- `make check` green (ruff/format/pyright/complexipy≤10/pytest cov≥80) before opening a PR; `make ui_e2e` for D.
- Commit (Co-Authored-By) → push → PR → **squash-merge only if all CI + tests pass** → delete local+remote branch.

## Gotchas
- **Voice/PII invariant:** mitigation/prep + eval findings are PRIVATE (gap-report + sidecars). The outward
  CV/cover/match must never list weaknesses. Verify any pack edit changed only gap-report/coverage-report.
- **Nothing under `results/` is committed** (PII/business data) — the retrofit + `pack-plan.json` stay local.
- **No pydantic model for the pack itself** (plan 007) — new pack/`must_haves` keys stay OPTIONAL so older
  packs still validate.
- **Tailoring is a Claude Code Workflow, not a CLI verb** — `pack-plan` only *reports* the missing-pack work
  list; the coverage guarantee is the orchestrator looping until `missing == []`.
- `complexipy` ceiling is 10 — `jd_truncation_warning` is already at 10; the registry refactor must not push
  any function over.
- New docstrings/comments: keep lines ≤100 (ruff E501 bites the `·`/backtick-heavy lines).

## Touch points (current state)
| Path | Current state |
|---|---|
| `.claude/workflows/cc-workflow-tailor-offer.js` | tailor prompt + `matchSchema`; NO voice/mitigation baked in yet |
| `src/ajoa_kit/pack_plan.py` | **does not exist** — create (Slice B) |
| `config/pack-policy.json` | **does not exist** — absent-file-inert loader defaults to `PackPolicy()` |
| `src/ajoa_kit/models.py` | has `ScoredItem`; **no `PackPolicy`** yet — add it here (ADR-0003 home) |
| `src/ajoa_kit/grounding.py` | **does not exist** — create (Slice C), sibling of `ats_check`/`stuffing` |
| `src/ajoa_kit/coverage.py` | has `coverage_summary`; **no `honesty_warnings`** yet |
| `src/ajoa_kit/persist_offer.py` | hotspot (churn/dup); sidecars written inline in `write_pack` — refactor to a check-registry |
| `src/ajoa_kit/__main__.py` | subcommands registered here; **no `pack-plan`** yet |
| `tests/test_pack_plan.py` / `tests/test_grounding.py` | **do not exist** — create |
| `tests/test_persist_offer.py` | 22 tests pin the sidecar wiring — must stay green through the refactor |
| `ui/src/companies.js` | `loadRealCompanies` fetches `companies.json` unconditionally → 404 |
| `ui/public/vendor/chart.umd.min.js`, `marked.esm.min.js` | trailing `//# sourceMappingURL=` → `.map` 404s |
| `scripts/ui_e2e.py` | exists; captures console only — **does not assert network 404s** yet |
| `docs/decisions/0005-pack-coverage-policy.md` | **does not exist** — create (Slice B) |
