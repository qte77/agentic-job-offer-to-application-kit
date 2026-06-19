"""Value-add tests for ingest source loading.

Cover the seed.json -> default-seed.json fallback contract only (the behavior with real
branches): the git-ignored run config wins, the shipped default is the fallback, and a
config dir holding neither fails loud. Adapter parsing / pre-filter is covered elsewhere.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import ingest

if TYPE_CHECKING:
    from pathlib import Path


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
