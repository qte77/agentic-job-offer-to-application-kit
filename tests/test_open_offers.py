"""Value-add tests for tier 1's selection->URL join (``open_offers``).

Cover the pure join core only (``selected_urls``) — NOT ``main`` (``webbrowser``/filesystem
orchestration, per project convention: mirrors ``test_pack_plan.py``'s split). ``webbrowser.open``
itself is deliberately untested here: this devcontainer has no display, so any such test would be
meaningless or hang (see the PR body for this same note).
"""

from __future__ import annotations

from ajoa_kit.models import PackPolicy, ScoredItem
from ajoa_kit.open_offers import selected_urls


def _item(
    id_: str,
    score: int,
    lane: str = "engineering",
    title: str = "",
    company: str = "",
    url: str = "",
) -> ScoredItem:
    return ScoredItem(
        id=id_,
        score=score,
        best_lane=lane,
        title=title or id_,
        company=company or "Acme",
        url=url,
    )


def test_selected_urls_empty_shortlist_returns_empty() -> None:
    assert selected_urls([], PackPolicy()) == []


def test_selected_urls_filters_below_min_score() -> None:
    items = [
        _item("a", 5, url="https://example.com/a"),
        _item("b", 4, url="https://example.com/b"),
    ]
    out = selected_urls(items, PackPolicy(min_score=5))
    assert [row[0] for row in out] == ["a"]


def test_selected_urls_filters_by_lane_when_lanes_configured() -> None:
    items = [
        _item("a", 5, lane="ml", url="https://example.com/a"),
        _item("b", 5, lane="engineering", url="https://example.com/b"),
    ]
    out = selected_urls(items, PackPolicy(min_score=5, lanes=["ml"]))
    assert [row[0] for row in out] == ["a"]


def test_selected_urls_skips_items_with_no_url() -> None:
    items = [
        _item("a", 5, url=""),
        _item("b", 5, url="https://example.com/b"),
    ]
    out = selected_urls(items, PackPolicy(min_score=5))
    assert [row[0] for row in out] == ["b"]


def test_selected_urls_returns_id_title_company_url_tuples_in_priority_order() -> None:
    items = [
        _item("low", 5, title="Low Score", company="Acme", url="https://acme.example/low"),
        _item("high", 7, title="High Score", company="Other", url="https://other.example/high"),
    ]
    out = selected_urls(items, PackPolicy(min_score=5))
    assert out == [
        ("high", "High Score", "Other", "https://other.example/high"),
        ("low", "Low Score", "Acme", "https://acme.example/low"),
    ]
