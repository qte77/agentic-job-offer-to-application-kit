"""Value-add tests for the keyword-only trend snapshot (#11 PR-A).

Sharp edges: document-frequency counting (a term repeated within one JD counts once),
multi-word term matching, and idempotent per-ISO-week upsert. No JD content reaches the
output — only ``{keyword: count}``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit import ingest, trend_snapshot

if TYPE_CHECKING:
    from pathlib import Path


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
