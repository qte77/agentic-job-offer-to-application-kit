"""Value-add tests for the Stage-3 offer-pack writer (``persist_offer``).

Cover the sharp edges only: slug path-traversal confinement (the slug originates in
third-party JD data), all-or-nothing writes on an incomplete pack, and results-root
resolution via ``AppSettings`` / ``AJOA_RESULTS_DIR`` — not trivial getters.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import persist_offer

if TYPE_CHECKING:
    from pathlib import Path

PACK = {
    "match": "Strong overlap on agentic LLM workflows, retrieval, and Python ownership.",
    "cv": "## Summary\nInfrastructure-first AI engineer.\n\n## Experience\n- Built an engine.",
    "cover_letter": "Dear hiring team, I am excited to apply...",
    "gap_report": "Gap: production-at-scale ops and on-call rotations.",
    "prefill_pack": "First name: Alexis\nEmail: alexis@example.com\n(Human reviews + submits.)",
}


def test_safe_slug_confines_traversal_and_separators() -> None:
    out = persist_offer.safe_slug("../../etc/passwd")
    assert "/" not in out
    assert ".." not in out
    assert persist_offer.safe_slug("ashby:acme-ai:101") == "ashby-acme-ai-101"


def test_safe_slug_rejects_empty_after_sanitizing() -> None:
    for bad in ["", "..", "///", "  "]:
        with pytest.raises(ValueError, match="slug"):
            persist_offer.safe_slug(bad)


def test_write_pack_emits_one_md_per_artifact(tmp_path: Path) -> None:
    offer_dir = persist_offer.write_pack(PACK, slug="acme-ai-101", results_dir=tmp_path)
    assert offer_dir == tmp_path / "offers" / "acme-ai-101"
    names = sorted(p.name for p in offer_dir.glob("*.md"))
    assert names == ["cover-letter.md", "cv.md", "gap-report.md", "match.md", "prefill-pack.md"]
    assert "Dear hiring team" in (offer_dir / "cover-letter.md").read_text()
    assert (offer_dir / "match.md").read_text().startswith("# ")  # rendered heading


def test_write_pack_emits_coverage_report_only_with_must_haves(tmp_path: Path) -> None:
    pack = {
        **PACK,
        "must_haves": [{"requirement": "Python", "covered": True, "evidence": "Acme"}],
    }
    offer_dir = persist_offer.write_pack(pack, slug="acme-ai-101", results_dir=tmp_path)
    names = sorted(p.name for p in offer_dir.glob("*.md"))
    assert "coverage-report.md" in names
    assert len(names) == 6  # the 5 core artifacts + the optional coverage report
    report = (offer_dir / "coverage-report.md").read_text()
    assert report.startswith("# Coverage report")
    assert "| Python | covered | Acme |" in report


def test_write_pack_incomplete_writes_nothing(tmp_path: Path) -> None:
    incomplete = {k: v for k, v in PACK.items() if k != "cover_letter"}
    with pytest.raises(ValueError, match="cover_letter"):
        persist_offer.write_pack(incomplete, slug="acme-ai-101", results_dir=tmp_path)
    assert not (tmp_path / "offers").exists()  # validated before any write


def test_write_pack_never_escapes_results_dir(tmp_path: Path) -> None:
    offer_dir = persist_offer.write_pack(PACK, slug="../../escape", results_dir=tmp_path)
    assert tmp_path in offer_dir.parents


def test_main_honors_results_dir_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "pack.json"
    # the Workflow tool wraps the script return value under "result"
    src.write_text(json.dumps({"result": {**PACK, "slug": "acme-ai-101"}}))
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(tmp_path / "ws"))
    persist_offer.main(src=src)
    assert (tmp_path / "ws" / "offers" / "acme-ai-101" / "match.md").exists()
