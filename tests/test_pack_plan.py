"""Value-add tests for the pack-coverage policy core (``pack_plan``).

Cover the pure decision core only (``select``/``missing``) — NOT the thin ``main``/CLI (network-
and-filesystem orchestration, per project convention: mirrors ``refresh.py``'s test split).
"""

from __future__ import annotations

from pathlib import Path

from ajoa_kit.models import PackPolicy, ScoredItem
from ajoa_kit.pack_plan import load_policy, missing, select


def _item(
    id_: str, score: int, lane: str = "engineering", title: str = "", company: str = ""
) -> ScoredItem:
    return ScoredItem(
        id=id_, score=score, best_lane=lane, title=title or id_, company=company or "Acme"
    )


def test_select_filters_below_min_score() -> None:
    items = [_item("a", 5), _item("b", 4), _item("c", 3)]
    out = select(items, PackPolicy(min_score=5))
    assert [i.id for i in out] == ["a"]


def test_select_treats_none_score_as_excluded() -> None:
    items = [ScoredItem(id="a", score=None, best_lane="engineering", title="A", company="Acme")]
    assert select(items, PackPolicy(min_score=5)) == []


def test_select_filters_by_lane_when_lanes_configured() -> None:
    items = [_item("a", 5, lane="ml"), _item("b", 5, lane="engineering")]
    out = select(items, PackPolicy(min_score=5, lanes=["ml"]))
    assert [i.id for i in out] == ["a"]


def test_select_empty_lanes_means_every_lane() -> None:
    items = [_item("a", 5, lane="ml"), _item("b", 5, lane="engineering")]
    out = select(items, PackPolicy(min_score=5, lanes=[]))
    assert {i.id for i in out} == {"a", "b"}


def test_select_orders_by_score_descending() -> None:
    items = [_item("low", 5), _item("high", 5, company="Other")]
    items[0].score = 5
    items[1].score = 7
    out = select(items, PackPolicy(min_score=5))
    assert [i.id for i in out] == ["high", "low"]


def test_select_is_stable_for_equal_scores() -> None:
    # Equal-score items keep their original relative (input) order — a stable sort, not an
    # arbitrary reorder.
    items = [
        _item("first", 5, company="A"),
        _item("second", 5, company="B"),
        _item("third", 5, company="C"),
    ]
    out = select(items, PackPolicy(min_score=5))
    assert [i.id for i in out] == ["first", "second", "third"]


def test_select_dedups_same_role_and_company_keeping_higher_score() -> None:
    items = [
        _item("dup-low", 5, title="Backend Engineer", company="Acme"),
        _item("dup-high", 7, title="backend engineer", company="ACME"),  # same, different case
    ]
    out = select(items, PackPolicy(min_score=5))
    assert [i.id for i in out] == ["dup-high"]  # higher score wins after sort-then-dedup


def test_select_dedup_off_keeps_both_when_dedup_is_a_different_value() -> None:
    items = [
        _item("dup-a", 5, title="Backend Engineer", company="Acme"),
        _item("dup-b", 5, title="Backend Engineer", company="Acme"),
    ]
    out = select(items, PackPolicy(min_score=5, dedup="none"))
    assert {i.id for i in out} == {"dup-a", "dup-b"}


def test_select_applies_per_company_cap_after_scoring() -> None:
    items = [
        _item("acme-1", 9, company="Acme", title="Role 1"),
        _item("acme-2", 8, company="Acme", title="Role 2"),
        _item("acme-3", 7, company="Acme", title="Role 3"),
        _item("other-1", 6, company="Other", title="Role 4"),
    ]
    out = select(items, PackPolicy(min_score=5, per_company_cap=2))
    assert [i.id for i in out] == ["acme-1", "acme-2", "other-1"]


def test_select_applies_max_packs_after_ordering() -> None:
    items = [_item("a", 9), _item("b", 8, company="B"), _item("c", 7, company="C")]
    out = select(items, PackPolicy(min_score=5, max_packs=2))
    assert [i.id for i in out] == ["a", "b"]


def test_select_max_packs_zero_is_unlimited() -> None:
    items = [_item("a", 9), _item("b", 8, company="B")]
    out = select(items, PackPolicy(min_score=5, max_packs=0))
    assert len(out) == 2


def test_missing_diffs_targets_against_the_offer_index() -> None:
    targets = [_item("a", 5), _item("b", 5, company="B")]
    offer_index = {"a": Path("/results/offers/a")}
    assert missing(targets, offer_index) == ["b"]


def test_missing_empty_when_all_targets_have_packs() -> None:
    targets = [_item("a", 5)]
    offer_index = {"a": Path("/results/offers/a")}
    assert missing(targets, offer_index) == []


def test_load_policy_absent_file_returns_defaults(tmp_path: Path) -> None:
    assert load_policy(tmp_path) == PackPolicy()


def test_load_policy_reads_config_override(tmp_path: Path) -> None:
    (tmp_path / "pack-policy.json").write_text('{"min_score": 4, "max_packs": 10}')
    policy = load_policy(tmp_path)
    assert policy.min_score == 4
    assert policy.max_packs == 10
    assert policy.dedup == "role_x_company"  # unspecified fields keep their default
