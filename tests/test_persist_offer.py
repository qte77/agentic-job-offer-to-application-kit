"""Value-add tests for the Stage-3 offer-pack writer (``persist_offer``).

Cover the sharp edges only: slug path-traversal confinement (the slug originates in
third-party JD data), all-or-nothing writes on an incomplete pack, and results-root
resolution via ``AppSettings`` / ``AJOA_RESULTS_DIR`` — not trivial getters.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
    assert (offer_dir / "match.md").read_text().startswith('---\ntitle: "Match assessment"\n---')


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
    assert report.startswith('---\ntitle: "Coverage report"\n---')
    assert "| Python | covered | Acme |" in report


def test_write_pack_flags_unsafe_cv_without_failing(tmp_path: Path) -> None:
    # A parse-unsafe CV (markdown table) must surface a cv-ats-check.md for human review (#75),
    # but never block the pack — it's a review aid, not a gate. A clean CV writes no such file
    # (covered by test_write_pack_emits_one_md_per_artifact, whose PACK cv is clean).
    unsafe = {**PACK, "cv": "## Experience\n\n| Role | Years |\n|---|---|\n| Eng | 5 |\n"}
    offer_dir = persist_offer.write_pack(unsafe, slug="acme-ai-101", results_dir=tmp_path)
    names = sorted(p.name for p in offer_dir.glob("*.md"))
    assert "cv-ats-check.md" in names
    assert "cv.md" in names  # the full pack still wrote — non-blocking
    assert "table" in (offer_dir / "cv-ats-check.md").read_text().lower()


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


def test_write_pack_writes_meta_json_when_id_present(tmp_path: Path) -> None:
    # The offer dir is named by the (possibly custom) slug, but the local dashboard joins packs to
    # shortlist rows by JD id — so persist_offer records {id, slug} in meta.json (#209).
    offer_dir = persist_offer.write_pack(
        {**PACK, "offer_id": "ashby:acme-ai:101"}, slug="pretty-name", results_dir=tmp_path
    )
    assert json.loads((offer_dir / "meta.json").read_text()) == {
        "id": "ashby:acme-ai:101",
        "slug": "pretty-name",
    }


def test_write_pack_no_meta_json_without_id(tmp_path: Path) -> None:
    # A pack with no id (older/canned) can't be joined — no meta.json; the artifacts still write.
    offer_dir = persist_offer.write_pack(PACK, slug="acme-ai-101", results_dir=tmp_path)
    assert not (offer_dir / "meta.json").exists()
    assert (offer_dir / "cv.md").is_file()


def test_attach_tailor_docs_joins_cv_by_id(tmp_path: Path) -> None:
    # A tailored pack (with id) attaches its *stripped* cv/cover-letter bodies onto the matching
    # shortlist row (by JD id, not slug); a row with no pack is left without cv/cover_letter (#209).
    persist_offer.write_pack(
        {**PACK, "offer_id": "ashby:acme-ai:101"}, slug="pretty-name", results_dir=tmp_path
    )
    rows = [
        {"id": "ashby:acme-ai:101", "title": "AI Engineer"},
        {"id": "greenhouse:globex:7", "title": "Platform Engineer"},  # no pack on disk
    ]
    out = persist_offer.attach_tailor_docs(rows, results_dir=tmp_path)
    assert out[0]["cv"].startswith("## Summary")  # frontmatter stripped, body attached
    assert "Dear hiring team" in out[0]["cover_letter"]
    assert "cv" not in out[1]  # unmatched row untouched
    assert "cover_letter" not in out[1]


class TestSafeSlugProperties:
    _SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    # Reason: pure sanitizer over arbitrary text; deadline off. Security: path confinement.
    @given(raw=st.text())
    @settings(deadline=None)
    def test_slug_is_confined_or_raises(self, raw: str) -> None:
        try:
            out = persist_offer.safe_slug(raw)
        except ValueError:
            return  # empty-after-sanitize is the documented failure mode
        assert self._SLUG.fullmatch(out)  # only [a-z0-9-]; no '/', '..', or edge/double dash
