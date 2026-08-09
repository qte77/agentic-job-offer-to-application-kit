"""Manual-JD durability across a re-ingest (arc 010 item 4).

`ingest.main` rewrites `results/jobs-raw.json` wholesale from the pull, so hand-captured JDs — the
ones whose packs are grounded in them — vanished on the next run. They now come from
`config/manual-jds.json` and are injected into every pull, which is also what keeps `merge_corpus`
from delisting them.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit.corpus import merge_corpus
from ajoa_kit.ingest import load_manual_jds, with_manual
from ajoa_kit.normalize import record

if TYPE_CHECKING:
    from pathlib import Path

ENTRY = {
    "id": "manual:acme:founding-engineer",
    "title": "Founding Engineer",
    "company": "Acme",
    "companySlug": "acme",
    "location": "Zurich, CH",
    "url": "https://acme.example/careers",
    "description": "Build the thing.",
    "laneHint": "founding",
    "remote": False,
}


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    (tmp_path / "manual-jds.json").write_text(json.dumps(entries))
    return tmp_path


@pytest.fixture
def manual(tmp_path: Path) -> list[dict]:
    """The loader's real output for ENTRY — so the merge tests exercise the shipped mapping."""
    return load_manual_jds(_write(tmp_path, [ENTRY]))


def test_absent_config_is_inert(tmp_path: Path) -> None:
    """A fresh clone has no manual JDs and must ingest exactly as before."""
    assert load_manual_jds(tmp_path) == []


def test_loaded_entry_gets_the_full_record_shape(tmp_path: Path) -> None:
    (rec,) = load_manual_jds(_write(tmp_path, [ENTRY]))

    assert rec["id"] == "manual:acme:founding-engineer"
    assert rec["source"] == "manual"
    assert rec["ats"] == "manual"
    assert rec["fetched_backend"] == "manual-capture"
    assert rec["lane_hint"] == "founding"
    assert rec["company_slug"] == "acme"
    # every key the adapters emit is present, so downstream code can use the same accessors
    assert set(rec) == set(record())


def test_a_pulled_record_wins_over_a_manual_one_with_the_same_id(manual: list[dict]) -> None:
    """Once a board publishes the posting, the board is authoritative."""
    pulled = [record(id="manual:acme:founding-engineer", title="Founding Engineer (updated)")]

    (kept,) = with_manual(pulled, manual)

    assert kept["title"] == "Founding Engineer (updated)"


def test_manual_record_survives_a_pull_that_does_not_contain_it(manual: list[dict]) -> None:
    """The regression this item exists for: neither dropped from jobs-raw nor delisted in corpus."""
    day1 = with_manual([record(id="greenhouse:other:1", title="Other")], manual)
    corpus = merge_corpus([], day1, "2026-08-01")

    # a later pull that knows nothing about the manual JD
    day2 = with_manual([record(id="greenhouse:other:1", title="Other")], manual)
    merged = merge_corpus(corpus, day2, "2026-08-02")

    row = next(r for r in merged if r["id"] == "manual:acme:founding-engineer")
    assert row["last_seen"] == "2026-08-02"  # refreshed -> not delisted
    assert row["first_seen"] == "2026-08-01"
    assert row["description"] == "Build the thing."


def test_removing_an_entry_from_the_config_does_delist_it(manual: list[dict]) -> None:
    """Deliberate removal is the one way a manual JD ages out — the owner's explicit choice."""
    corpus = merge_corpus([], with_manual([], manual), "2026-08-01")

    merged = merge_corpus(corpus, with_manual([], []), "2026-08-02")

    row = next(r for r in merged if r["id"] == "manual:acme:founding-engineer")
    assert row["last_seen"] == "2026-08-01"  # frozen -> delisted, as intended


def test_a_malformed_entry_fails_loudly(tmp_path: Path) -> None:
    """A silent skip would lose exactly what this feature exists to protect."""
    with pytest.raises(ValueError, match=r"manual-jds\.json"):
        load_manual_jds(_write(tmp_path, [{"title": "no id here"}]))
