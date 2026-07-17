"""Value-add tests for the pure HTML normaliser behind ``render-pdf`` (issue #275).

``_normalize_html`` reduces markdown-it's HTML to the tag subset fpdf2's ``write_html`` renders.
Each case pins one transformation the renderer depends on — the sharp edges (tag remap, drop with
text kept, link survival, entity safety), not the glue (that is verified live against a real PDF).
The module imports without the ``pdf`` extra (fpdf2/markdown-it are lazy), so importing it here
never needs those deps.
"""

from __future__ import annotations

from ajoa_kit import render_pdf


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
