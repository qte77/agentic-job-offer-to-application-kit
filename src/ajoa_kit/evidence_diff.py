"""Detect evidence-library drift across rebuilds (#414).

Rebuilding ``evidence-library.json`` rewords fields (``gapNarrative`` most visibly), so packs
tailored against an older build can quote text the current library no longer holds. Two parts:

- :func:`library_stamp` is the library's version: a short sha256 of the file's bytes.
  ``persist-offer`` records it in each pack's ``meta.json`` as ``evidence_library``, so a pack
  whose stamp differs from the current library's was tailored against an older build. Being a
  content hash, it needs no change to the Stage-1 Workflow (which cannot write files) and no file
  can disagree with its own stamp.
- ``ajoa-kit evidence-diff OLD [NEW]`` names the top-level fields a rebuild added, removed or
  changed, so a human sees what went stale before old packs are read. Run::

    ajoa-kit evidence-diff results/evidence-library.2026-06-29.json
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from pathlib import Path

STAMP_LEN = 12


def library_stamp(path: Path) -> str:
    """Return the library's version stamp (sha256 prefix of its bytes); "" when it is missing."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:STAMP_LEN]
    except OSError:
        return ""


def diff_fields(old: dict, new: dict) -> dict[str, list[str]]:
    """Name the top-level fields ``new`` added, removed or changed relative to ``old``."""
    return {
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "changed": sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
    }


def main(old: Path, new: Path | None = None) -> None:
    """Print both stamps and the changed top-level fields (``new`` defaults to the live library)."""
    new = new or AppSettings().results_dir / "evidence-library.json"
    print(f"old {library_stamp(old)}  {old}")
    print(f"new {library_stamp(new)}  {new}")
    diff = diff_fields(json.loads(old.read_text()), json.loads(new.read_text()))
    for kind, fields in diff.items():
        if fields:
            print(f"{kind}: {', '.join(fields)}")
    if not any(diff.values()):
        print("no top-level field changed")
