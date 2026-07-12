"""Local application-outcome tracker (#273) — a per-offer ``status.json`` a human sets by hand.

Records how far each application has progressed (stage / date / notes) under the git-ignored PII
boundary (``results/offers/<slug>/status.json``), never published — closing the apply -> outcome
loop the offer packs left open. Pure read/write logic; :func:`main` resolves the offer dir from
``AppSettings`` and backs the ``ajoa-kit status`` CLI verb (set when any field is given, else read).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit.models import OfferStatus
from ajoa_kit.persist_offer import safe_slug
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from pathlib import Path

_STATUS_FILE = "status.json"
# The pipeline the CLI documents; ``stage`` is free text but these are the expected values.
STAGES = ("applied", "responded", "interview", "offer", "rejected")


def read_status(offer_dir: Path) -> OfferStatus:
    """Read ``offer_dir/status.json`` into an :class:`OfferStatus` (absent file -> empty status).

    Fail-loud on a present-but-malformed file — it is Python-written, so corruption is a bug, not
    tolerated input (matches :func:`ajoa_kit.persist_scored.load_shortlist`).
    """
    path = offer_dir / _STATUS_FILE
    if not path.is_file():
        return OfferStatus()
    return OfferStatus.model_validate(json.loads(path.read_text()))


def set_status(
    offer_dir: Path,
    *,
    stage: str | None = None,
    date: str | None = None,
    notes: str | None = None,
) -> OfferStatus:
    """Update ``status.json`` with the provided fields (others preserved) and return the result."""
    fields = {"stage": stage, "date": date, "notes": notes}
    changed = {k: v for k, v in fields.items() if v is not None}
    updated = read_status(offer_dir).model_copy(update=changed)
    offer_dir.mkdir(parents=True, exist_ok=True)
    (offer_dir / _STATUS_FILE).write_text(json.dumps(updated.model_dump(), indent=2) + "\n")
    return updated


def main(
    offer: str | None = None,
    *,
    stage: str | None = None,
    date: str | None = None,
    notes: str | None = None,
) -> None:
    """Set (when any field is given) or read a local offer's application status, then print it.

    ``offer`` is the offer slug (the ``results/offers/<slug>/`` dir name). Reads args from argv when
    called directly; ``ajoa-kit status`` passes them in.
    """
    if offer is None:
        import argparse

        parser = argparse.ArgumentParser(prog="ajoa-kit status")
        parser.add_argument("offer", help="offer slug (the results/offers/<slug>/ dir)")
        parser.add_argument("--stage", default=None, help=f"one of: {', '.join(STAGES)}")
        parser.add_argument("--date", default=None, help="application/update date (YYYY-MM-DD)")
        parser.add_argument("--notes", default=None, help="free-text note")
        ns = parser.parse_args()
        offer, stage, date, notes = str(ns.offer), ns.stage, ns.date, ns.notes
    offer_dir = AppSettings().results_dir / "offers" / safe_slug(offer)
    setting = stage is not None or date is not None or notes is not None
    st = (
        set_status(offer_dir, stage=stage, date=date, notes=notes)
        if setting
        else read_status(offer_dir)
    )
    verb = "updated" if setting else "status"
    print(f"{verb} {offer}: stage={st.stage or '-'} date={st.date or '-'} notes={st.notes or '-'}")


if __name__ == "__main__":
    main()
