"""Optional Markdown→PDF export for a tailored offer pack (issue #275).

Turns a tailored ``results/offers/<slug>/{cv,cover-letter}.md`` into a clean, single-column,
ATS-safe PDF with a real (selectable) text layer that a human reviews and submits — never a core
dependency (no-build / no-LaTeX ethos, ADR-0001). ``fpdf2`` and ``markdown-it-py`` are imported
lazily so this module stays importable offline (mirrors :mod:`ajoa_kit.sources`); install them with
the ``pdf`` extra::

    uv sync --extra pdf
    ajoa-kit render-pdf results/offers/<slug>/cv.md

The bundled DejaVu Sans TTFs (``fonts/``) give real Unicode glyphs (accents, en-dash, ``·``,
smart-quotes) — fpdf2's core fonts are latin-1 only. Single-column, standard headings, real text:
the ATS constraints :func:`ajoa_kit.ats_check.parse_safety_warnings` enforces are preserved by
construction (fpdf2's weak spots — tables/multi-column — are already banned upstream).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ajoa_kit.persist_offer import strip_frontmatter

FONTS_DIR = Path(__file__).parent / "fonts"
# (fpdf2 style code, bundled TTF) — all four styles registered so write_html can render bold
# headings and italic emphasis with real Unicode glyphs (a Unicode font needs each variant).
_DEJAVU = (
    ("", "DejaVuSans.ttf"),
    ("b", "DejaVuSans-Bold.ttf"),
    ("i", "DejaVuSans-Oblique.ttf"),
    ("bi", "DejaVuSans-BoldOblique.ttf"),
)

# fpdf2 write_html's usable subset for a single-column CV/letter (fpdf2 docs: HTML.md). Every other
# tag is dropped with its inner text kept; <a href> stays so portfolio/GitHub links survive.
_ALLOWED = frozenset(
    {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "ul",
        "ol",
        "li",
        "b",
        "i",
        "u",
        "hr",
        "blockquote",
        "br",
        "a",
    }
)
# markdown-it emits <strong>/<em>; write_html only styles <b>/<i>.
_REMAP = {"strong": "b", "em": "i"}
_TAG = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)(?:\s[^>]*)?/?>")

# Heading point sizes matching fpdf2 write_html's defaults; we keep the size hierarchy but recolor
# to black — fpdf2 defaults headings to dark red (150,0,0), unprofessional on a submitted CV.
_HEADING_PT = {"h1": 24, "h2": 18, "h3": 14, "h4": 12, "h5": 10, "h6": 8}


def _normalize_html(html: str) -> str:
    """Reduce markdown-it HTML to fpdf2 ``write_html``'s supported tag subset.

    Remaps ``<strong>``/``<em>`` to ``<b>``/``<i>``, keeps the tags in :data:`_ALLOWED`
    (``<a href>`` included, with its attributes), and drops every other tag while preserving its
    inner text. HTML entities are left untouched.

    Args:
        html: HTML as emitted by ``markdown_it.MarkdownIt().render``.

    Returns:
        HTML using only tags ``write_html`` renders.
    """

    def _sub(m: re.Match[str]) -> str:
        name = m.group(1).lower()
        mapped = _REMAP.get(name)
        if mapped is not None:
            return f"</{mapped}>" if m.group(0).startswith("</") else f"<{mapped}>"
        return m.group(0) if name in _ALLOWED else ""

    return _TAG.sub(_sub, html)


def render_pdf(md: str, out: Path) -> None:
    """Render a tailored markdown document to a single-column, ATS-safe PDF at ``out``.

    Strips the persist-offer title frontmatter, converts markdown→HTML (markdown-it), reduces it to
    fpdf2's tag subset (:func:`_normalize_html`), and writes a real-text PDF using the bundled
    DejaVu Unicode font. The document's own H1 (the candidate's name) is its visible title.

    Args:
        md: The tailored markdown (with or without the persist-offer title frontmatter).
        out: Destination ``.pdf`` path.

    Raises:
        ImportError: If the ``pdf`` extra (fpdf2 + markdown-it-py) is not installed.
    """
    from fpdf import FPDF, FontFace  # lazy: keep module importable without the [pdf] extra
    from markdown_it import MarkdownIt  # lazy: same

    html = _normalize_html(MarkdownIt().render(strip_frontmatter(md)))
    pdf = FPDF()
    pdf.add_page()
    for style, fname in _DEJAVU:
        pdf.add_font("dejavu-sans", style=style, fname=str(FONTS_DIR / fname))
    pdf.set_font("dejavu-sans", size=11)
    headings = {tag: FontFace(color=(0, 0, 0), size_pt=pt) for tag, pt in _HEADING_PT.items()}
    # Recolor fpdf2's dark-red defaults to black (headings + list bullets) for a professional CV.
    pdf.write_html(html, tag_styles=headings, li_prefix_color=(0, 0, 0))
    pdf.output(str(out))


def main(src: Path | None = None, out: Path | None = None) -> None:
    """Render a tailored markdown file to a PDF; reads args from argv when called directly.

    Args:
        src: Path to the tailored markdown (defaults to the first CLI arg).
        out: Destination PDF (defaults to ``src`` with a ``.pdf`` suffix).
    """
    if src is None:
        parser = argparse.ArgumentParser(prog="ajoa-kit render-pdf")
        parser.add_argument("file", metavar="FILE", help="Path to a tailored markdown file.")
        parser.add_argument("--out", default="", help="Output PDF path (default: <file>.pdf).")
        ns = parser.parse_args()
        src = Path(ns.file)
        out = Path(ns.out) if ns.out else None
    out = out or src.with_suffix(".pdf")
    try:
        render_pdf(src.read_text(), out)
    except ImportError:
        print(
            "PDF export needs the [pdf] extra — run `uv sync --extra pdf` "
            "(or `pip install 'ajoa-kit[pdf]'`).",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"wrote PDF -> {out}")


if __name__ == "__main__":
    main()
