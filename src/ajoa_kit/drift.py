"""Detect offer packs whose rendered files no longer match their ``result.json`` source (#366).

Rendering is a pure function of the pack's source, so the check re-runs
:func:`ajoa_kit.persist_offer.write_pack` into a throwaway directory and compares the rendered
artifacts with the files on disk. Run::

    ajoa-kit drift-check

Per pack under ``results/offers/``: ``clean``, ``drifted`` (naming the files), ``no source``
(persisted before #365 kept ``result.json``; expected, never a failure) or ``invalid source``
(``result.json`` no longer renders). Report only: nothing in a pack is written or deleted, since a
hand edit may be the better text, and the fix is then to move it into ``result.json``.

Compared: the five :data:`~ajoa_kit.persist_offer.ARTIFACTS` plus ``coverage-report.md``. Not
compared: the review sidecars (``cv-ats-check.md`` and the rest of ``CHECKS``), which also read
``jobs-raw.json`` and the evidence library, and ``meta.json``, which records the pull date.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ajoa_kit.persist_offer import ARTIFACTS, SOURCE, write_pack
from ajoa_kit.settings import AppSettings

# Files that are a pure function of result.json, so any difference is drift.
RENDERED = [filename for _, filename, _ in ARTIFACTS] + ["coverage-report.md"]


class PackDrift(BaseModel):
    """One pack's drift verdict."""

    slug: str
    status: Literal["clean", "drifted", "no source", "invalid source"]
    files: list[str] = []


def _read(path: Path) -> str | None:
    return path.read_text() if path.is_file() else None


def check_pack(offer_dir: Path) -> PackDrift:
    """Re-render one pack from its ``result.json`` and diff the rendered files against disk."""
    slug = offer_dir.name
    if not (offer_dir / SOURCE).is_file():
        return PackDrift(slug=slug, status="no source")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            pack = json.loads((offer_dir / SOURCE).read_text())
            fresh = write_pack(pack, slug=slug, results_dir=Path(tmp))
        except (ValueError, TypeError, AttributeError):  # bad JSON or a pack that won't render
            return PackDrift(slug=slug, status="invalid source")
        changed = sorted(f for f in RENDERED if _read(fresh / f) != _read(offer_dir / f))
    return PackDrift(slug=slug, status="drifted" if changed else "clean", files=changed)


def check_offers(results_dir: Path) -> list[PackDrift]:
    """Check every pack under ``results_dir/offers/``, sorted by slug."""
    offers = results_dir / "offers"
    dirs = sorted(p for p in offers.iterdir() if p.is_dir()) if offers.is_dir() else []
    return [check_pack(d) for d in dirs]


def main(results_dir: Path | None = None) -> int:
    """Print one line per pack; return 1 when any pack drifted or has an invalid source."""
    reports = check_offers(results_dir or AppSettings().results_dir)
    for r in reports:
        print(f"{r.slug}: {r.status}" + (f" ({', '.join(r.files)})" if r.files else ""))
    bad = [r for r in reports if r.status in ("drifted", "invalid source")]
    print(f"{len(reports)} packs checked, {len(bad)} need attention")
    return 1 if bad else 0
