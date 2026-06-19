"""Value-add tests for ingest source loading.

Cover the seed.json -> default-seed.json fallback contract and the integrity of the shipped
default-seed.json (so a malformed committed default can't silently break out-of-box ingest).
Adapter parsing / pre-filter is covered elsewhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ajoa_kit import ingest


def _write(path: Path, slug: str) -> None:
    entry = {"ats": "lever", "slug": slug, "company": "X", "lane": "engineering"}
    path.write_text(json.dumps({"feeds": [], "ats": [entry]}))


def test_load_sources_prefers_seed_over_default(tmp_path: Path) -> None:
    _write(tmp_path / "seed.json", "from-seed")
    _write(tmp_path / "default-seed.json", "from-default")
    _, ats = ingest.load_sources(tmp_path)
    assert [a["slug"] for a in ats] == ["from-seed"]  # the run config wins


def test_load_sources_falls_back_to_default(tmp_path: Path) -> None:
    _write(tmp_path / "default-seed.json", "from-default")  # no seed.json present
    _, ats = ingest.load_sources(tmp_path)
    assert [a["slug"] for a in ats] == ["from-default"]


def test_load_sources_fails_loud_when_neither_present(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"seed\.json"):
        ingest.load_sources(tmp_path)


def test_shipped_default_seed_is_valid() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "default-seed.json"
    cfg = json.loads(path.read_text())  # raises on malformed JSON
    assert cfg["ats"], "default-seed.json must list ats sources"
    assert all({"ats", "slug", "company", "lane"} <= e.keys() for e in cfg["ats"])
    assert all({"source", "url"} <= f.keys() for f in cfg["feeds"])
