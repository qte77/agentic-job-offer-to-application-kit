"""Local company-hiring tracker aggregation (#284) — who's hiring, by geo x field.

Pure text/aggregate logic (mirrors :mod:`ajoa_kit.normalize`: no network, no file I/O). Folds the
running corpus (:func:`ajoa_kit.corpus.merge_corpus` records) into
:class:`ajoa_kit.models.CompanyRow` counts. The free-text ``location`` is parsed to a canonical
``(city, region)`` — duplicate spellings collapse into one *city* bucket so the ranking isn't split,
while the state/country *qualifier* is KEPT for display; the corpus itself is never modified, so no
source information is lost. Momentum (heating/cooling) stays ``None`` until the history is deep.

LOCAL-ONLY by construction: the caller writes the result into ``make preview``'s throwaway copy,
never to the published ``data`` branch (the boundary guard forbids company data there).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

from ajoa_kit.models import CompanyRow

# Duplicate-spelling / abbreviation merges (lowercased primary segment -> canonical city). Only
# genuine same-place variants the corpus actually contains — cross-language (München/Munich) and
# abbreviations (SF, NYC) the comma/accent split alone cannot unify. The long tail is left as-is:
# singletons cannot move a top-N ranking, so normalizing them is wasted effort.
_CITY_ALIASES = {
    "sf": "San Francisco",
    "nyc": "New York",
    "new york city": "New York",
    "bangalore": "Bengaluru",
    "münchen": "Munich",
    "köln": "Cologne",
    "usa": "United States",
}
_MULTI = re.compile(r"[|•]")  # separators between *distinct* locations (not city/qualifier)

_Key = tuple[str, str, str]  # (city, field, company)


def _is_remote(location: str, remote: object) -> bool:
    """Remote when the location says so, or the location is blank and the record's flag is set."""
    return "remote" in location.lower() or (not location.strip() and bool(remote))


def parse_geo(location: str, remote: object = None) -> tuple[str, str]:
    """Parse a free-text ``location`` into a canonical ``(city, region)`` — lossless by design.

    ``city`` is the group key (duplicate spellings collapse via :data:`_CITY_ALIASES`); ``region``
    keeps the source's verbatim next qualifier (state/country), ``""`` when absent. ``remote`` is
    the record's flag: an empty location with it set is the ``Remote`` bucket, a fully empty
    location is ``Unknown``. Multi-location strings (``|`` / ``•``) take the primary location.
    """
    loc = location or ""
    if _is_remote(loc, remote):
        return "Remote", ""
    primary = _MULTI.split(loc)[0]
    parts = [p.strip() for p in primary.split(",")]
    city = parts[0]
    if not city:
        return "Unknown", ""
    region = parts[1] if len(parts) > 1 and parts[1] else ""
    return _CITY_ALIASES.get(city.lower(), city), region


def _reference_date(corpus: list[dict]) -> date | None:
    """Newest ``last_seen`` in the corpus — the recency anchor (avoids reading the wall clock)."""
    seens = [date.fromisoformat(r["last_seen"]) for r in corpus if r.get("last_seen")]
    return max(seens) if seens else None


def _is_active(rec: dict, ref: date | None, active_days: int) -> bool:
    """A role is active when its ``last_seen`` is within ``active_days`` of the newest pull."""
    ls = rec.get("last_seen")
    if not ls or ref is None:
        return True
    return (ref - date.fromisoformat(ls)).days <= active_days


def _field(rec: dict, lane_by_id: dict[str, str]) -> str:
    """Field fallback: scored lane (shortlist) -> ingest ``lane_hint`` -> ``unscored``."""
    return lane_by_id.get(rec.get("id", "")) or rec.get("lane_hint") or "unscored"


def _history_span_days(corpus: list[dict]) -> int:
    """Calendar span between the earliest and latest ``first_seen`` — the history depth proxy."""
    firsts = [date.fromisoformat(r["first_seen"]) for r in corpus if r.get("first_seen")]
    return (max(firsts) - min(firsts)).days if firsts else 0


def _momentum(first_seens: list[date], ref: date) -> str:
    """Heating/cooling/steady: this company's role intake in the last 14 days vs the prior 14."""
    recent = sum(1 for d in first_seens if 0 <= (ref - d).days <= 14)
    prior = sum(1 for d in first_seens if 14 < (ref - d).days <= 28)
    if recent > prior:
        return "heating"
    if recent < prior:
        return "cooling"
    return "steady"


# Below this history span the delta is noise, so the snapshot ships without a momentum claim (~4wk).
_MIN_MOMENTUM_SPAN_DAYS = 28


def aggregate_companies(
    corpus: list[dict],
    lane_by_id: dict[str, str] | None = None,
    active_days: int = 7,
) -> list[CompanyRow]:
    """Aggregate active corpus roles into per-(city, field, company) :class:`CompanyRow` counts.

    ``lane_by_id`` maps JD id -> scored ``best_lane`` (from the non-stale shortlist); it refines the
    field over the coarse ingest ``lane_hint``. ``region`` surfaces the modal qualifier for the
    merged city. ``momentum`` is ``None`` unless the corpus spans ~4+ weeks of ``first_seen``.
    """
    lanes = lane_by_id or {}
    ref = _reference_date(corpus)
    counts: Counter[_Key] = Counter()
    regions: dict[_Key, Counter[str]] = defaultdict(Counter)
    firsts: dict[_Key, list[date]] = defaultdict(list)

    for rec in corpus:
        if not _is_active(rec, ref, active_days):
            continue
        city, region = parse_geo(rec.get("location", ""), rec.get("remote"))
        key: _Key = (city, _field(rec, lanes), rec.get("company", ""))
        counts[key] += 1
        if region:
            regions[key][region] += 1
        fs = rec.get("first_seen")
        if fs:
            firsts[key].append(date.fromisoformat(fs))

    ref_for_momentum = (
        ref if ref and _history_span_days(corpus) >= _MIN_MOMENTUM_SPAN_DAYS else None
    )
    rows = [
        CompanyRow(
            city=city,
            region=regions[key].most_common(1)[0][0] if regions[key] else "",
            field=field,
            company=company,
            count=count,
            momentum=_momentum(firsts[key], ref_for_momentum) if ref_for_momentum else None,
        )
        for key in counts
        for (city, field, company), count in [(key, counts[key])]
    ]
    rows.sort(key=lambda r: (r.city, r.field, -r.count, r.company))
    return rows
