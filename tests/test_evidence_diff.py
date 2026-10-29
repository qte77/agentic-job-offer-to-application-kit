"""Value-add tests for evidence-library drift detection (#414).

Pin the two halves: a pack records which library version it was tailored against (so a later
rebuild is visible), and ``evidence-diff`` names the top-level fields a rebuild changed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit import evidence_diff, persist_offer
from ajoa_kit.models import OfferMeta

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

PACK = {
    "id": "ashby:acme:1",
    "match": "Strong overlap.",
    "cv": "## Summary\nEngineer.",
    "cover_letter": "Dear team.",
    "gap_report": "Gap: ops.",
    "prefill_pack": "First name: Alexis",
}


def _meta(results: Path) -> OfferMeta:
    offer = persist_offer.write_pack(dict(PACK), slug="acme", results_dir=results)
    return OfferMeta.model_validate_json((offer / "meta.json").read_text())


def test_pack_records_the_library_stamp_and_a_rebuild_changes_it(tmp_path: Path) -> None:
    library = tmp_path / "evidence-library.json"
    library.write_text(json.dumps({"gapNarrative": "no database work"}))
    first = _meta(tmp_path).evidence_library
    assert first == evidence_diff.library_stamp(library)
    library.write_text(json.dumps({"gapNarrative": "no message-queue work"}))
    assert _meta(tmp_path).evidence_library not in ("", first)


def test_pack_without_a_library_records_an_empty_stamp(tmp_path: Path) -> None:
    assert _meta(tmp_path).evidence_library == ""


def test_diff_names_added_removed_and_changed_top_level_fields() -> None:
    old = {"headline": "same", "gapNarrative": "db framing", "mlAngle": "x", "skills": ["a"]}
    new = {"headline": "same", "gapNarrative": "reworded", "opsAngle": "y", "skills": ["a", "b"]}
    assert evidence_diff.diff_fields(old, new) == {
        "added": ["opsAngle"],
        "removed": ["mlAngle"],
        "changed": ["gapNarrative", "skills"],
    }


def test_cli_reports_both_stamps_and_the_changed_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    old.write_text(json.dumps({"headline": "h", "gapNarrative": "a"}))
    new.write_text(json.dumps({"headline": "h", "gapNarrative": "b"}))
    evidence_diff.main(old, new)
    out = capsys.readouterr().out
    assert evidence_diff.library_stamp(old) in out
    assert evidence_diff.library_stamp(new) in out
    assert "changed: gapNarrative" in out
    assert "headline" not in out
