"""Typed L1 data contracts (ADR-0003) — every pydantic data model lives here.

Two seam families today: parse-on-read at the JS→Python boundary (the relevance workflow result —
JSON-Schema-validated JS-side but read back from a human-supplied path: :class:`ScoredItem`,
:class:`Lane`), and the publishable trend-series contracts (:class:`WeekCounts` /
:class:`DayCounts` / :class:`MonthCounts`, written as NDJSON to ``public-data/``). The Stage-3
tailor pass's resolved writing-style inputs (:class:`StyleBrief`) live here too. A ``JobRecord``
for the JD record stays a follow-up — Python-produced and Python-consumed, so always well-formed.
``AppSettings`` is config, not a data contract, and stays in :mod:`ajoa_kit.settings`.
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

    Lenient by design (``extra="allow"``, all fields optional) so a new field never drops a row;
    only a wrong-typed item (a non-numeric ``score`` or non-object entry) is dropped at the read
    boundary.
    """

    # extra="allow" keeps unknown workflow fields through model_dump(), so persist's re-write of
    # jobs-scored.json round-trips any field the relevance schema grows beyond the 12 below (#197).
    # The first 10 are the relevance RESULT schema; `stale`/`last_checked` come from refresh (#214).
    model_config = ConfigDict(extra="allow")

    id: str = ""
    title: str = ""
    company: str = ""
    best_lane: str = ""
    score: int | float | None = None
    verdict: str = ""
    rationale: str = ""
    url: str = ""
    # Human-actionable GATE-2 flags (#271): the JD's stated application deadline and a one-phrase
    # hard concern; "" = none. Optional in the JS RESULT schema, typed here (not left as extras) so
    # they survive the model pipeline (persist -> merge -> refresh) and surface in shortlist.md.
    deadline: str = ""
    deal_breaker: str = ""
    # Liveness (#214): the refresh sweep flags an offer that is filled/closed (corpus-delisted or a
    # dead URL re-probe) and stamps when last checked. Typed (not a dropped extra) so the flag
    # survives a persist round-trip and the dashboard can hide stale rows.
    stale: bool = False
    last_checked: str = ""


class WeekCounts(BaseModel):
    """One ISO week's aggregate keyword frequencies — the publishable trends contract.

    The single typed shape written to ``public-data/trends.ndjson``, read by the dashboard's pivot
    layer: ``{week, counts}`` where ``counts`` is ``{keyword: document-frequency}``. No JD content,
    company, title, or per-posting row ever appears here (ADR-0001 PII gate).
    """

    week: str
    counts: dict[str, int]


class DayCounts(BaseModel):
    """One ISO calendar day's aggregate keyword frequencies — the daily-granularity trends contract.

    Written to ``public-data/trends-daily.ndjson`` as ``{date, counts}`` (``YYYY-MM-DD``).
    Same keyword-only, no-PII guarantee as :class:`WeekCounts`; weeks are summed from these days.
    """

    date: str
    counts: dict[str, int]


class MonthCounts(BaseModel):
    """One calendar month's aggregate keyword frequencies — the monthly-granularity contract (#188).

    Written to ``public-data/trends-monthly.ndjson`` as ``{month, counts}`` (``YYYY-MM``).
    Same keyword-only, no-PII guarantee as :class:`WeekCounts`; months are summed from the days.
    """

    month: str
    counts: dict[str, int]


class StyleBrief(BaseModel):
    """Resolved writing-style inputs for the Stage-3 tailor pass (#16).

    Empty strings mean nothing was configured. Loaded from ``config/style.json`` by
    :func:`ajoa_kit.style.load_style` and rendered to the workflow ``style`` arg by
    :func:`ajoa_kit.style.as_directives`.
    """

    tone: str = ""
    cv_sample: str = ""
    cover_letter_sample: str = ""
