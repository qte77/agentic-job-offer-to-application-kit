# Plan 008 — `render-pdf`: optional light Markdown→PDF for tailored packs (#275)

> **Closed plan, kept as a record.** Commands in it are one machine's history, not procedure; for current steps see the repo's CONTRIBUTING and the newest plan.

**Status: SHIPPED (2026-07-19)** — #275 CLOSED via #335 (`render-pdf` feature) + #336 (glue smoke test).
Spike done → **GO via fpdf2**. Kept as history; carries the symbol-level source map from the build.
Handoff: [§Handoff](#handoff).

## Context

Issue #275 asks for an OPTIONAL, lazy-imported `ajoa-kit render-pdf FILE` verb that turns a tailored `.md`
(`results/offers/<slug>/cv.md` / `cover-letter.md`) into a clean, ATS-safe, single-column PDF a human can
submit — never a core dependency (no-build / no-LaTeX ethos, ADR-0001 / #71). Closes #275.

**Why fpdf2 (spike verdict, 2026-07-14):** the only Markdown→PDF path that is pure-wheel / no-system-libs /
no-build AND yields a real selectable text layer. Rejected: **weasyprint** (needs Pango/HarfBuzz system libs),
**pandoc-if-present** (cannot emit PDF without a LaTeX/typst engine), **headless-chromium/md-to-pdf** (a whole
browser). One point the read-only spike could NOT measure: `pdftotext` on fpdf2 output — the live verify below
closes it.

## Source map (verified 2026-07-14, `file:line` — reuse, don't rebuild)

### Reuse patterns

- **Lazy optional-dep** — `src/ajoa_kit/sources.py:41-42` (in `get_json`) and `:57-58` (in `get_bytes`):
  `# lazy: keep pure logic importable w/o polyfetch` then `from polyfetch_scrape import FetchError, fetch`.
  Docstring `sources.py:7-9` states the "importable offline" intent. → `render_pdf.py` lazy-imports fpdf/markdown_it identically.
- **CLI verb** — `src/ajoa_kit/__main__.py:67-71` `_ats_check` handler (`from ajoa_kit.ats_check import main as run; run(src=Path(args.file))`);
  registration `:227-231` (`ats_p = sub.add_parser("ats-check", ...)` + `.add_argument("file", ...)` + `.set_defaults(func=_ats_check)`).
  Dispatch is generic (`args.func(args)`); usage list in the module docstring `:3-18`.
- **Input artifacts** — `src/ajoa_kit/persist_offer.py`: `ARTIFACTS` `:33-39` defines `("cv","cv.md",…)` /
  `("cover_letter","cover-letter.md",…)` written under `results/offers/<slug>/`. Each body is wrapped by
  `render()` `:84` as `---\ntitle: "<heading>"\n---\n\n<body>\n`. **Reuse `strip_frontmatter(md)` `:146-152`**
  (drops that block, returns body) — the exact helper the renderer consumes.
- **ATS constraints the PDF must preserve** — `src/ajoa_kit/ats_check.py:44-53` (`parse_safety_warnings`) bans
  tables/multi-col, raw HTML, images, HTML comments (hidden text); requires standard headings (regex `:28-31`:
  `summary|profile|experience|education|skills|projects|work history|employment`). → PDF must be **single-column,
  real selectable text, headings intact**. (fpdf2's weak spots — tables/multi-col — are irrelevant; ats-check already bans them.)
- **pyproject deps** — `pyproject.toml:10-14` core = `defusedxml` / `pydantic` / `pydantic-settings` only;
  comment `:9` "polyfetch-scrape … never installed here"; **no `[project.optional-dependencies]` table exists yet**;
  dev group `[dependency-groups].dev` `:19-32`.

### New / changed

- `pyproject.toml` — add `[project.optional-dependencies]` `pdf = ["fpdf2>=2.8", "markdown-it-py>=3.0"]`; add the
  same two to `[dependency-groups].dev` (so `make check` renders live). Core deps untouched.
- **NEW** `src/ajoa_kit/render_pdf.py` (L1) · `tests/test_render_pdf.py` — **do not exist yet**.
- `src/ajoa_kit/__main__.py` — add `_render_pdf` + a `render-pdf` parser + usage line.

## Design

`render_pdf.py`:

- **Pure (TDD surface):** `_normalize_html(html: str) -> str` — `<strong>`→`<b>`, `<em>`→`<i>`; strip tags outside
  fpdf2 `write_html`'s subset (keep `h1-h6, p, ul, ol, li, b, i, hr, blockquote, br`; drop `code, pre, table, img, …`).
  String/regex only, **no dep** → imports + tests offline.
- **Glue (verified live, NOT unit-tested):** `render_pdf(md: str, out: Path, title: str | None) -> None`:
  `strip_frontmatter(md)` → lazy `from markdown_it import MarkdownIt; MarkdownIt().render(body)` → `_normalize_html` →
  lazy `from fpdf import FPDF; pdf=FPDF(); pdf.add_page(); pdf.set_font(...); pdf.write_html(html); pdf.output(str(out))`.
  Single column; frontmatter `title` → doc title/header.
- `main(src: Path | None = None, out: Path | None = None)` — argparse when `src` is None; `out` defaults to
  `src.with_suffix(".pdf")`. Wrap the lazy import: `except ImportError:` → "PDF export needs the extra — `pip install ajoa-kit[pdf]`".
- **Unicode gotcha:** fpdf2 core fonts are latin-1, but CV bodies carry `—` / `·` / `é` / smart-quotes →
  `add_font` a Unicode TTF (`fc-match` / system DejaVu at `/usr/share/fonts`, else bundle a small OSS TTF), else
  transliterate those chars in preprocessing. The live `pdftotext` check catches garble. (complexipy ≤10 — keep functions small.)

`__main__.py` (mirror `_ats_check`):

```python
def _render_pdf(args: argparse.Namespace) -> None:
    """Render a tailored .md (cv/cover-letter) to an ATS-safe PDF (needs the [pdf] extra)."""
    from ajoa_kit.render_pdf import main as run

    run(src=Path(args.file), out=Path(args.out) if args.out else None)


# ... in main():
rp = sub.add_parser(
    "render-pdf", help="Render a tailored .md to an ATS-safe PDF. Needs the [pdf] extra."
)
rp.add_argument("file", metavar="FILE", help="Path to a tailored markdown file.")
rp.add_argument("--out", default="", help="Output PDF path (default: <file>.pdf).")
rp.set_defaults(func=_render_pdf)
```

## Docs

CHANGELOG fragment (Added: `render-pdf` verb + `[pdf]` extra); CONTRIBUTING §CLI-subcommands table row + a
`uv sync --extra pdf` install note; `__main__` usage docstring; architecture **Built** line + **§Data layout**
(PDF written beside the `.md` under local `results/offers/<slug>/`, never published). README optional.

## Verification

- `pytest tests/test_render_pdf.py` red→green: `_normalize_html` maps `strong→b` / `em→i`, strips unsupported tags,
  operates on the frontmatter-stripped body. Behavior-focused, no dep.
- **Live (closes the spike's one gap):** `uv sync --extra pdf` → `ajoa-kit render-pdf results/offers/<slug>/cv.md` →
  `pdftotext out.pdf -` shows **selectable, single-column, top-to-bottom-ordered** text with section headings intact.
- `make check` green (pure test; fpdf2/markdown-it lazy → offline import holds); `markdownlint-cli2 --no-globs` on
  changed md. Gate LAST → commit by topic (`--no-gpg-sign`) → PR (`Closes #275`) → squash-merge on green → prune.

## Guardrails (#275)

Optional + lazy-imported, never core · no LaTeX / no build step (fpdf2 pure wheels) · ATS-safe single-column
selectable text (`pdftotext`-verified).

## Handoff

The session handoff for this arc, merged in from the former `docs/handoffs/` folder (one file per arc). Historical: this arc is closed.

**State (2026-07-19): SHIPPED.** #275 CLOSED via #335 (the `render-pdf` feature) + #336 (glue smoke test);
`main` @ `983ff6a`. Kept as history — the source map below is the record. Plan:
[docs/plans/008-render-pdf.md](008-render-pdf.md).

### Done (context)

The #275 spike is complete → **GO with `fpdf2`**. Only fpdf2 (+ `markdown-it-py`) fits the no-build / no-LaTeX ethos
(pure wheels, no system libs, real selectable text); weasyprint (system libs), pandoc (needs a LaTeX/typst engine),
and headless-chromium (a browser) were rejected. Owner **approved implementing it**. The spike result + plan are
also on issue #275 (2026-07-14 comment).

### Resume here (one PR `feat/render-pdf`, `Closes #275` — in order)

1. `pyproject.toml` — add `[project.optional-dependencies]` `pdf = ["fpdf2>=2.8", "markdown-it-py>=3.0"]` **and**
   add both to the `[dependency-groups].dev` group. `uv sync --extra pdf`.
2. **TDD** `tests/test_render_pdf.py` → `src/ajoa_kit/render_pdf.py` `_normalize_html` (pure) red→green.
3. Add the glue `render_pdf()` + `main()` — lazy `fpdf` / `markdown_it`; reuse `persist_offer.strip_frontmatter`.
4. `src/ajoa_kit/__main__.py` — `render-pdf` verb, mirroring `_ats_check` / `ats-check` (see the plan's snippet).
5. Docs (CHANGELOG / CONTRIBUTING CLI table / architecture) → gate → PR → merge.

### Per-slice recipe

Branch off fresh `main` → TDD red→green (pure `_normalize_html` only; the render is glue, **verified live**) →
mutators (`ruff --fix`/format) → **gate LAST** (`make check` + `markdownlint-cli2 --no-globs` on changed md) →
commit by topic (`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN` push/gh → PR → `gh pr checks <n> --watch` →
`gh pr merge <n> --squash --delete-branch` on green → prune local + `git remote prune origin`.

### Gotchas

- **fpdf2 latin-1 fonts** — CV bodies carry `—` / `·` / `é` / smart-quotes → embed a Unicode TTF (`add_font`) or
  transliterate; the live `pdftotext` check catches garble. This is the plan's one un-de-risked point.
- Keep `fpdf` / `markdown_it` imports **inside** functions so `render_pdf.py` imports offline (mirrors `sources.py`).
- `env -u GH_TOKEN -u GITHUB_TOKEN` on all `gh`/`git push`; `×` trips RUF001-3 (use `x`); `lint/links` runs whole-repo
  lychee and flakes on a transient external link — `gh run rerun <id> --failed` (not your diff).

### Touch points (current state — verify, don't re-map; line detail is in the plan)

| Path | State |
|---|---|
| `src/ajoa_kit/render_pdf.py` · `tests/test_render_pdf.py` | **do not exist yet** — the new L1 module + its TDD. |
| `src/ajoa_kit/sources.py` | shipped — the lazy `from polyfetch_scrape import fetch` pattern the renderer mirrors. |
| `src/ajoa_kit/ats_check.py` | shipped `parse_safety_warnings` — defines the ATS constraints the PDF must preserve (single-column, real text, standard headings). |
| `src/ajoa_kit/persist_offer.py` | shipped `strip_frontmatter` (reuse) + `ARTIFACTS` (`cv.md` / `cover-letter.md` inputs). |
| `src/ajoa_kit/__main__.py` | CLI dispatcher; add `render-pdf` mirroring `ats-check`. |
| `pyproject.toml` | core deps only; **no `[project.optional-dependencies]` table yet** — add one. |
| GitHub issues | `#275` OPEN — the PR `Closes` it; a 2026-07-14 comment carries the spike result + this plan. |
