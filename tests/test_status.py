"""Value-add tests for the local application-outcome tracker (``status``, #273).

Cover the sharp edges: round-trip write/read of ``status.json``, a PARTIAL update (only the provided
fields change, the others are preserved), a missing file defaulting to an empty status, and a
fail-loud read on a malformed file (it is Python-written, so corruption is a bug, not input).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import status

if TYPE_CHECKING:
    from pathlib import Path


def test_set_status_writes_and_read_round_trips(tmp_path: Path) -> None:
    offer = tmp_path / "offers" / "acme-founding"
    offer.mkdir(parents=True)
    out = status.set_status(offer, stage="applied", date="2026-07-12", notes="referred by X")
    assert (out.stage, out.date, out.notes) == ("applied", "2026-07-12", "referred by X")
    back = status.read_status(offer)
    assert (back.stage, back.date, back.notes) == ("applied", "2026-07-12", "referred by X")
    assert json.loads((offer / "status.json").read_text())["stage"] == "applied"


def test_set_status_partial_update_preserves_other_fields(tmp_path: Path) -> None:
    offer = tmp_path / "offers" / "acme-founding"
    offer.mkdir(parents=True)
    status.set_status(offer, stage="applied", date="2026-07-12", notes="first")
    # advance only the stage — the date + notes set earlier must survive.
    out = status.set_status(offer, stage="interview")
    assert out.stage == "interview"
    assert out.date == "2026-07-12"
    assert out.notes == "first"


def test_read_status_missing_file_is_empty_default(tmp_path: Path) -> None:
    offer = tmp_path / "offers" / "never-touched"
    offer.mkdir(parents=True)
    s = status.read_status(offer)
    assert (s.stage, s.date, s.notes) == ("", "", "")


def test_read_status_fails_loud_on_malformed_file(tmp_path: Path) -> None:
    offer = tmp_path / "offers" / "corrupt"
    offer.mkdir(parents=True)
    (offer / "status.json").write_text("{ not json")
    with pytest.raises(json.JSONDecodeError):
        status.read_status(offer)
