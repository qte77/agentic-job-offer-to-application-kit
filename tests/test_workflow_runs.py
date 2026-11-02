"""Value-add tests for collecting headless relevance runs from their workflow journals (#342).

Claude Code appends one journal line per workflow agent event under
``~/.claude/projects/<cwd-slug>/<session>/subagents/workflows/<runId>/journal.jsonl``. That file is
not in the public docs, so these fixtures pin the fields the collector relies on (observed with
Claude Code 2.1.316): a run cut short still leaves its finished batches there, a timed-out batch is
a ``failed`` line, and re-runs of the same batch must not double-count a JD.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import workflow_runs

if TYPE_CHECKING:
    from pathlib import Path


def _row(jd_id: str, score: int) -> dict:
    return {"id": jd_id, "title": "Engineer", "company": "Acme", "best_lane": "ml", "score": score}


def _journal(
    projects: Path, session: str, events: list[tuple[str, str, list[dict] | None]]
) -> None:
    """Write one run's journal: ``(label, kind, rows)`` per agent; kind is result or failed."""
    run = projects / session / "subagents" / "workflows" / "wf_test-1"
    run.mkdir(parents=True)
    lines: list[dict] = [{"type": "launched"}]  # the real first line carries no key
    for n, (label, kind, rows) in enumerate(events):
        key = f"v2:{session}-{n}"
        lines.append({"type": "started", "key": key, "agentId": f"a{n}", "label": label})
        done = {"type": kind, "key": key, "agentId": f"a{n}"}
        if kind == "result":
            done["result"] = {"relevant": rows, "dropped_count": 0}
        lines.append(done)
    (run / "journal.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")


S1 = "4b8ef9d2-1e0c-4444-b56a-f44e32890206"


def test_cwd_slug_matches_claude_code_project_dir_naming() -> None:
    cwd = "/workspaces/qte77/agentic-job-offer-to-application-kit"
    assert workflow_runs.cwd_slug(cwd) == "-workspaces-qte77-agentic-job-offer-to-application-kit"


def test_collects_finished_batches_and_reports_failed_ones_as_missing(tmp_path: Path) -> None:
    _journal(
        tmp_path,
        "s1",
        [
            ("batch-000", "result", [_row("a", 5)]),
            ("batch-001", "failed", None),
            ("batch-002", "result", [_row("b", 4), _row("c", 3)]),
        ],
    )
    got = workflow_runs.collect(["s1"], tmp_path)
    assert sorted(r.id for r in got.relevant) == ["a", "b", "c"]
    assert got.done == {0, 2}
    assert workflow_runs.missing_ranges(got.done, batch_count=4) == [(1, 1), (3, 1)]


def test_rerun_of_a_batch_keeps_one_row_per_jd_with_the_higher_score(tmp_path: Path) -> None:
    _journal(tmp_path, "first", [("batch-000", "result", [_row("a", 3), _row("b", 4)])])
    _journal(tmp_path, "rerun", [("batch-000", "result", [_row("a", 5)])])
    got = workflow_runs.collect(["first", "rerun"], tmp_path)
    assert {r.id: r.score for r in got.relevant} == {"a": 5, "b": 4}


def test_missing_ranges_merges_consecutive_batches_into_start_limit_pairs() -> None:
    done = {0, 1, 5, 9}
    assert workflow_runs.missing_ranges(done, batch_count=10) == [(2, 3), (6, 3)]


def test_main_writes_the_result_and_fails_listing_the_rerun_ranges(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    projects = tmp_path / "projects"
    _journal(projects, S1, [("batch-000", "result", [_row("a", 5)])])
    sessions = tmp_path / "sessions.txt"
    sessions.write_text(f"{S1}  # batches 0..2\n\n")
    out = tmp_path / "relevant.json"
    assert workflow_runs.main(sessions, out=out, projects=projects, batch_count=3) == 1
    assert [r["id"] for r in json.loads(out.read_text())["relevant"]] == ["a"]
    assert 'RANGES="1:2"' in capsys.readouterr().out


def test_sessions_file_with_a_non_uuid_line_fails_loud(tmp_path: Path) -> None:
    bad = tmp_path / "sessions.txt"
    bad.write_text("not-a-session\n")
    with pytest.raises(ValueError, match="session UUID"):
        workflow_runs.main(bad, out=tmp_path / "o.json", projects=tmp_path, batch_count=1)
