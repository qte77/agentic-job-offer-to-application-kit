"""Company-hiring trend series (#2 / plan 006 S2a) — new roles seen per bucket, two views.

Mirrors :mod:`ajoa_kit.trend_snapshot` but counts *jobs per bucket key* instead of keyword document
frequency. Each corpus JD is bucketed by its ``first_seen`` day (reusing that module's date parsing,
day->week/month roll-ups, and idempotent NDJSON upserts), then counted once — so this measures the
**intake** (flow of newly-seen roles per bucket), matching the companies-tab momentum semantics, not
the count of currently-open roles.

Two views come out of one corpus:

- **Publishable geo x field** -> ``public-data/hiring-{weekly,daily,monthly}.ndjson`` as
  ``{week|date|month, counts}`` where each ``counts`` key is ``"<city>, <region> · <field>"``
  (region omitted when absent). **No company names** — non-copyrightable aggregate facts, the same
  bar the keyword trends clear (ADR-0001 PII gate / ADR-0002 ToU). Published via the trends
  ``data``-branch path; the Makefile boundary guard structurally refuses anything else.
- **Local per-company** -> ``results/hiring-companies.ndjson`` as ``{week, counts:{company: n}}``.
  Business data: git-ignored, bundled into ``make preview`` only, NEVER published.

Run::

    ajoa-kit companies-snapshot
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit.companies import _field, parse_geo
from ajoa_kit.settings import AppSettings
from ajoa_kit.trend_snapshot import (
    monthly_from_daily,
    parse_day,
    upsert_day,
    upsert_month,
    upsert_week,
    weekly_from_daily,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Separator between the geo qualifier and the field in a publishable bucket key. A middle dot (·)
# mirrors the dashboard's geo rendering; it lives only inside the JSON value, never a path.
_SEP = " · "


def geo_field_key(job: dict, lane_by_id: dict[str, str]) -> str:
    """Build the publishable ``"<city>, <region> · <field>"`` bucket key (region omitted if absent).

    Reuses :func:`ajoa_kit.companies.parse_geo` (canonical city + qualifier) and
    :func:`ajoa_kit.companies._field` (scored lane -> ``lane_hint`` -> ``"unscored"``). Carries no
    company name by construction — this is what may reach the ``data`` branch.
    """
    city, region = parse_geo(job.get("location", ""), job.get("remote"))
    geo = f"{city}, {region}" if region else city
    return f"{geo}{_SEP}{_field(job, lane_by_id)}"


def company_key(job: dict) -> str:
    """Local per-company bucket key; ``""`` for a blank company (skipped — nothing to attribute)."""
    return (job.get("company") or "").strip()


def count_by(jobs: list[dict], key_of: Callable[[dict], str]) -> dict[str, int]:
    """Count jobs per ``key_of(job)`` — each JD once. Blank/empty keys are skipped.

    The hiring analogue of :func:`ajoa_kit.trend_snapshot.extract_counts`: no keyword regex and no
    per-JD dedup needed, because each JD maps to exactly one bucket key.
    """
    counts: dict[str, int] = {}
    for job in jobs:
        key = key_of(job)
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


def bucket_by_day(
    jobs: list[dict], key_of: Callable[[dict], str]
) -> tuple[dict[str, dict[str, int]], int]:
    """Group JDs by ``first_seen`` ISO day and count them per ``key_of`` bucket within each day.

    Returns ``({date: {bucket-key: job-count}}, skipped)`` where ``skipped`` counts JDs whose
    ``first_seen`` is empty/unparseable. Weeks and months roll up from these days (via
    :mod:`ajoa_kit.trend_snapshot`) so the three published series can never disagree.
    """
    groups: dict[str, list[dict]] = {}
    skipped = 0
    for job in jobs:
        day = parse_day(job.get("first_seen", ""))
        if day is None:
            skipped += 1
            continue
        groups.setdefault(day, []).append(job)
    return {day: count_by(group, key_of) for day, group in groups.items()}, skipped


def main() -> None:
    """Snapshot the corpus into the publishable geo-x-field trio + the local per-company series.

    Reads ``results/corpus.json`` (each record already carries ``first_seen`` + ``company`` +
    ``location`` + ``lane_hint`` — no re-scrape). No shortlist context here, so the field falls back
    to ``lane_hint`` / ``"unscored"`` (an empty ``lane_by_id``), keeping the series deterministic.
    """
    settings = AppSettings()
    results = settings.results_dir
    corpus_path = results / "corpus.json"
    if not corpus_path.is_file():
        print(f"no {corpus_path} yet — run ingest first; nothing to snapshot")
        return
    jobs = json.loads(corpus_path.read_text())
    lanes: dict[str, str] = {}
    public = settings.public_data_dir
    public.mkdir(parents=True, exist_ok=True)

    # Publishable geo x field: bucket by day, roll up weeks/months, upsert the trio (no PII).
    geo_days, skipped = bucket_by_day(jobs, lambda j: geo_field_key(j, lanes))
    geo_weeks = weekly_from_daily(geo_days)
    geo_months = monthly_from_daily(geo_days)
    for week, counts in geo_weeks.items():
        upsert_week(public / "hiring-weekly.ndjson", week, counts)
    for day, counts in geo_days.items():
        upsert_day(public / "hiring-daily.ndjson", day, counts)
    for month, counts in geo_months.items():
        upsert_month(public / "hiring-monthly.ndjson", month, counts)

    # Local per-company weekly — business data; stays under git-ignored results/, never published.
    company_weeks = weekly_from_daily(bucket_by_day(jobs, company_key)[0])
    local_path = results / "hiring-companies.ndjson"
    for week, counts in company_weeks.items():
        upsert_week(local_path, week, counts)

    print(
        f"hiring: {len(geo_weeks)} public weeks -> {public}/hiring-weekly.ndjson (+daily/monthly), "
        f"{len(company_weeks)} weeks per-company -> {local_path} (skipped {skipped} undated JDs)"
    )


if __name__ == "__main__":
    main()
