"""A results file is replaced whole or not at all (#514).

On 2026-11-18 an ingest killed mid-write left ``jobs-raw.json`` truncated, and every later stage
reads that file. The write must leave either the previous file or the new one, never a partial one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ajoa_kit.atomic import write_text_atomic


def test_a_failed_write_keeps_the_previous_file_and_leaves_no_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "jobs-raw.json"
    target.write_text('["previous pull"]')
    real_write = Path.write_text

    def dies_halfway(self: Path, data: str, *args: object, **kwargs: object) -> int:
        real_write(self, data[: len(data) // 2], *args, **kwargs)  # partial bytes on disk
        raise OSError("killed mid-write")

    monkeypatch.setattr(Path, "write_text", dies_halfway)
    with pytest.raises(OSError, match="killed mid-write"):
        write_text_atomic(target, '["new pull", "with more records"]')
    monkeypatch.undo()

    assert target.read_text() == '["previous pull"]'
    assert sorted(p.name for p in tmp_path.iterdir()) == ["jobs-raw.json"]
