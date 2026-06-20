"""Keyword-only job-market trend snapshot (#11 PR-A).

Derives an aggregate, per-ISO-week keyword-frequency record from the ingested corpus
(``results/jobs-raw.json``) and upserts it into ``results/trends.ndjson``. Each JD is bucketed by
the ISO week it was actually **posted** (its ``posted_at``), so a single scrape backfills a real
multi-week timeline rather than stamping the whole corpus with the run date. The output is
**keyword-only by construction** — ``{week, counts}`` where ``counts`` is ``{keyword: int}``;
no JD text, company, title, URL, or per-posting row is ever written. That keeps the data
publishable without tripping the ADR-0001 PII gate (`pseudonymize-text` stays belt-and-suspenders).

Backfill is **survivorship-biased**: live boards only expose currently-open postings, so recent
weeks are fuller than older ones (filled/closed roles have dropped off). Re-running accumulates
weeks over time (``upsert_week`` replaces a week in place, preserving others).

The pre-filter vocabulary comes from :func:`ajoa_kit.ingest.load_keywords` (config-overridable),
so a consumer can drive which keywords are tracked. Run::

    ajoa-kit trend-snapshot
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from ajoa_kit.ingest import build_patterns, load_keywords
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    import re
    from pathlib import Path


class WeekCounts(BaseModel):
    """One ISO week's aggregate keyword frequencies — the publishable trends contract.

    The single typed shape written to ``results/trends.ndjson`` and read by the dashboard's pivot
    layer: ``{week, counts}`` where ``counts`` is ``{keyword: document-frequency}``. No JD content,
    company, title, or per-posting row ever appears here (ADR-0001 PII gate).
    """

    week: str
    counts: dict[str, int]


def extract_counts(jobs: list[dict], pattern: re.Pattern[str]) -> dict[str, int]:
    """Per-keyword document frequency across JDs (word-boundary, case-insensitive match).

    A keyword repeated within one JD counts once (per-JD set), so a verbose posting cannot skew the
    trend. Returns ``{keyword: count}`` only — never any JD content.
    """
    counts: dict[str, int] = {}
    for job in jobs:
        text = f"{job.get('title', '')} {job.get('description', '')}"
        for term in {m.lower() for m in pattern.findall(text)}:
            counts[term] = counts.get(term, 0) + 1
    return counts


def _from_epoch(s: str) -> datetime | None:
    """Parse an all-digit Unix timestamp; >= 1e12 means milliseconds (lever), else seconds."""
    if not s.isdigit():
        return None
    try:
        ts = int(s)
        if ts >= 10**12:
            ts //= 1000
        return datetime.fromtimestamp(ts, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def _from_iso(s: str) -> datetime | None:
    """Parse ISO-8601 (incl. date-only and a trailing ``Z``)."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _from_rfc822(s: str) -> datetime | None:
    """Parse an RFC-822 date (RSS ``pubDate``)."""
    try:
        return parsedate_to_datetime(s)
    except (ValueError, TypeError):
        return None


_DATE_PARSERS = (_from_epoch, _from_iso, _from_rfc822)


def parse_week(posted_at: str) -> str | None:
    """Map a raw ``posted_at`` to its ISO week ``YYYY-Www``; None if empty/unparseable.

    Tries each adapter's date dialect in turn — epoch seconds/milliseconds, ISO-8601, then
    RFC-822. Empty or unparseable input returns None so the caller can skip-and-count it
    (per-record wrap-continue), never guessing a week. Bucketing by the *posted* week is what
    lets one scrape backfill a real timeline instead of stamping everything with the run date.
    """
    s = (posted_at or "").strip()
    if not s:
        return None
    for parse in _DATE_PARSERS:
        dt = parse(s)
        if dt is not None:
            year, week_no, _ = dt.isocalendar()
            return f"{year}-W{week_no:02d}"
    return None


def bucket_by_week(
    jobs: list[dict], pattern: re.Pattern[str]
) -> tuple[dict[str, dict[str, int]], int]:
    """Group JDs by the ISO week of their ``posted_at`` and count keywords per week.

    Returns ``({week: {keyword: document-frequency}}, skipped)`` where ``skipped`` counts JDs with
    no parseable ``posted_at`` (they can't be placed in time). Reuses :func:`extract_counts` per
    week, so the per-JD document-frequency semantics match the single-week path.
    """
    by_week: dict[str, list[dict]] = {}
    skipped = 0
    for job in jobs:
        week = parse_week(job.get("posted_at", ""))
        if week is None:
            skipped += 1
            continue
        by_week.setdefault(week, []).append(job)
    return {week: extract_counts(group, pattern) for week, group in by_week.items()}, skipped


def upsert_week(path: Path, week: str, counts: dict[str, int]) -> None:
    """Append one ``{week, counts}`` NDJSON record, replacing any existing same-week line.

    Idempotent: re-running for the same ISO week overwrites that week's record.
    """
    record = json.dumps(
        WeekCounts(week=week, counts=counts).model_dump(), ensure_ascii=False, sort_keys=True
    )
    kept: list[str] = []
    if path.is_file():
        # Split on "\n" only — NOT str.splitlines(), which also breaks on Unicode line
        # separators (NEL \x85, LS, PS) that json.dumps leaves unescaped, corrupting a record.
        kept = [
            line
            for line in path.read_text().split("\n")
            if line.strip() and json.loads(line).get("week") != week
        ]
    kept.append(record)
    path.write_text("\n".join(kept) + "\n")


def main() -> None:
    """Backfill per-ISO-week keyword frequencies (by JD posted_at) into results/trends.ndjson."""
    settings = AppSettings()
    results = settings.results_dir
    jobs = json.loads((results / "jobs-raw.json").read_text())
    interest, title_roles = load_keywords(settings.config_dir)
    pat_interest, _ = build_patterns(interest, title_roles)
    weeks, skipped = bucket_by_week(jobs, pat_interest)
    path = results / "trends.ndjson"
    for week, counts in weeks.items():
        upsert_week(path, week, counts)
    print(
        f"backfilled {len(weeks)} ISO weeks -> {path} "
        f"(skipped {skipped} JDs with no parseable posted_at)"
    )


if __name__ == "__main__":
    main()
