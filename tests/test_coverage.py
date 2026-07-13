"""Value-add tests for the JD must-have coverage summary (``coverage``).

Cover the sharp edges: pipe/newline sanitization so a cell can't break the table,
None/missing-key tolerance, the empty-list placeholder, and the gap-report append —
plus a property test that the summary never raises and emits exactly one row per
must-have for arbitrary (messy) input.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit.coverage import coverage_summary


def test_renders_one_row_per_must_have_with_covered_evidence_and_resources() -> None:
    must_haves = [
        {"requirement": "5y Python", "covered": True, "evidence": "ML platform at Acme"},
        {
            "requirement": "Kubernetes",
            "covered": False,
            "evidence": None,
            "resources": ["CKA course", "k8s.io docs"],
        },
    ]
    out = coverage_summary(must_haves, "Production on-call is the main gap.")
    assert "| Must-have | covered/gap | Evidence | Resources |" in out
    # covered must-have carries no upskilling pointers -> placeholder
    assert "| 5y Python | covered | ML platform at Acme | — |" in out
    # uncovered must-have shows the (grounded, generic) learning pointers
    assert "| Kubernetes | gap | — | CKA course; k8s.io docs |" in out
    assert "Production on-call is the main gap." in out  # gap_report appended


def test_missing_or_empty_resources_render_as_placeholder() -> None:
    must_haves = [
        {"requirement": "Go", "covered": False, "evidence": None},  # key absent
        {"requirement": "Rust", "covered": False, "evidence": None, "resources": None},
        {"requirement": "SQL", "covered": False, "evidence": None, "resources": []},
    ]
    out = coverage_summary(must_haves, "")
    for req in ("Go", "Rust", "SQL"):
        assert f"| {req} | gap | — | — |" in out


def test_resource_cells_are_sanitized_and_joined() -> None:
    must_haves = [
        {
            "requirement": "X",
            "covered": False,
            "evidence": None,
            "resources": ["a | b", "line1\nline2"],
        }
    ]
    out = coverage_summary(must_haves, "")
    assert "| X | gap | — | a \\| b; line1 line2 |" in out  # pipes escaped, newline collapsed


def test_sanitizes_pipes_and_newlines_so_cells_cannot_break_the_table() -> None:
    must_haves = [{"requirement": "A | B", "covered": True, "evidence": "line1\nline2"}]
    out = coverage_summary(must_haves, "")
    assert "A \\| B" in out  # literal pipe escaped
    assert "line1 line2" in out  # newline collapsed
    rows = [ln for ln in out.splitlines() if ln.startswith("| ")]
    assert len(rows) == 3  # header + separator + exactly one data row


def test_empty_must_haves_is_a_placeholder_not_a_table() -> None:
    out = coverage_summary([], "")
    assert "No must-have requirements identified" in out
    assert "| --- |" not in out  # no table emitted


_VALUES = st.one_of(st.none(), st.text(), st.booleans(), st.integers(), st.lists(st.text()))
_ITEM = st.dictionaries(
    keys=st.sampled_from(["requirement", "covered", "evidence", "resources", "extra"]),
    values=_VALUES,
)


class TestCoverageProperties:
    # Reason: pure string-building over generated input; deadline off so coverage
    # instrumentation timing cannot flake the property.
    @given(must_haves=st.lists(_ITEM), gap_report=st.text())
    @settings(deadline=None)
    def test_never_raises_on_arbitrary_input(self, must_haves: list[dict], gap_report: str) -> None:
        coverage_summary(must_haves, gap_report)

    @given(must_haves=st.lists(_ITEM))
    @settings(deadline=None)
    def test_one_table_row_per_must_have(self, must_haves: list[dict]) -> None:
        out = coverage_summary(must_haves, "")
        rows = [ln for ln in out.splitlines() if ln.startswith("| ")]
        expected = len(must_haves) + 2 if must_haves else 0  # header + separator + N
        assert len(rows) == expected
