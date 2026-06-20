"""Keyword-only job-market trend snapshot (#11 PR-A).

Derives an aggregate, per-ISO-week keyword-frequency record from the ingested corpus
(``results/jobs-raw.json``) and appends it to ``results/trends.ndjson``. The output is
**keyword-only by construction** — ``{week, counts}`` where ``counts`` is ``{keyword: int}``;
no JD text, company, title, URL, or per-posting row is ever written. That keeps the data
publishable without tripping the ADR-0001 PII gate (`pseudonymize-text` stays belt-and-suspenders).

The pre-filter vocabulary comes from :func:`ajoa_kit.ingest.load_keywords` (config-overridable),
so a consumer can drive which keywords are tracked. Run::

    ajoa-kit trend-snapshot
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from ajoa_kit.ingest import build_patterns, load_keywords
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    import re
    from pathlib import Path


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


def upsert_week(path: Path, week: str, counts: dict[str, int]) -> None:
    """Append one ``{week, counts}`` NDJSON record, replacing any existing same-week line.

    Idempotent: re-running for the same ISO week overwrites that week's record.
    """
    record = json.dumps({"week": week, "counts": counts}, ensure_ascii=False, sort_keys=True)
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
    """Snapshot this ISO week's keyword frequencies into results/trends.ndjson."""
    settings = AppSettings()
    results = settings.results_dir
    jobs = json.loads((results / "jobs-raw.json").read_text())
    interest, title_roles = load_keywords(settings.config_dir)
    pat_interest, _ = build_patterns(interest, title_roles)
    year, week_no, _ = date.today().isocalendar()
    week = f"{year}-W{week_no:02d}"
    counts = extract_counts(jobs, pat_interest)
    path = results / "trends.ndjson"
    upsert_week(path, week, counts)
    print(f"wrote keyword trend for {week} -> {path} ({len(counts)} keywords)")


if __name__ == "__main__":
    main()
