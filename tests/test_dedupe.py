"""Value-add test for id-based dedupe (first occurrence wins, order preserved)."""

from __future__ import annotations

from ajoa_kit.ingest import dedupe


def test_dedupe_first_wins_and_preserves_order() -> None:
    rows = [
        {"id": "a", "title": "first"},
        {"id": "b", "title": "second"},
        {"id": "a", "title": "dup-loses"},
    ]
    out = dedupe(rows)
    assert [r["id"] for r in out] == ["a", "b"]
    assert out[0]["title"] == "first"  # earlier source wins on collision
