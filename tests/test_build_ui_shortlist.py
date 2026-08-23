"""Value-add tests for the preview aggregator (``scripts/build_ui_shortlist.py``).

Covers the one contract the dashboard depends on: the flattened row order. ``aggregate()`` used to
emit rows in glob-path order, and because the ``engineering`` lane holds the large majority of them
a high-scoring row from a later lane landed hundreds of positions down (plan 010, item 6).

``scripts/`` is not part of the installed package, so the module is imported off an explicit
``sys.path`` entry rather than by restructuring the project layout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_ui_shortlist import aggregate

if TYPE_CHECKING:
    from collections.abc import Mapping


def _lane_glob(root: Path, lanes: Mapping[str, list[dict]]) -> str:
    """Write ``<root>/results/<lane>/shortlist.json`` per lane, return the matching glob."""
    for lane, rows in lanes.items():
        lane_dir = root / "results" / lane
        lane_dir.mkdir(parents=True)
        (lane_dir / "shortlist.json").write_text(json.dumps(rows))
    return str(root / "results" / "*" / "shortlist.json")


def test_aggregate_orders_by_score_desc_across_lane_files(tmp_path: Path) -> None:
    # The top score sits in the alphabetically LAST lane, behind a fat `engineering` lane —
    # the exact burial the glob-path ordering caused.
    results_glob = _lane_glob(
        tmp_path,
        {
            "engineering": [{"id": f"eng-{n}", "score": 2} for n in range(5)],
            "ml": [{"id": "ml-mid", "score": 3}],
            "strategy": [{"id": "strat-top", "score": 5}],
        },
    )

    out = aggregate(results_glob)

    assert [it["id"] for it in out][:2] == ["strat-top", "ml-mid"]
    scores = [it["score"] for it in out]
    assert scores == sorted(scores, reverse=True)


def test_aggregate_tie_break_keeps_lane_path_then_in_file_order(tmp_path: Path) -> None:
    # Equal scores must not be reshuffled: the dashboard output is snapshot-compared, so the
    # pre-existing glob-path -> in-file order has to survive the sort.
    results_glob = _lane_glob(
        tmp_path,
        {
            "engineering": [{"id": "eng-first", "score": 4}, {"id": "eng-second", "score": 4}],
            "strategy": [{"id": "strat-first", "score": 4}, {"id": "strat-second", "score": 4}],
        },
    )

    out = aggregate(results_glob)

    assert [it["id"] for it in out] == ["eng-first", "eng-second", "strat-first", "strat-second"]


def test_aggregate_sinks_unusable_scores_and_still_drops_stale(tmp_path: Path) -> None:
    # `score` is optional in the ScoredItem contract and this boundary reads raw JSON, so a
    # missing/None/non-numeric score must sort last instead of raising or displacing a real row.
    results_glob = _lane_glob(
        tmp_path,
        {
            "engineering": [
                {"id": "no-score"},
                {"id": "null-score", "score": None},
                {"id": "text-score", "score": "high"},
                {"id": "stale-top", "score": 5, "stale": True},
            ],
            "ml": [{"id": "ml-real", "score": 1}],
        },
    )

    out = aggregate(results_glob)

    assert [it["id"] for it in out] == ["ml-real", "no-score", "null-score", "text-score"]
