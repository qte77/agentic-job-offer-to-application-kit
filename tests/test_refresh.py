"""Value-add tests for the shortlist liveness sweep (#214).

Cover the pure decision core (``is_delisted`` / ``classify``), ``refresh_lane``'s three write modes
with an injected probe (no network), and the ``--lane`` validation. The key guard: an inconclusive
probe (``None``) never expires a live entry.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import refresh

if TYPE_CHECKING:
    from pathlib import Path


def test_is_delisted_only_when_absent_from_latest_pull() -> None:
    assert refresh.is_delisted({"last_seen": "2026-06-20"}, "2026-06-30") is True  # delisted
    assert refresh.is_delisted({"last_seen": "2026-06-30"}, "2026-06-30") is False  # seen this pull
    assert refresh.is_delisted(None, "2026-06-30") is False  # absent from corpus -> probe decides


def test_classify_stale_rules() -> None:
    assert refresh.classify(corpus_delisted=True, status=None) is True  # corpus says gone
    assert refresh.classify(corpus_delisted=False, status=404) is True  # definitive dead URL
    assert refresh.classify(corpus_delisted=False, status=200) is False  # live
    assert refresh.classify(corpus_delisted=False, status=None) is False  # inconclusive kept
    assert refresh.classify(corpus_delisted=True, status=200) is True  # corpus wins over a live URL


def _bucket(tmp_path: Path, items: list[dict]) -> Path:
    d = tmp_path / "ml"
    d.mkdir(parents=True)
    (d / "shortlist.json").write_text(json.dumps(items))
    return d


def test_refresh_lane_flags_stale_keeps_rows(tmp_path: Path) -> None:
    _bucket(
        tmp_path,
        [
            {"id": "a", "url": "https://x/a", "score": 5},  # 200 -> live
            {"id": "b", "url": "https://x/b", "score": 4},  # 404 -> stale
            {"id": "c", "url": "https://x/c", "score": 3},  # corpus-delisted -> stale (not probed)
            {"id": "d", "url": "https://x/d", "score": 2},  # unreachable (None) -> stays live
        ],
    )
    corpus = {"c": {"id": "c", "last_seen": "2026-06-20"}}

    def probe(url: str) -> int | None:
        return {"https://x/a": 200, "https://x/b": 404}.get(url)  # c/d -> None

    rep = refresh.refresh_lane(
        "ml", tmp_path, corpus, "2026-06-30", probe, "2026-06-30", delete=False, dry_run=False
    )
    assert rep == {"lane": "ml", "live": 2, "stale": 2, "missing": False}
    written = json.loads((tmp_path / "ml" / "shortlist.json").read_text())
    by_id = {it["id"]: it for it in written}
    assert by_id["a"]["stale"] is False  # 200 -> live
    assert by_id["d"]["stale"] is False  # inconclusive -> live
    assert by_id["b"]["stale"] is True
    assert by_id["c"]["stale"] is True
    assert all(it["last_checked"] == "2026-06-30" for it in written)
    assert [it["id"] for it in written] == ["a", "d", "b", "c"]  # live (by score) above stale


def test_refresh_lane_delete_drops_stale(tmp_path: Path) -> None:
    _bucket(tmp_path, [{"id": "a", "url": "https://x/a"}, {"id": "b", "url": "https://x/b"}])

    def probe(url: str) -> int | None:
        return {"https://x/a": 200, "https://x/b": 410}.get(url)

    refresh.refresh_lane(
        "ml", tmp_path, {}, "2026-06-30", probe, "2026-06-30", delete=True, dry_run=False
    )
    written = json.loads((tmp_path / "ml" / "shortlist.json").read_text())
    assert [it["id"] for it in written] == ["a"]  # the 410 row is removed, not flagged


def test_refresh_lane_dry_run_leaves_files_untouched(tmp_path: Path) -> None:
    d = _bucket(tmp_path, [{"id": "b", "url": "https://x/b"}])
    before = (d / "shortlist.json").read_text()

    def probe(_url: str) -> int | None:
        return 404

    rep = refresh.refresh_lane(
        "ml", tmp_path, {}, "2026-06-30", probe, "2026-06-30", delete=False, dry_run=True
    )
    assert rep["stale"] == 1
    assert (d / "shortlist.json").read_text() == before  # reported, not written


def test_targets_validates_lane_and_globs_existing_buckets(tmp_path: Path) -> None:
    # No lanes.json -> load_lanes falls back to DEFAULT_LANES, whose keys include "ml".
    assert refresh._targets("ml", tmp_path, tmp_path) == ["ml"]
    with pytest.raises(SystemExit):
        refresh._targets("bogus", tmp_path, tmp_path)
    for lane in ("ml", "cloud"):
        (tmp_path / lane).mkdir()
        (tmp_path / lane / "shortlist.json").write_text("[]")
    assert refresh._targets(None, tmp_path, tmp_path) == ["cloud", "ml"]  # sorted bucket dirs
