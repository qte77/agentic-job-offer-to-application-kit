"""Value-add test for id-based dedupe (first occurrence wins, order preserved)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

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


class TestDedupeProperties:
    _ROWS = st.lists(st.fixed_dictionaries({"id": st.text(min_size=1)}), max_size=12)

    # Reason: pure dedupe over generated rows; deadline off.
    @given(rows=_ROWS)
    @settings(deadline=None)
    def test_unique_ids_idempotent_first_wins(self, rows: list[dict]) -> None:
        out = dedupe(rows)
        ids = [r["id"] for r in out]
        assert len(ids) == len(set(ids))  # ids unique
        assert len(out) <= len(rows)  # never grows
        assert dedupe(out) == out  # idempotent
        seen: set[str] = set()
        expected: list[dict] = []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                expected.append(r)
        assert out == expected  # first occurrence kept, order preserved
