# Backlog execution plan

A sequenced implementation plan for the open issues: recommended order, per-issue approach (with
vetted gotchas), dependencies, and the decisions a maintainer makes before each slice. High-level
status is in [roadmap.md](../roadmap.md); this is the execution detail.

## Conventions (every slice)

- Topic branch per slice → commit by topic (`git commit --no-gpg-sign`) → PR base `main` →
  `gh pr checks <n> --watch` → squash-merge on green. Rebase with `git -c commit.gpgsign=false rebase …`
  (global commit signing is on, so a plain rebase fails to sign).
- Run `make check` + `make docs-lint` locally before pushing — catches ruff/pyright/complexipy/pytest/
  coverage and markdownlint/lychee before CI.
- One [scriv](https://scriv.readthedocs.io/) fragment per PR under `changelog.d/` (`make changelog_new`).
- TDD, value-add tests only — see [AGENTS.md](../../AGENTS.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md).
  L3 `.js` workflows aren't unit-testable; put testable logic in the L1 Python they call.
- Docs-only PRs (`*.md`, `docs/**`, `changelog.d/**`, `lychee.toml`, `.markdownlint-cli2.jsonc`) skip
  CI + CodeQL via `paths-ignore`; the `lint-md-links` workflow still runs.

## Order

### 1. Locale axis — #31 + #12 (small, TDD on #31; pair)

- **#31** — make `ingest.py`'s `INTEREST`/`TITLE_ROLES` locale-driven. Put the default `keywords.json`
  in `src/ajoa_kit/data/` (load via `importlib.resources`); keep the module constants as the in-code
  fallback (no duplication). Switch the `keep()`/`collect()` filter to a **closure passed as a
  `filter_fn`** rather than threading args. Annotate `re.Pattern[str]` for pyright. Note: `from_personio`
  hardcodes `?language=en`, so German Personio boards still return English — scope that out or handle it.
- **#12** — spec at **`docs/locale-conventions.md`** (NOT `config/`, which is git-ignored); wire an
  optional `locale` arg into the tailor workflow using `${rootDir}/docs/locale-conventions.md`.
- **Decisions:** `src/ajoa_kit/data/` vs `config/` ownership and global-vs-per-source locale (#31);
  which locales to ship (#12).

### 2. #55 — JD must-have coverage (small, TDD)

L1 `coverage_summary(must_haves, gap_report)`; **drop** a `parse_must_haves` helper (redundant). The
tailor Match agent returns a structured `must_haves` array (needs an inline JSON-schema; `strField`
can't express it). Write `coverage-report.md` as a **post-render step** in `write_pack()`, **not** an
`ARTIFACTS` entry (preserves the all-or-nothing `render()` contract); update `tests/test_persist_offer.py`'s
file-list assertion.

### 3. #53 — per-adapter error tests (medium, TDD)

Error/edge tests for the `ingest.py` `from_*` adapters (malformed payloads, missing fields, non-200,
empty results). Offline fixtures, no `network` mark. Legitimately raises the coverage floor (the gate
added under the closed coverage issue).

### 4. #11 PR-A — trend-snapshot (small, TDD)

New L1 `trend_snapshot.py` + a `trend-snapshot` subcommand appending/upserting an ISO-week record to
`results/trends.ndjson`. **Import** `INTEREST`/`TITLE_ROLES` from `ingest.py` (don't copy) and match
with the compiled word-boundary regexes (not naive tokenizing); reuse `results_dir`; don't touch
`.gitignore`. Test a multi-word term.

### 5. #56 — prefill-pack reach (small)

**Probe** whether the Ashby job-board GET embeds an `applicationForm` (network). If yes →
`parse_ashby_questions`/`fetch_ashby_questions` mirroring the Greenhouse path + an offline-fixture
test; if no → a comment above `GENERIC_FIELDS` citing the issue. Issue-only triage adds no changelog
fragment.

### 6. #52 — pseudonymize-text (medium, TDD)

An L1 helper that strips company / person / contact PII from records before any public surface.
Blocks the dashboard (#11 PR-B) under the ADR-0001 hard PII gate.

### 7. #11 PR-B — gh-pages dashboard (medium, L4; blocked by #52)

Static Chart.js `ui/` on GitHub Pages. Playbook (from `qte77/analyze-stock-kpi`): official Pages
deploy (`actions/configure-pages` → `upload-pages-artifact` → `deploy-pages`, `environment:
github-pages`, `permissions: pages:write, id-token:write`); **no build** (`cp -r ui/. _site/`);
**vendored** Chart.js (no CDN); **data on a separate `data` branch fetched at runtime — only
pseudonymized data may land there**; EyeRest zero-blue data-arc tokens via CSS vars, three-state
(`system`/`light`/`dark`) theme.

### 8. #54 — org-settings apply (medium)

Apply branch protection + widen the Actions allowlist. **Must add a same-named always-pass shim** for
the jobs `paths-ignore`d by CI/CodeQL, or docs-only PRs would stall on a never-reported required check.

## Issue index

| # | Slice | Effort | Blocked by |
| --- | --- | --- | --- |
| [#31](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/31) | i18n keywords | small | — |
| [#12](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/12) | locale conventions | small | — |
| [#55](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/55) | JD must-have coverage | small | — |
| [#53](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/53) | per-adapter tests | medium | — |
| [#11](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/11) | trend-snapshot / dashboard | small / medium | #52 (PR-B) |
| [#56](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/56) | prefill-pack reach | small | — |
| [#52](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/52) | pseudonymize-text | medium | — |
| [#54](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/54) | org-settings apply | medium | — |
