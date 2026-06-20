"""Value-add tests for ``html_to_text``: the angle-bracket-in-attribute bug + invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit import ingest


def test_strips_tag_with_angle_bracket_in_attribute() -> None:
    # a '>' inside a quoted attribute value must not end the tag early (the greedy <[^>]+> bug)
    out = ingest.html_to_text('<a title="x>y" href="z">click</a>')
    assert out == "click"


class TestHtmlToTextProperties:
    # Reason: pure text transform over arbitrary (possibly malformed) input; deadline off.
    @given(s=st.one_of(st.none(), st.text()))
    @settings(deadline=None)
    def test_never_raises_and_caps_length(self, s: str | None) -> None:
        out = ingest.html_to_text(s)
        assert isinstance(out, str)
        assert len(out) <= ingest.DESC_CAP
