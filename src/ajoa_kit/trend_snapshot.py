"""Keyword-only job-market trend snapshot (#11 PR-A).

Derives aggregate keyword-frequency records from the ingested corpus into two series.
``results/trends-daily.ndjson`` holds ``{date, counts}``; ``results/trends.ndjson`` holds
``{week, counts}``, **rolled up from the daily buckets** so the two can't disagree. It prefers the
#164 incremental ``results/corpus.json`` bucketed by each JD's ``first_seen`` (the field we control
and always populate), else falls back to ``results/jobs-raw.json`` with the less-reliable
``posted_at``. So one scrape backfills a real timeline rather than stamping everything with the
run date. ``counts`` is ``{keyword: int}`` — no JD text, company, title, URL, or per-posting row
is ever written. That keeps the data
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
    from collections.abc import Callable
    from pathlib import Path


class WeekCounts(BaseModel):
    """One ISO week's aggregate keyword frequencies — the publishable trends contract.

    The single typed shape written to ``results/trends.ndjson`` and read by the dashboard's pivot
    layer: ``{week, counts}`` where ``counts`` is ``{keyword: document-frequency}``. No JD content,
    company, title, or per-posting row ever appears here (ADR-0001 PII gate).
    """

    week: str
    counts: dict[str, int]


class DayCounts(BaseModel):
    """One ISO calendar day's aggregate keyword frequencies — the daily-granularity trends contract.

    The typed shape written to ``results/trends-daily.ndjson``: ``{date, counts}`` (``YYYY-MM-DD``).
    Same keyword-only, no-PII guarantee as :class:`WeekCounts`; weeks are summed from these days.
    """

    date: str
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


def parse_day(posted_at: str) -> str | None:
    """Map a raw ``posted_at`` to its ISO calendar day ``YYYY-MM-DD``; None if empty/unparseable.

    Same date-dialect handling as :func:`parse_week` (epoch / ISO-8601 / RFC-822), but keyed to the
    day — the finest bucket. Weeks are rolled up from days (:func:`weekly_from_daily`).
    """
    s = (posted_at or "").strip()
    if not s:
        return None
    for parse in _DATE_PARSERS:
        dt = parse(s)
        if dt is not None:
            return dt.date().isoformat()
    return None


def _posted_at(job: dict) -> str:
    """Default ``date_of`` for :func:`bucket_by_week` — bucket by the JD's posted date."""
    return job.get("posted_at", "")


def _first_seen(job: dict) -> str:
    """``date_of`` for the #164 incremental corpus — bucket by when the JD first appeared."""
    return job.get("first_seen", "")


def _bucket(
    jobs: list[dict],
    pattern: re.Pattern[str],
    key_of: Callable[[dict], str | None],
) -> tuple[dict[str, dict[str, int]], int]:
    """Group JDs by ``key_of(job)`` and count keywords per bucket; skip JDs whose key is None.

    Shared core of :func:`bucket_by_day` / :func:`bucket_by_week`. Returns ``({bucket: {keyword:
    document-frequency}}, skipped)`` where ``skipped`` counts JDs with an empty/unparseable date.
    Reuses :func:`extract_counts` per bucket, so per-JD document-frequency semantics are uniform.
    """
    groups: dict[str, list[dict]] = {}
    skipped = 0
    for job in jobs:
        key = key_of(job)
        if key is None:
            skipped += 1
            continue
        groups.setdefault(key, []).append(job)
    return {k: extract_counts(group, pattern) for k, group in groups.items()}, skipped


def bucket_by_day(
    jobs: list[dict],
    pattern: re.Pattern[str],
    date_of: Callable[[dict], str] = _posted_at,
) -> tuple[dict[str, dict[str, int]], int]:
    """Group JDs by the ISO **day** (``YYYY-MM-DD``) of ``date_of`` and count keywords per day.

    The finest-grained, deduped series: :func:`extract_counts` is per-JD document-frequency and,
    bucketed by ``first_seen``, each JD lands in exactly one day — so no keyword is double-counted
    across days. ``date_of`` defaults to ``posted_at``; the daily/weekly cron passes ``first_seen``.
    """
    return _bucket(jobs, pattern, lambda j: parse_day(date_of(j)))


