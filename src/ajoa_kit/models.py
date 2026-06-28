"""Typed L1 data contracts (ADR-0003) — pydantic models for parse-on-read at the JS→Python seams.

Only what re-enters Python from a file needs one today: the relevance workflow result, JSON-Schema
-validated JS-side but read back here from a human-supplied path. Other boundaries (a ``JobRecord``
for the JD record, config-entry models) are follow-ups — the JD record is Python-produced and
Python-consumed, so always well-formed; it needs no guard.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScoredItem(BaseModel):
    """One scored JD from the relevance workflow.

    Lenient by design (``extra="ignore"``, all fields optional) so a new field never drops a row;
    only a wrong-typed item (a non-numeric ``score`` or non-object entry) is dropped at the read
    boundary.
    """

    # extra="ignore" lets unknown workflow fields pass, but they're dropped from model_dump() — so
    # persist_scored's jobs-scored.json re-write loses any field beyond the 8 below. None today (the
    # RESULT schema is exactly these); use extra="allow" for forward-compat round-tripping (#197).
    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    company: str = ""
    best_lane: str = ""
    score: int | float | None = None
    verdict: str = ""
    rationale: str = ""
    url: str = ""
