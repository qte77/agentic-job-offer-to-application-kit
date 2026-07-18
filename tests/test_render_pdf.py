"""Value-add tests for ``render-pdf`` (issue #275).

The pure ``_normalize_html`` cases pin one transformation each — the sharp edges (tag remap, drop
with text kept, link survival, entity safety). A final guarded smoke test pins the render *glue*:
that a real accented / bold / italic / linked document renders to a valid PDF without raising (it
skips when the ``pdf`` extra is absent, so the pure cases still run offline — importing this module
never needs fpdf2/markdown-it, they are lazy inside ``render_pdf``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ajoa_kit import render_pdf

if TYPE_CHECKING:
    from pathlib import Path


def test_strong_and_em_are_remapped_to_b_and_i() -> None:
    # markdown-it emits <strong>/<em>; fpdf2 write_html only styles <b>/<i>.
    out = render_pdf._normalize_html("<p><strong>bold</strong> and <em>it</em></p>")
    assert "<b>bold</b>" in out
    assert "<i>it</i>" in out
    assert "strong" not in out
    assert "<em>" not in out


def test_unsupported_tags_are_dropped_but_inner_text_is_kept() -> None:
    # <code>/<pre>/<table> are outside write_html's usable subset — the markup goes, the text stays.
    inline = render_pdf._normalize_html("<p>run <code>ruff</code> first</p>")
    assert "ruff" in inline
    assert "<code>" not in inline
    table = render_pdf._normalize_html("<table><tr><td>Alice</td></tr></table>")
    assert "Alice" in table
    assert "<table" not in table
    assert "<td>" not in table


def test_links_keep_their_href() -> None:
    # Refinement: fpdf2 renders <a href>; portfolio/GitHub links must survive as real links.
    out = render_pdf._normalize_html('<p>see <a href="https://github.com/me">GitHub</a></p>')
    assert '<a href="https://github.com/me">GitHub</a>' in out


def test_supported_structure_is_preserved() -> None:
    out = render_pdf._normalize_html("<h2>Experience</h2><ul><li>Built it</li></ul><hr>")
    assert "<h2>Experience</h2>" in out
    assert "<li>Built it</li>" in out
    assert "<hr>" in out


def test_html_entities_are_left_untouched() -> None:
    # The normaliser only strips tags — entities must reach write_html intact, not be mangled.
    out = render_pdf._normalize_html("<p>Tom &amp; Jerry &lt;3</p>")
    assert "&amp;" in out
    assert "&lt;" in out


def test_render_pdf_produces_a_valid_pdf(tmp_path: Path) -> None:
    # Glue smoke (skips without the [pdf] extra). Covers the silent-regression surface: frontmatter
    # strip, an accented H1 (Unicode-font path — the spike's one gap), bold/italic, a link. A broken
    # font path or write_html signature would raise; a valid PDF starts with the %PDF- magic bytes.
    pytest.importorskip("fpdf")
    pytest.importorskip("markdown_it")
    md = (
        '---\ntitle: "Tailored CV"\n---\n\n'
        "# José Müller\n\n## Summary\n**Infra** and *DX* — see [GitHub](https://github.com/me).\n"
    )
    out = tmp_path / "cv.pdf"
    render_pdf.render_pdf(md, out)
    data = out.read_bytes()
    assert data.startswith(b"%PDF-")
    assert len(data) > 1024  # embedded DejaVu ⇒ a real PDF is comfortably over 1 KB