def weekly_from_daily(day_counts: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """Roll daily ``{date: counts}`` up into ``{week: counts}`` by summing each ISO week's days.

    Exact because each JD sits in exactly one ``first_seen`` day (hence one week): summing the
    per-day document-frequencies reproduces the weekly document-frequency with no double-counting.
    """
    weeks: dict[str, dict[str, int]] = {}
    for date_str, counts in day_counts.items():
        # Defensive: day keys from parse_day are always valid ISO dates, so parse_week never returns
        # None here in practice — this guards only a stray non-date key from a future caller.
        week = parse_week(date_str)
        if week is None:
            continue
        bucket = weeks.setdefault(week, {})
        for term, c in counts.items():
            bucket[term] = bucket.get(term, 0) + c
    return weeks


def bucket_by_week(
    jobs: list[dict],
    pattern: re.Pattern[str],
    date_of: Callable[[dict], str] = _posted_at,
) -> tuple[dict[str, dict[str, int]], int]:
    """Group JDs by ISO week — derived from :func:`bucket_by_day` so weekly == sum of daily.

    ``weekly_from_daily(bucket_by_day(...))``: one bucketing pass, and the two published series can
    never disagree. ``date_of`` picks the date field (default ``posted_at``); e.g.
    ``lambda j: j.get("last_modified") or j.get("posted_at", "")`` for activity-dating — a
    deliberate, test-exercised seam (``main()`` passes ``first_seen`` / ``posted_at``). Returns
    ``({week: {keyword: document-frequency}}, skipped)``.
    """
    days, skipped = bucket_by_day(jobs, pattern, date_of)
    return weekly_from_daily(days), skipped


def _upsert(path: Path, key_field: str, record: dict) -> None:
    """Append one NDJSON ``record``, replacing any line with the same ``record[key_field]``.

    Idempotent per key — re-running for the same week/day overwrites that record.
    """
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    key = record[key_field]
    kept: list[str] = []
    if path.is_file():
        # Split on "\n" only — NOT str.splitlines(), which also breaks on Unicode line
        # separators (NEL \x85, LS, PS) that json.dumps leaves unescaped, corrupting a record.
        kept = [
            ln
            for ln in path.read_text().split("\n")
            if ln.strip() and json.loads(ln).get(key_field) != key
        ]
    kept.append(line)
    path.write_text("\n".join(kept) + "\n")


def upsert_week(path: Path, week: str, counts: dict[str, int]) -> None:
    """Append/replace one ``{week, counts}`` NDJSON record (idempotent per ISO week)."""
    _upsert(path, "week", WeekCounts(week=week, counts=counts).model_dump())


def upsert_day(path: Path, date: str, counts: dict[str, int]) -> None:
    """Append/replace one ``{date, counts}`` NDJSON record (idempotent per ISO day)."""
    _upsert(path, "date", DayCounts(date=date, counts=counts).model_dump())


def main() -> None:
    """Backfill per-ISO-week and per-day keyword frequencies into results/trends{,-daily}.ndjson.

    Buckets the corpus by day **once** (the deduped, finest-grained series) and rolls weeks up from
    it (:func:`weekly_from_daily`), so the two series can't disagree. Prefers the #164 incremental
    ``results/corpus.json`` bucketed by each JD's ``first_seen``; falls back to
    ``results/jobs-raw.json`` by ``posted_at`` when no corpus exists yet. Both outputs are aggregate
    keyword-only (no JD content) — publishable.
    """
    settings = AppSettings()
    results = settings.results_dir
    corpus_path = results / "corpus.json"
    if corpus_path.is_file():
        jobs = json.loads(corpus_path.read_text())
        date_of, dated_by = _first_seen, "first_seen"
    else:
        jobs = json.loads((results / "jobs-raw.json").read_text())
        date_of, dated_by = _posted_at, "posted_at"
    interest, title_roles = load_keywords(settings.config_dir)
    pat_interest, _ = build_patterns(interest, title_roles)
    days, skipped = bucket_by_day(jobs, pat_interest, date_of=date_of)
    weeks = weekly_from_daily(days)
    weekly_path = results / "trends.ndjson"
    daily_path = results / "trends-daily.ndjson"
    for week, counts in weeks.items():
        upsert_week(weekly_path, week, counts)
    for day, counts in days.items():
        upsert_day(daily_path, day, counts)
    print(
        f"backfilled {len(weeks)} ISO weeks -> {weekly_path} and {len(days)} days -> {daily_path} "
        f"(by {dated_by}; skipped {skipped} JDs with no parseable date)"
    )


if __name__ == "__main__":
    main()
