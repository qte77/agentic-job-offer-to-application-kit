# Handoff 008 — `render-pdf` (#275)

**State (2026-07-14): PLANNED, not started.** `main` @ `c5ab2dd`, clean, v0.7.0 released. Approved plan with a
full symbol-level source map — **read it, don't re-map**:
[docs/plans/008-render-pdf.md](../plans/008-render-pdf.md).

## Done (context)

The #275 spike is complete → **GO with `fpdf2`**. Only fpdf2 (+ `markdown-it-py`) fits the no-build / no-LaTeX ethos
(pure wheels, no system libs, real selectable text); weasyprint (system libs), pandoc (needs a LaTeX/typst engine),
and headless-chromium (a browser) were rejected. Owner **approved implementing it**. The spike result + plan are
also on issue #275 (2026-07-14 comment).

## Resume here (one PR `feat/render-pdf`, `Closes #275` — in order)

1. `pyproject.toml` — add `[project.optional-dependencies]` `pdf = ["fpdf2>=2.8", "markdown-it-py>=3.0"]` **and**
   add both to the `[dependency-groups].dev` group. `uv sync --extra pdf`.
2. **TDD** `tests/test_render_pdf.py` → `src/ajoa_kit/render_pdf.py` `_normalize_html` (pure) red→green.
3. Add the glue `render_pdf()` + `main()` — lazy `fpdf` / `markdown_it`; reuse `persist_offer.strip_frontmatter`.
4. `src/ajoa_kit/__main__.py` — `render-pdf` verb, mirroring `_ats_check` / `ats-check` (see the plan's snippet).
5. Docs (CHANGELOG / CONTRIBUTING CLI table / architecture) → gate → PR → merge.

## Per-slice recipe

Branch off fresh `main` → TDD red→green (pure `_normalize_html` only; the render is glue, **verified live**) →
mutators (`ruff --fix`/format) → **gate LAST** (`make check` + `markdownlint-cli2 --no-globs` on changed md) →
commit by topic (`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN` push/gh → PR → `gh pr checks <n> --watch` →
`gh pr merge <n> --squash --admin --delete-branch` on green → prune local + `git remote prune origin`.

## Gotchas

- **fpdf2 latin-1 fonts** — CV bodies carry `—` / `·` / `é` / smart-quotes → embed a Unicode TTF (`add_font`) or
  transliterate; the live `pdftotext` check catches garble. This is the plan's one un-de-risked point.
- Keep `fpdf` / `markdown_it` imports **inside** functions so `render_pdf.py` imports offline (mirrors `sources.py`).
- `env -u GH_TOKEN -u GITHUB_TOKEN` on all `gh`/`git push`; `×` trips RUF001-3 (use `x`); `lint/links` runs whole-repo
  lychee and flakes on a transient external link — `gh run rerun <id> --failed` (not your diff).

## Touch points (current state — verify, don't re-map; line detail is in the plan)

| Path | State |
|---|---|
| `src/ajoa_kit/render_pdf.py` · `tests/test_render_pdf.py` | **do not exist yet** — the new L1 module + its TDD. |
| `src/ajoa_kit/sources.py` | shipped — the lazy `from polyfetch_scrape import fetch` pattern the renderer mirrors. |
| `src/ajoa_kit/ats_check.py` | shipped `parse_safety_warnings` — defines the ATS constraints the PDF must preserve (single-column, real text, standard headings). |
| `src/ajoa_kit/persist_offer.py` | shipped `strip_frontmatter` (reuse) + `ARTIFACTS` (`cv.md` / `cover-letter.md` inputs). |
| `src/ajoa_kit/__main__.py` | CLI dispatcher; add `render-pdf` mirroring `ats-check`. |
| `pyproject.toml` | core deps only; **no `[project.optional-dependencies]` table yet** — add one. |
| GitHub issues | `#275` OPEN — the PR `Closes` it; a 2026-07-14 comment carries the spike result + this plan. |
