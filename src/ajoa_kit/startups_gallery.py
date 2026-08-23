"""startups.gallery discovery adapter: rendered jobs page -> typed cards -> ATS refs.

startups.gallery is a broad startup-jobs index (Framer, HTML-only, no API) whose cards link straight
to each company's own ATS (Ashby/Greenhouse/Lever). It is used as a DISCOVERY source: parse the
apply links, recover the underlying ``(ats, slug)``, and hand NEW slugs to the first-party ATS
ingest -- clean JDs and natural dedup -- rather than scraping the aggregator's coarse cards as
terminal JDs.

ToS (ADR-0002): CAUTION. ``robots.txt`` is ``Allow: /`` but the site publishes no ToS, so access is
read-only public GET only, patchright-rendered via :mod:`polyfetch_scrape` (lazy-imported). The pure
parse/derive logic is offline-testable; the render orchestrator runs behind a live smoke test.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlencode, urlsplit

from ajoa_kit.models import AtsRef, SgFilters, SgJob
from ajoa_kit.normalize import html_to_text

if TYPE_CHECKING:
    from collections.abc import Iterable

SG_JOBS_URL = "https://startups.gallery/jobs"

# Anchor cards: <a href="<ats-url>"> ...title node... "Company . Location . Posted on <date>" </a>.
# The title is a separate node; the middot-delimited meta line carries company/location/posted
# (confirmed live 2026-08-22, ADR-0004 Phase 2).
_ANCHOR = re.compile(r"<a\b[^>]*\bhref=\"(?P<href>[^\"]+)\"[^>]*>(?P<inner>.*?)</a>", re.I | re.S)
_BULLET = "·"  # the middot delimiter between card fields
# A clean first-party ATS board slug: alnum start, then alnum/dot/dash/underscore (no spaces).
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Apply-URL host -> ATS name; the board slug is the first path segment. Confirmed card hosts.
_ATS_HOSTS: dict[str, str] = {
    "jobs.ashbyhq.com": "ashby",
    "job-boards.greenhouse.io": "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
}


def build_jobs_url(filters: SgFilters) -> str:
    """Compose the ``/jobs`` URL with only the non-empty filters, as hyphenated query params."""
    params = {
        "location": filters.location,
        "job-title": filters.job_title,
        "company-name": filters.company_name,
    }
    query = urlencode({k: v for k, v in params.items() if v})
    return f"{SG_JOBS_URL}?{query}" if query else SG_JOBS_URL


def derive_ats_ref(url: str) -> AtsRef | None:
    """Recover ``(ats, slug)`` from an ATS apply URL, or ``None`` if unrecognized/not-clean."""
    parts = urlsplit(url)
    ats = _ATS_HOSTS.get(parts.netloc.lower())
    if ats is None:
        return None
    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        return None
    slug = unquote(segments[0])
    if not _SLUG_RE.match(slug):
        return None  # e.g. an encoded "Civic%20Roundtable" is not a real first-party board slug
    return AtsRef(ats=ats, slug=slug, url=url)


def _sg_job(href: str, text: str, ref: AtsRef) -> SgJob:
    """Build one :class:`SgJob` from an apply URL and its middot-delimited card text.

    The title flattens in front of the meta line, so ``heading`` keeps the role+company blob;
    ``location`` is the last non-posted field and ``posted_at`` the posted one.
    """
    parts = [p.strip() for p in text.split(_BULLET) if p.strip()]
    posted = next((p for p in parts if p.lower().startswith("posted")), "")
    meta = [p for p in parts if not p.lower().startswith("posted")]
    return SgJob(
        apply_url=href,
        ats_ref=ref,
        heading=meta[0] if meta else "",
        location=meta[-1] if len(meta) >= 2 else "",
        posted_at=posted,
    )


def parse_jobs(html: str) -> list[SgJob]:
    """Parse rendered startups.gallery anchor cards into :class:`SgJob` rows.

    Keeps only anchors whose href resolves to a known ATS (the discovery target); a card whose text
    does not split into the expected shape still yields the apply URL + ATS ref, so a layout tweak
    degrades rather than drops the row.
    """
    out: list[SgJob] = []
    for m in _ANCHOR.finditer(html):
        ref = derive_ats_ref(m.group("href"))
        if ref is None:
            continue
        out.append(_sg_job(m.group("href"), html_to_text(m.group("inner")), ref))
    return out


def discover_ats_refs(jobs: Iterable[SgJob]) -> list[AtsRef]:
    """Collect the distinct ATS refs from parsed jobs, first-seen order (dedup by ats + slug)."""
    seen: set[tuple[str, str]] = set()
    out: list[AtsRef] = []
    for j in jobs:
        if j.ats_ref is None:
            continue
        key = (j.ats_ref.ats, j.ats_ref.slug)
        if key in seen:
            continue
        seen.add(key)
        out.append(j.ats_ref)
    return out


def fetch_jobs(filters: SgFilters) -> list[SgJob]:
    """Render a filtered startups.gallery jobs page and parse it (network, lazy import).

    Read-only public GET, patchright-rendered (the cards need JS). Unit tests cover the pure parse;
    this orchestrator is exercised by a live smoke test.
    """
    from polyfetch_scrape import RenderOptions, fetch  # pyright: ignore[reportMissingImports]

    r = fetch(
        build_jobs_url(filters),
        max_tier="patchright",
        render=RenderOptions(wait_until="networkidle"),
    )
    return parse_jobs(r.body.decode("utf-8", "replace"))


def main(filters: SgFilters | None = None) -> None:
    """Render a filtered startups.gallery page -> new ATS slugs in ``results/emerging-slugs.json``.

    The parsed cards + the distinct ATS refs (new first-party ingest targets) are written under
    ``results/`` (git-ignored business data), for human review before any seed change. Network path.
    """
    import json

    from ajoa_kit.settings import AppSettings

    settings = AppSettings()
    jobs = fetch_jobs(filters or SgFilters())
    refs = discover_ats_refs(jobs)
    out_path = settings.results_dir / "emerging-slugs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"slugs": [r.model_dump() for r in refs], "jobs": [j.model_dump() for j in jobs]}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"startups_gallery: {len(jobs)} cards -> {len(refs)} distinct ATS slugs -> {out_path}")
