"""Value-add tests for writing-style resolution (``style``, #16).

Cover the real decision logic and sharp edges only: the sample-over-tone-over-neutral
precedence (per artifact), fail-loud on a referenced-but-missing sample, and the sample
length cap. No getter/shape trivia.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit import style

if TYPE_CHECKING:
    from pathlib import Path


def test_tone_only_applies_to_both_artifacts(tmp_path: Path) -> None:
    (tmp_path / "style.json").write_text(json.dumps({"tone": "Direct and understated."}))
    brief = style.load_style(tmp_path)
    assert "Direct and understated." in style.directive(brief, "cv")
    assert "Direct and understated." in style.directive(brief, "cover_letter")


def test_sample_overrides_tone_for_its_artifact_only(tmp_path: Path) -> None:
    (tmp_path / "style").mkdir()
    (tmp_path / "style" / "cv.md").write_text("UNIQUE_CV_VOICE marker")
    (tmp_path / "style.json").write_text(
        json.dumps({"tone": "Formal.", "cv_sample": "style/cv.md"})
    )
    brief = style.load_style(tmp_path)
    assert "UNIQUE_CV_VOICE" in style.directive(brief, "cv")  # sample wins for cv
    assert "Formal." in style.directive(brief, "cover_letter")  # no cover sample → tone


def test_no_config_is_neutral(tmp_path: Path) -> None:
    brief = style.load_style(tmp_path)
    assert style.directive(brief, "cv") == ""
    assert style.directive(brief, "cover_letter") == ""


def test_missing_referenced_sample_raises_loud(tmp_path: Path) -> None:
    (tmp_path / "style.json").write_text(json.dumps({"cv_sample": "style/missing.md"}))
    with pytest.raises(FileNotFoundError, match=r"missing\.md"):
        style.load_style(tmp_path)


def test_sample_text_is_capped(tmp_path: Path) -> None:
    (tmp_path / "style").mkdir()
    (tmp_path / "style" / "cv.md").write_text("x" * (style.SAMPLE_CAP + 500))
    (tmp_path / "style.json").write_text(json.dumps({"cv_sample": "style/cv.md"}))
    brief = style.load_style(tmp_path)
    assert len(brief.cv_sample) == style.SAMPLE_CAP


class TestDirectiveProperties:
    # Reason: pure precedence logic over generated briefs; deadline off.
    @given(
        tone=st.text(),
        cv=st.text(),
        cover=st.text(),
        kind=st.sampled_from(["cv", "cover_letter"]),
    )
    @settings(deadline=None)
    def test_precedence_sample_over_tone_over_neutral(
        self, tone: str, cv: str, cover: str, kind: str
    ) -> None:
        brief = style.StyleBrief(tone=tone, cv_sample=cv, cover_letter_sample=cover)
        out = style.directive(brief, kind)
        assert isinstance(out, str)
        sample = cv if kind == "cv" else cover
        if sample:
            assert sample in out  # a sample wins for its artifact
        elif tone:
            assert tone in out  # else the tone applies
        else:
            assert out == ""  # neutral when nothing configured
