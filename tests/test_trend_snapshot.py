"""Value-add tests for the keyword-only trend snapshot (#11 PR-A).

Sharp edges: document-frequency counting (a term repeated within one JD counts once),
multi-word term matching, and idempotent per-ISO-week upsert. No JD content reaches the
output — only ``{keyword: count}``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit import ingest, trend_snapshot


def _read_ndjson(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def test_extract_counts_document_frequency_and_multiword() -> None:
    pat, _ = ingest.build_patterns(["python", "site reliability", "kubernetes"], ["python"])
    jobs = [
        {"title": "Site Reliability Engineer", "description": "Python and Kubernetes."},
        {"title": "Backend Engineer", "description": "Python, python, PYTHON."},
        {"title": "Designer", "description": "Figma only."},
    ]
    counts = trend_snapshot.extract_counts(jobs, pat)
    assert counts["python"] == 2  # document frequency: 2 JDs mention python, not 4 occurrences
    assert counts["site reliability"] == 1  # multi-word term matched on word boundary
    assert counts["kubernetes"] == 1
    assert "figma" not in counts  # outside the configured vocabulary


def test_upsert_week_appends_new_week(tmp_path: Path) -> None:
    path = tmp_path / "trends.ndjson"
    trend_snapshot.upsert_week(path, "2026-W10", {"python": 3})
    trend_snapshot.upsert_week(path, "2026-W11", {"python": 5})
    weeks = [json.loads(ln)["week"] for ln in path.read_text().splitlines()]
    assert weeks == ["2026-W10", "2026-W11"]


def test_upsert_week_replaces_same_week(tmp_path: Path) -> None:
    path = tmp_path / "trends.ndjson"
    trend_snapshot.upsert_week(path, "2026-W10", {"python": 3})
    trend_snapshot.upsert_week(path, "2026-W10", {"python": 9})  # same week -> replace, not append
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["counts"] == {"python": 9}


class TestTrendSnapshotProperties:
    _JOBS = st.lists(
        st.fixed_dictionaries({"title": st.text(), "description": st.text()}), max_size=8
    )
    _WEEK = st.text(min_size=1).filter(lambda s: bool(s.strip()))

    # Reason: pure counting over generated jobs; deadline off.
    @given(jobs=_JOBS)
    @settings(deadline=None)
    def test_extract_counts_bounded_by_job_count(self, jobs: list[dict]) -> None:
        pat, _ = ingest.build_patterns(["python", "rust", "go", "ml"], [])
        counts = trend_snapshot.extract_counts(jobs, pat)
        assert all(1 <= c <= len(jobs) for c in counts.values())

    # Reason: filesystem round-trip per example; own temp dir avoids fixture reuse across examples.
    @given(wa=_WEEK, wb=_WEEK)
    @settings(deadline=None)
    def test_upsert_one_line_per_week_idempotent_preserving_others(self, wa: str, wb: str) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trends.ndjson"
            trend_snapshot.upsert_week(path, wa, {"python": 1})
            trend_snapshot.upsert_week(path, wb, {"rust": 2})
            trend_snapshot.upsert_week(path, wa, {"python": 3})  # re-upsert wa
            records = [json.loads(ln) for ln in path.read_text().split("\n") if ln.strip()]
            weeks = [r["week"] for r in records]
            assert weeks.count(wa) == 1  # one line for wa despite re-upsert
            if wb != wa:
                assert wb in weeks  # other week preserved
            wa_counts = next(r["counts"] for r in records if r["week"] == wa)
            assert wa_counts == {"python": 3}  # re-upsert updated wa's counts


# 2024-01-15 is a Monday in ISO week 2024-W03; every adapter's posted_at format below resolves
# to that same week, so backfill buckets a JD by when it was really posted (not the run date).
@pytest.mark.parametrize(
    "raw",
    [
        "2024-01-15T10:30:00+02:00",  # ISO-8601 with offset (greenhouse/ashby/themuse)
        "2024-01-15T10:30:00Z",  # ISO-8601 Zulu suffix
        "2024-01-15",  # ISO date-only (workable published_on)
        "Mon, 15 Jan 2024 10:30:00 +0000",  # RFC-822 (RSS pubDate)
        "1705276800",  # epoch seconds = 2024-01-15 00:00 UTC (arbeitnow created_at)
        "1705276800000",  # epoch milliseconds, same instant (lever createdAt)
    ],
)
def test_parse_week_resolves_each_adapter_format(raw: str) -> None:
    assert trend_snapshot.parse_week(raw) == "2024-W03"


@pytest.mark.parametrize("raw", ["", "   ", "not a date", "2024-13-99"])
def test_parse_week_returns_none_when_unparseable(raw: str) -> None:
    assert trend_snapshot.parse_week(raw) is None


def test_bucket_by_week_activity_dating_prefers_last_modified_with_fallback() -> None:
    pat, _ = ingest.build_patterns(["python", "rust"], [])
    jobs = [
        # posted W03, but last-modified W08 -> activity dating must place it in W08
        {
            "title": "Python",
            "description": "python",
            "posted_at": "2024-01-15",
            "last_modified": "2024-02-19",
        },
        # no last_modified -> activity dating falls back to posted_at (W04)
        {"title": "Rust", "description": "rust", "posted_at": "2024-01-22", "last_modified": ""},
    ]
    activity = lambda j: j.get("last_modified") or j.get("posted_at", "")  # noqa: E731
    weeks, skipped = trend_snapshot.bucket_by_week(jobs, pat, date_of=activity)
    assert weeks["2024-W08"] == {"python": 1}  # re-dated by last_modified
    assert weeks["2024-W04"] == {"rust": 1}  # fell back to posted_at
    assert skipped == 0
    # default extractor still buckets by posted_at (back-compat)
    posted, _ = trend_snapshot.bucket_by_week(jobs, pat)
    assert set(posted) == {"2024-W03", "2024-W04"}


def test_bucket_by_week_groups_by_posted_week_and_counts_skipped() -> None:
    pat, _ = ingest.build_patterns(["python", "rust"], [])
    jobs = [
        {"title": "Python Dev", "description": "python", "posted_at": "2024-01-15"},  # W03
        {"title": "More Python", "description": "python", "posted_at": "2024-01-16"},  # W03
        {"title": "Rust Dev", "description": "rust", "posted_at": "2024-01-22"},  # W04
        {"title": "Undated", "description": "python", "posted_at": ""},  # no date -> skipped
    ]
    weeks, skipped = trend_snapshot.bucket_by_week(jobs, pat)
    assert weeks["2024-W03"] == {"python": 2}  # document frequency within the week
    assert weeks["2024-W04"] == {"rust": 1}
    assert skipped == 1  # the undated JD cannot be placed in time


def test_main_buckets_corpus_by_first_seen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    monkeypatch.setattr(trend_snapshot, "load_keywords", lambda _cfg: (["python"], ["python"]))
    # corpus.json present -> bucket by first_seen. posted_at is a different YEAR, so the bucketed
    # week proves which field main() used.
    (results / "corpus.json").write_text(
        json.dumps(
            [
                {
                    "id": "a",
                    "title": "Python Dev",
                    "description": "python",
                    "first_seen": "2026-06-01",
                    "posted_at": "2024-01-15",
                }
            ]
        )
    )
    trend_snapshot.main()
    lines = _read_ndjson(results / "trends.ndjson")
    assert len(lines) == 1
    assert lines[0]["week"].startswith("2026-W")  # first_seen, not posted_at's 2024
    assert lines[0]["counts"]["python"] == 1


def test_main_falls_back_to_jobs_raw_posted_at_without_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    monkeypatch.setattr(trend_snapshot, "load_keywords", lambda _cfg: (["python"], ["python"]))
    # no corpus.json -> read jobs-raw.json, bucket by posted_at (back-compat).
    job = {"id": "a", "title": "Python Dev", "description": "python", "posted_at": "2024-01-15"}
    (results / "jobs-raw.json").write_text(json.dumps([job]))
    trend_snapshot.main()
    lines = _read_ndjson(results / "trends.ndjson")
    assert lines[0]["week"] == "2024-W03"  # posted_at week
