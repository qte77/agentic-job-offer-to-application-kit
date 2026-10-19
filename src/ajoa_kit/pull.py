"""The latest ingest pull date, kept in ``results/last-pull.json`` (#346).

``ingest`` writes it on every pull; ``persist`` and ``persist-offer`` stamp it onto what they write,
so a shortlist row or offer pack built from an old pull is visibly old. A small sidecar rather
than ``max(last_seen)`` over ``corpus.json``, which is large and only exists after ``--merge``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from ajoa_kit.models import PullStamp

if TYPE_CHECKING:
    from pathlib import Path

PULL_STAMP = "last-pull.json"


def write_pull_date(results_dir: Path, day: str) -> None:
    """Record ``day`` (ISO date) as the latest pull."""
    (results_dir / PULL_STAMP).write_text(PullStamp(date=day).model_dump_json())


def pull_date(results_dir: Path) -> str:
    """Return the latest pull date, or "" when no valid stamp exists."""
    try:
        return PullStamp.model_validate_json((results_dir / PULL_STAMP).read_text()).date
    except (OSError, ValidationError):
        return ""
