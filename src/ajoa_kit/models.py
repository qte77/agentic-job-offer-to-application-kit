"""Typed L1 data contracts (ADR-0003) — pydantic models for parse-on-read at the JS→Python seams.

Only what re-enters Python from a file needs one today: the relevance workflow result, JSON-Schema
-validated JS-side but read back here from a human-supplied path. Other boundaries (a ``JobRecord``
for the JD record, config-entry models) are follow-ups — the JD record is Python-produced and
Python-consumed, so always well-formed; it needs no guard.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Lane(BaseModel):
    """One position lane — the canonical lane definition (ADR-0003 lane SSOT).

    The authoritative set lives in ``config/lanes.json`` and is loaded by
    :func:`ajoa_kit.ingest.load_lanes`; the two JS workflow scripts carry an in-code copy only as a
    no-config fallback. ``gap_hint`` uses the ``gapHint`` alias so a lane round-trips to the exact
    ``{key,label,focus,gapHint}`` shape the workflows expect as ``args.lanes``.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    focus: str
    gap_hint: str = Field(alias="gapHint")


class ScoredItem(BaseModel):
    """One scored JD from the relevance workflow.

    Lenient by design (``extra="ignore"``, all fields optional) so a new field never drops a row;
    only a wrong-typed item (a non-numeric ``score`` or non-object entry) is dropped at the read
    boundary.
    """

    # extra="ignore" lets unknown workflow fields pass, but they're dropped from model_dump() — so
    # persist's jobs-scored.json re-write loses any field beyond the 10 below. The first 8 are the
    # relevance RESULT schema; `stale`/`last_checked` are added by the refresh sweep (#214). Use
    # extra="allow" for forward-compat round-tripping of any other future field (#197).
    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    company: str = ""
    best_lane: str = ""
    score: int | float | None = None
    verdict: str = ""
    rationale: str = ""
    url: str = ""
    # Liveness (#214): the refresh sweep flags an offer that is filled/closed (corpus-delisted or a
    # dead URL re-probe) and stamps when last checked. Typed (not a dropped extra) so the flag
    # survives a persist round-trip and the dashboard can hide stale rows.
    stale: bool = False
    last_checked: str = ""
