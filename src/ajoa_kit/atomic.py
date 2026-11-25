"""Replace a results file whole or not at all (#514).

A plain ``Path.write_text`` truncates the target first, so a run killed mid-write leaves a partial
file behind; on 2026-11-18 that cut ``jobs-raw.json`` short and broke every stage that reads it.
Writing to a sibling temp file and swapping it in with :func:`os.replace` (atomic on POSIX and
Windows within one filesystem) means a reader sees the previous file or the new one, never half.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` via a temp file in the same directory, then swap it in."""
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
