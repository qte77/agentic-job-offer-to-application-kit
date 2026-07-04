"""Value-add tests for persist_scored parse-on-read (ADR-0003).

The relevance result is JSON-Schema-validated in the JS workflow, but that guarantee is lost when
Python re-reads the file (a human passes the path — it may be hand-edited, truncated, or wrong). So
persist re-validates: fail loud on a non-result, drop+count malformed items, flag un-laned ones.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import persist_scored

if TYPE_CHECKING:
    from pathlib import Path


def _item(jid: str, lane: str, score: object, **kw: object) -> dict:
    return {
        "id": jid,
        "title": f"{jid} engineer",
        "company": "Acme",
        "best_lane": lane,
        "score": score,
        "verdict": "shortlist",
        "rationale": "fits",
        "url": f"https://x/{jid}",
        **kw,
    }


def _run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: dict, *, merge: bool = False
) -> Path:
    results = tmp_path / "results"
    results.mkdir(exist_ok=True)  # exist_ok: a merge test persists twice into one results dir
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    src = tmp_path / "result.json"
    src.write_text(json.dumps(result))
    persist_scored.main(src=src, merge=merge)
    return results


def test_valid_result_writes_per_lane_shortlists_sorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = _run(
        tmp_path,
        monkeypatch,
        {
            "relevant": [
                _item("a", "engineering", 3),
                _item("b", "engineering", 5),
                _item("c", "cloud", 4),
            ]
        },
    )
    eng = json.loads((results / "engineering" / "shortlist.json").read_text())
    assert [j["id"] for j in eng] == ["b", "a"]  # sorted by score desc
    assert (results / "cloud" / "shortlist.json").is_file()
    assert json.loads((results / "jobs-scored.json").read_text())["relevant"][0]["id"] == "a"


def test_unknown_result_field_survives_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A field the relevance schema grows beyond ScoredItem's known set must round-trip (#197):
    # extra="allow" keeps it through model_dump() into jobs-scored.json and the per-lane shortlist.
    results = _run(
        tmp_path, monkeypatch, {"relevant": [_item("a", "engineering", 4, confidence=0.9)]}
    )
    scored = json.loads((results / "jobs-scored.json").read_text())["relevant"][0]
    assert scored["confidence"] == 0.9
    eng = json.loads((results / "engineering" / "shortlist.json").read_text())[0]
    assert eng["confidence"] == 0.9  # survives into the per-lane bucket too


def test_malformed_items_are_dropped_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    results = _run(
        tmp_path,
        monkeypatch,
        {
            "relevant": [
                _item("a", "engineering", 4),
                "garbage",  # not a dict
                {"id": "b", "best_lane": "engineering", "score": "not-a-number"},  # bad score type
            ]
        },
    )
    eng = json.loads((results / "engineering" / "shortlist.json").read_text())
    assert [j["id"] for j in eng] == ["a"]  # the two malformed items dropped
    assert "dropped 2" in capsys.readouterr().out


def test_missing_relevant_array_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    src = tmp_path / "r.json"
    src.write_text(json.dumps({"notes": "this is not a relevance result"}))
    with pytest.raises(ValueError, match="relevant"):
        persist_scored.main(src=src)


def test_unlaned_item_goes_to_unsorted_and_is_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    results = _run(tmp_path, monkeypatch, {"relevant": [_item("a", "", 4)]})  # empty best_lane
    assert (results / "unsorted" / "shortlist.json").is_file()
    assert "un-laned" in capsys.readouterr().out


def test_persist_merge_unions_into_existing_buckets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # seed ml + fde buckets (default overwrite persist)
    _run(tmp_path, monkeypatch, {"relevant": [_item("a1", "ml", 3), _item("f1", "fde", 5)]})
    # --merge a new ml id + a re-scored existing ml id; fde is absent from this delta
    results = _run(
        tmp_path,
        monkeypatch,
        {"relevant": [_item("a2", "ml", 4), _item("a1", "ml", 9)]},
        merge=True,
    )
    ml = {j["id"]: j for j in json.loads((results / "ml" / "shortlist.json").read_text())}
    assert set(ml) == {"a1", "a2"}  # existing kept, new added
    assert ml["a1"]["score"] == 9  # same id -> the re-scored (incoming) item wins
    fde = json.loads((results / "fde" / "shortlist.json").read_text())
    assert [j["id"] for j in fde] == ["f1"]  # a lane absent from the delta is untouched


def test_persist_merge_unions_jobs_scored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _run(tmp_path, monkeypatch, {"relevant": [_item("a", "ml", 3)]})
    results = _run(
        tmp_path,
        monkeypatch,
        {"relevant": [_item("a", "ml", 9), _item("b", "ml", 4)]},
        merge=True,
    )
    rel = {j["id"]: j for j in json.loads((results / "jobs-scored.json").read_text())["relevant"]}
    assert set(rel) == {"a", "b"}  # relevant[] unioned by id
    assert rel["a"]["score"] == 9  # same id -> new wins


def test_persist_merge_evicts_relaned_offer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An offer that changes lane on --merge must move, not duplicate: it lands in its new lane only,
    # evicted from the old bucket (#236); an unrelated id in the old lane stays.
    _run(tmp_path, monkeypatch, {"relevant": [_item("x", "ml", 5), _item("keep", "ml", 3)]})
    results = _run(
        tmp_path,
        monkeypatch,
        {"relevant": [_item("x", "engineering", 6)]},
        merge=True,
    )
    eng = [j["id"] for j in json.loads((results / "engineering" / "shortlist.json").read_text())]
    ml = [j["id"] for j in json.loads((results / "ml" / "shortlist.json").read_text())]
    assert eng == ["x"]  # re-laned into engineering
    assert ml == ["keep"]  # evicted from ml; the unrelated ml id remains


def test_persist_routes_hallucinated_lane_to_unsorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # a best_lane not in config/lanes.json is blanked and routed to unsorted/ (no junk
    # results/<bogus>/ dir) and tallied; a valid lane still buckets normally.
    results = _run(
        tmp_path,
        monkeypatch,
        {"relevant": [_item("a", "engineering", 4), _item("b", "nonsense-lane", 5)]},
    )
    assert not (results / "nonsense-lane").exists()  # no junk dir for the hallucinated lane
    unsorted = json.loads((results / "unsorted" / "shortlist.json").read_text())
    assert [j["id"] for j in unsorted] == ["b"]  # the bogus-lane JD kept, routed to unsorted
    assert (results / "engineering" / "shortlist.json").is_file()  # valid lane still buckets
    assert "invalid-lane" in capsys.readouterr().out  # tallied in the summary line
