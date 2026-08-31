"""Value-add tests for the deterministic CV-grounding check (``grounding``).

Mirrors ``test_stuffing.py``: pure, heuristic, non-blocking review aid. Only *distinctive*
numbers (decimal, %, x-multiplier, comma-grouped, or 4+ digits) are checked — bare 1-3 digit
integers are too noisy and are skipped even though it costs recall.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit.grounding import grounding_warnings

LIBRARY = {
    "headline": "Shipped 2.3x faster inference across 4,813,103 variants.",
    "positioningSummary": "Validated at SNP F1 0.9961.",
    "skillClusters": [{"cluster": "ML", "bullets": ["INT8 quantization, 21 MB image"]}],
    "masterCvBullets": ["94 benchmarking runs consolidated into one leaderboard."],
    "perProject": [{"project": "X", "bullets": ["1,561 test functions across 141 files"]}],
    "mlAngle": "Applied ML depth without foundational research.",
}


def test_flags_a_distinctive_number_absent_from_the_library() -> None:
    cv = "## Summary\nDelivered a 5.7x speedup on the training loop.\n"
    out = grounding_warnings(cv, LIBRARY)
    assert len(out) == 1
    assert "5.7x" in out[0]


def test_does_not_flag_a_number_present_in_the_library() -> None:
    cv = "## Summary\nShipped 2.3x faster inference.\n"
    assert grounding_warnings(cv, LIBRARY) == []


def test_does_not_flag_a_library_number_reformatted_in_the_cv() -> None:
    # Same value, different formatting (no comma) — normalized comparison should still match.
    cv = "## Summary\nValidated against 4813103 variants.\n"
    assert grounding_warnings(cv, LIBRARY) == []


def test_ignores_bare_short_integers() -> None:
    # 1-3 digit bare integers are noise (list counts, small tallies) — never flagged.
    cv = "## Summary\nLed a 3-tier evaluation framework across 24 repos.\n"
    assert grounding_warnings(cv, LIBRARY) == []


def test_flags_a_percentage_not_grounded_in_the_library() -> None:
    cv = "## Summary\nCut latency by 47%.\n"
    out = grounding_warnings(cv, LIBRARY)
    assert any("47%" in w for w in out)


def test_deduplicates_the_same_unverified_number_repeated_in_the_cv() -> None:
    cv = "## Summary\nA 5.7x speedup. Later, another 5.7x speedup mentioned again.\n"
    out = grounding_warnings(cv, LIBRARY)
    assert len(out) == 1


def test_matches_a_number_nested_anywhere_in_the_library_structure() -> None:
    # skillClusters/masterCvBullets/perProject are nested — the check must reach into them, not
    # just the two top-level string fields.
    cv = "## Summary\n94 runs consolidated into one leaderboard.\n"
    assert grounding_warnings(cv, LIBRARY) == []


def test_ignores_a_bare_year() -> None:
    cv = "## Summary\nPublic commit history since 2019.\n"
    assert grounding_warnings(cv, LIBRARY) == []


def test_ignores_an_id_prefixed_by_hyphen_or_hash() -> None:
    cv = "## Summary\nSee ADR-0000 and issue #4021 for details.\n"
    assert grounding_warnings(cv, LIBRARY) == []


def test_still_flags_a_percentage_shaped_like_a_year() -> None:
    # The year exclusion only applies to a BARE 4-digit run — a % marker still counts.
    cv = "## Summary\nImproved throughput by 1900%.\n"
    out = grounding_warnings(cv, LIBRARY)
    assert any("1900%" in w for w in out)


def test_empty_cv_or_non_dict_library_is_silent_not_a_crash() -> None:
    assert grounding_warnings("", LIBRARY) == []
    assert grounding_warnings("5.7x speedup", {}) == []
    assert grounding_warnings("5.7x speedup", None) == []  # type: ignore[arg-type]


class TestGroundingProperties:
    # Reason: pure text scan over generated input; deadline off so instrumentation timing
    # cannot flake the property.
    @given(cv_md=st.text(), library=st.dictionaries(st.text(), st.text()))
    @settings(deadline=None)
    def test_never_raises_on_arbitrary_input(self, cv_md: str, library: dict) -> None:
        grounding_warnings(cv_md, library)
