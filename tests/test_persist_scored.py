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


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: dict) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    src = tmp_path / "result.json"
    src.write_text(json.dumps(result))
    persist_scored.main(src=src)
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
                _item("c", "platform", 4),
            ]
        },
    )
    eng = json.loads((results / "engineering" / "shortlist.json").read_text())
    assert [j["id"] for j in eng] == ["b", "a"]  # sorted by score desc
    assert (results / "platform" / "shortlist.json").is_file()
    assert json.loads((results / "jobs-scored.json").read_text())["relevant"][0]["id"] == "a"


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
