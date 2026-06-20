"""Value-add tests for the deterministic résumé parse-safety checker (``ats_check``).

Each case pins one ATS-hostile markdown construct the checker must flag (or, for the clean
CV, must not) — the sharp edges, not trivial getters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit import ats_check

if TYPE_CHECKING:
    from pathlib import Path

CLEAN_CV = (
    "# Jane Doe\n\n## Summary\nInfra-first engineer.\n\n"
    "## Experience\n- Built a pipeline.\n\n## Skills\n- Python\n"
)


def test_clean_cv_is_safe() -> None:
    assert ats_check.parse_safety_warnings(CLEAN_CV) == []


def test_table_is_flagged() -> None:
    cv = "## Experience\n\n| Role | Years |\n|---|---|\n| Eng | 5 |\n"
    assert any("table" in w.lower() for w in ats_check.parse_safety_warnings(cv))


def test_thematic_break_is_not_a_table() -> None:
    # `---` section separators / Setext underlines are not GFM tables (a delimiter row always
    # has a pipe). The tailor CV agent emits `---` separators, so these must not trip the gate.
    cv = "## Summary\nInfra-first engineer.\n\n---\n\n## Experience\n- Built an engine.\n"
    assert ats_check.parse_safety_warnings(cv) == []


def test_raw_html_is_flagged_but_autolink_is_not() -> None:
    flagged = ats_check.parse_safety_warnings("## Skills\n<div>x</div>")
    assert any("html" in w.lower() for w in flagged)
    # a markdown autolink is not a tag and must not trip the HTML check
    autolink = "## Summary\nSee <https://example.com>.\n\n## Experience\n- x"
    assert ats_check.parse_safety_warnings(autolink) == []


def test_image_is_flagged() -> None:
    cv = "# Jane\n\n## Summary\n![headshot](me.png)\n\n## Experience\n- x"
    assert any("image" in w.lower() for w in ats_check.parse_safety_warnings(cv))


def test_hidden_comment_is_flagged() -> None:
    cv = "## Summary\nx\n\n## Experience\n<!-- python java rust kubernetes -->\n- x"
    assert any("hidden" in w.lower() for w in ats_check.parse_safety_warnings(cv))


def test_missing_section_headings_is_flagged() -> None:
    cv = "# Jane Doe\n\nA short biography paragraph about the candidate.\n"
    assert any("heading" in w.lower() for w in ats_check.parse_safety_warnings(cv))


def test_main_exits_nonzero_on_unsafe_cv(tmp_path: Path) -> None:
    cv = tmp_path / "cv.md"
    cv.write_text("## Experience\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    with pytest.raises(SystemExit) as exc:
        ats_check.main(src=cv)
    assert exc.value.code == 1


def test_main_passes_clean_cv(tmp_path: Path) -> None:
    cv = tmp_path / "cv.md"
    cv.write_text(CLEAN_CV)
    ats_check.main(src=cv)  # no SystemExit


class TestParseSafetyProperties:
    # Reason: pure detector over arbitrary text; deadline off.
    @given(a=st.text(), b=st.text())
    @settings(deadline=None)
    def test_positive_warnings_monotone_under_concatenation(self, a: str, b: str) -> None:
        def positives(s: str) -> set[str]:
            # the absence-of-headings warning is anti-monotone by design; exclude it
            return {w for w in ats_check.parse_safety_warnings(s) if "heading" not in w.lower()}

        combined = positives(a + b)
        assert positives(a) <= combined  # a flagged issue never vanishes when text is appended
        assert positives(b) <= combined
