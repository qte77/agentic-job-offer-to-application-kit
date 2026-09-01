# Handoff 012 — Tiered auto-open + browser prefill for application URLs (#417)

Read this first; the matching plan
[`docs/plans/012-tiered-apply-prefill.md`](../plans/012-tiered-apply-prefill.md) holds the full
spec, source map, and the single remaining-work table (do not duplicate that table here — this
file only points at it).

## State

Branch `docs/plan-012-tiered-apply-prefill`, off `main` at the tip after #418 (SHIPPED stamps on
plans 001–003). This PR carries only this handoff, the plan, and the `docs/research.md` fix
(remaining-work item 1). No code changes yet.

## Done

- All 8 `docs/research.md` §Delivery primary sources re-verified live (Greenhouse, Ashby, Lever,
  Workable API+ToS; LinkedIn/Indeed automation clauses) — all still hold; two doc facts fixed
  (Greenhouse URL redirects, Workable uncertainty → confirmed-gated) in this same PR.
- `render_session`'s hardcoded `headless=True` verified by reading
  `polyfetch-scrape/src/polyfetch_scrape/render_session.py` directly.
- Confirmed no structured candidate-profile source exists anywhere in this repo today.
- CLI-vs-UI decision ratified (CLI-only) — reasoning in the plan's Decision section; also post it
  as a comment on #417.
- This plan + handoff written.

## Resume here (in order)

Follow the plan's remaining-work table as the single source of truth for what's open; the ordered
summary:

1. Item 2 — `config/candidate.json` scaffold (`CandidateProfile` model + loader + quickstart doc).
2. Item 3 — tier 1 `open-offers` CLI. Independent of item 2; can run in parallel.
3. Item 4 — tier 2 `locate-fields` CLI. Independent of items 2/3; can run in parallel.
4. Item 5 — tier 3 dry-run `fill-offer` CLI. **Depends on items 2 and 4 being merged to `main`**
   (needs `CandidateProfile` from item 2 and the field-locate helper from item 4) — do not start
   until both land. Also pre-stage (not push) the `polyfetch-scrape` `headless` param diff here.
5. Item 7 — the Phase B owner decision (headed vs. dry-run-only). Present the pre-staged diff from
   item 5/6 and the tradeoff written out in the plan's Phase B section; do not default this
   silently even though everything else in this arc is decide-by-default — the plan explicitly
   flags it as the one gate.
6. Item 8 — only if item 7 picks headed: push the polyfetch-scrape PR, wire `--headed`, full e2e,
   close #417.
7. File the two deferred-item follow-on issues (items 9–10) before considering Phase A closed.

## Per-slice recipe (applies to items 2–5)

- Branch off `main` (`feat/...` per repo convention), one topic branch per item.
- Strict TDD for the pure logic named in the plan's Testing section (red first).
- `make check` + `make docs_lint` green before pushing.
- `make changelog_new` fragment (all four are behaviour-changing).
- Update the doc-impact rows the plan's audit table assigns to that item — do not touch a doc row
  another item owns; the audit table is per-file, not per-item, so check for overlap (e.g. the
  CONTRIBUTING CLI table gains one row per item — don't let two parallel branches both try to add
  their row to the same table position without expecting a small merge conflict; resolve by
  keeping both rows, alphabetical by subcommand name).
- Open PR, wait for its own CI (`gh pr checks <n>`, not a sibling PR's), squash-merge on green,
  delete both branches.
- Comment progress on #417.

## Gotchas

- `pack-plan.json`'s on-disk output drops `.url` — call `pack_plan.select()` as a library function
  and read `.url` off the in-memory `ScoredItem`s, or read `shortlist.json` directly. Do not try to
  recover `url` from `pack-plan.json`.
- Tiers 2/3's selection is the *inverse* of `pack_plan.missing()` — intersect with the offer index,
  don't exclude.
- `s.fill()` silently no-ops on framework-controlled inputs (React/Vue/Svelte) — use
  `page.locator(...).press_sequentially(value, delay=25)` for every text field tier 3 writes.
- `render_session` is headless-only today (verified at source) — tier 1 must use stdlib
  `webbrowser.open()`, not `render_session`, or it shows the human nothing.
- Bash `grep`/`ls`/`head -c`/`sed` against paths outside this repo's normal working set get
  permission-denied in this environment — use the `Read` tool, or run `grep`/`ls` scoped to files
  already known to exist inside this repo's own tree only when Read isn't practical.
- Devcontainer: `~/.cache/ms-playwright` is a symlink into ephemeral `/tmp` — `mkdir -p` the target
  before `patchright install` after any container restart.
- e2e fixtures live under `tests/fixtures/forms/` and are served on `localhost` (not `127.0.0.1` —
  matters for polyfetch's SSRF guard) — never point any tier at a real employer's live form.

## Touch points (current state)

| Path | State |
|---|---|
| `src/ajoa_kit/models.py` | Exists; `PackPolicy` and `ScoredItem` already defined — add `CandidateProfile` alongside them. |
| `src/ajoa_kit/pack_plan.py` | Exists; `load_policy()`, `select()`, `missing()`, `main()` all present — reuse `select()`, do not duplicate its filter/sort logic. |
| `src/ajoa_kit/prefill.py` | Exists; `GENERIC_FIELDS`, `fetch_greenhouse_questions()`, `parse_greenhouse_questions()` present — schema only, no values. |
| `src/ajoa_kit/persist_offer.py` | Exists; `_load_offer_index()`, `write_pack()`, `safe_slug()` present. |
| `src/ajoa_kit/render_pdf.py` | Exists; manual/opt-in, not wired into `persist-offer`. |
| `src/ajoa_kit/open_offers.py` | Does not exist yet — item 3 creates it. |
| `src/ajoa_kit/locate_fields.py` | Does not exist yet — item 4 creates it. |
| `src/ajoa_kit/fill_offer.py` | Does not exist yet — item 5 creates it. |
| `config/candidate.json` | Does not exist; git-ignored by the existing `config/` rule in `.gitignore` — no gitignore edit needed. |
| `../polyfetch-scrape/src/polyfetch_scrape/render_session.py` | Exists; `RenderSession.__init__`/`render_session()` hardcode `headless=True`, no override param — item 5/6 pre-stages a diff here, not pushed. |
| `tests/fixtures/forms/` | Does not exist yet — item 4/5 creates the plain + controlled-input fixture pair. |
| `docs/research.md` | Exists; this PR fixes the Greenhouse URLs + Workable uncertainty note + adds the re-verification stamp. |
| `docs/quickstart.md`, `README.md`, `CONTRIBUTING.md`, `docs/architecture.md`, `docs/roadmap.md`, `docs/userstory.md` | All exist; each item's doc-impact rows are in the plan's audit table — check it before editing to avoid two items touching the same section unexpectedly. |
