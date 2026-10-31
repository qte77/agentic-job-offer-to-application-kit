"""Value-add tests for the offer-pack drift check (#366).

Pin the issue's three done-when cases (hand-edited artifact, stale source, no source) plus the two
edges from the 2026-10-19 comment: review sidecars are not a pure function of ``result.json``, so
they never count as drift, and the check never writes to or deletes from a pack.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit import drift, persist_offer

if TYPE_CHECKING:
    from pathlib import Path

PACK = {
    "match": "Strong overlap on agentic LLM workflows.",
    "cv": "## Summary\nInfrastructure-first AI engineer.",
    "cover_letter": "Dear hiring team, I am excited to apply...",
    "gap_report": "Gap: production-at-scale ops.",
    "prefill_pack": "First name: Alexis\n(Human reviews + submits.)",
    "must_haves": [{"requirement": "Python", "covered": True, "evidence": "Acme"}],
}


def _persist(results: Path, slug: str = "acme") -> Path:
    return persist_offer.write_pack(dict(PACK), slug=slug, results_dir=results)


def test_freshly_persisted_pack_is_clean(tmp_path: Path) -> None:
    _persist(tmp_path)
    assert drift.check_offers(tmp_path) == [drift.PackDrift(slug="acme", status="clean")]


def test_hand_edited_artifact_is_drifted_and_named(tmp_path: Path) -> None:
    offer = _persist(tmp_path)
    letter = offer / "cover-letter.md"
    letter.write_text(letter.read_text().replace("excited", "thrilled"))
    [report] = drift.check_offers(tmp_path)
    assert report.status == "drifted"
    assert report.files == ["cover-letter.md"]


def test_source_changed_without_repersist_is_drifted(tmp_path: Path) -> None:
    offer = _persist(tmp_path)
    source = json.loads((offer / "result.json").read_text())
    source["cv"] = "## Summary\nRewritten summary."
    source["must_haves"] = []  # coverage-report.md no longer applies
    (offer / "result.json").write_text(json.dumps(source))
    [report] = drift.check_offers(tmp_path)
    assert report.status == "drifted"
    assert report.files == ["coverage-report.md", "cv.md"]


def test_pack_without_result_json_is_no_source_and_does_not_fail(tmp_path: Path) -> None:
    offer = _persist(tmp_path, slug="legacy")
    (offer / "result.json").unlink()
    _persist(tmp_path, slug="fresh")
    reports = drift.check_offers(tmp_path)
    assert [(r.slug, r.status) for r in reports] == [("fresh", "clean"), ("legacy", "no source")]
    assert drift.main(results_dir=tmp_path) == 0


def test_sidecars_are_ignored_and_the_pack_is_left_untouched(tmp_path: Path) -> None:
    offer = _persist(tmp_path)
    (offer / "cv-ats-check.md").write_text("stale sidecar a re-render would not produce")
    (offer / "cover-letter.md").write_text("hand edit")
    before = {p.name: p.read_text() for p in offer.iterdir()}
    [report] = drift.check_offers(tmp_path)
    assert report.files == ["cover-letter.md"]
    assert {p.name: p.read_text() for p in offer.iterdir()} == before
    assert drift.main(results_dir=tmp_path) == 1


def test_unrenderable_source_is_reported_not_raised(tmp_path: Path) -> None:
    offer = _persist(tmp_path)
    (offer / "result.json").write_text(json.dumps({"match": "only one field"}))
    [report] = drift.check_offers(tmp_path)
    assert report.status == "invalid source"
