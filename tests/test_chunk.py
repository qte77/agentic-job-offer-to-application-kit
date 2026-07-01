"""Value-add tests for `chunk --new` incremental delta batching (#226).

`chunk` normally splits the whole `results/jobs-raw.json`; `--new` instead batches only the offers
first seen in the latest ingest pull (`first_seen == max(last_seen)` in `results/corpus.json`), so a
daily re-screen fans relevance out over just the delta. These pin the two behaviours a unit test can
own: the filter keys on `first_seen` (not merely "seen today"), and a missing corpus fails loud.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import chunk

if TYPE_CHECKING:
    from pathlib import Path


def _rec(jid: str, first: str, last: str) -> dict:
    """A corpus.json record (JD fields + the merge-stamped first_seen/last_seen/content_hash)."""
    return {
        "id": jid,
        "title": f"{jid} role",
        "first_seen": first,
        "last_seen": last,
        "content_hash": jid,
    }


# latest pull date = max(last_seen) = 2026-06-30. `new1`/`new2` are first seen then (the delta);
# `old` is seen in that pull but first seen earlier (must be excluded — proves we key on first_seen,
# not last_seen); `gone` is delisted (last_seen frozen in the past).
CORPUS = [
    _rec("old", "2026-06-01", "2026-06-30"),
    _rec("new1", "2026-06-30", "2026-06-30"),
    _rec("new2", "2026-06-30", "2026-06-30"),
    _rec("gone", "2026-05-01", "2026-06-20"),
]


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    return results


def test_chunk_new_batches_only_the_delta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = _setup(tmp_path, monkeypatch)
    (results / "corpus.json").write_text(json.dumps(CORPUS))
    raw = results / "jobs-raw.json"
    raw.write_text(json.dumps([{"id": "should-not-be-read"}]))  # --new must ignore jobs-raw.json

    chunk.main(batch=40, new=True)

    manifest = json.loads((results / "batches" / "manifest.json").read_text())
    assert manifest["total_jobs"] == 2  # only first_seen == max(last_seen)
    assert manifest["batch_count"] == 1
    batch = json.loads((results / "batches" / "batch-000.json").read_text())
    assert sorted(j["id"] for j in batch) == ["new1", "new2"]  # old + gone excluded
    assert json.loads(raw.read_text()) == [{"id": "should-not-be-read"}]  # jobs-raw.json untouched


def test_chunk_new_fails_loud_without_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(tmp_path, monkeypatch)  # no corpus.json written
    with pytest.raises(FileNotFoundError, match="corpus"):
        chunk.main(batch=40, new=True)
