"""Value-add tests for ``html_to_text``: the angle-bracket-in-attribute bug + invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit import defaults, normalize


def test_strips_tag_with_angle_bracket_in_attribute() -> None:
    # a '>' inside a quoted attribute value must not end the tag early (the greedy <[^>]+> bug)
    out = normalize.html_to_text('<a title="x>y" href="z">click</a>')
    assert out == "click"


def test_strips_script_and_style_blocks_with_content() -> None:
    # analytics/CSS must never leak into JD text; the '>' in the script body must not end it early
    html = "<style>.x{color:red}</style><p>Real JD</p><script>track('a>b');</script>"
    assert normalize.html_to_text(html) == "Real JD"


def test_keeps_the_whole_posting_for_tailoring() -> None:
    """Ingest stores the full JD; ``DESC_CAP`` belongs to the relevance pass instead (#347).

    The cap used to be applied here, and 80% of ingested JDs hit it (4632 of 5773, median length
    exactly 4000). The tailor pass reads the same record, so most application packs were grounded
    in a partial posting — the requirements past 4000 chars were simply gone.
    """
    body = "z" * (defaults.DESC_CAP + 500)
    assert normalize.html_to_text(f"<p>{body}</p>") == body


class TestHtmlToTextProperties:
    # Reason: pure text transform over arbitrary (possibly malformed) input; deadline off.
    @given(s=st.one_of(st.none(), st.text()))
    @settings(deadline=None)
    def test_never_raises_and_collapses_whitespace(self, s: str | None) -> None:
        out = normalize.html_to_text(s)
        assert isinstance(out, str)
        assert out == out.strip()  # leading/trailing whitespace always collapsed away
