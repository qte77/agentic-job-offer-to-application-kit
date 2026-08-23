"""YC discovery->JD adapter: yc-oss hiring signal -> public YC job pages -> normalized records.

The yc-oss feed (a third-party daily mirror of YC's public Algolia directory) carries company
signal only -- name, slug, batch, hiring flag -- never a JD. This follows the ``hiring`` flag to
each company's PUBLIC ``ycombinator.com/companies/<slug>/jobs`` page, extracts the per-role links,
and fetches each detail page into the shared :func:`ajoa_kit.normalize.record` shape.

ToS (ADR-0002): CAUTION. YC ``robots.txt`` disallows ``/companies?*`` (query URLs) but not the
clean ``/companies/<slug>/jobs`` path; access is read-only public GET only. The pure parse/select
logic is offline-testable; the network fetch lazy-imports :mod:`polyfetch_scrape` so this module
imports without it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ajoa_kit.models import YcCompany
from ajoa_kit.normalize import html_to_text, record

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

YC_BASE = "https://www.ycombinator.com"

# Per-role hrefs on a company jobs page: /companies/<slug>/jobs/<jobid>-<role-slug> (confirmed live
# 2026-08-22). jobid is the leading alnum token; role-slug de-slugs into a display title.
_JOB_HREF = re.compile(
    r"/companies/(?P<slug>[a-z0-9][a-z0-9-]*)/jobs/(?P<jobid>[A-Za-z0-9]+)-(?P<role>[a-z0-9][a-z0-9-]*)"
)


def _text(value: object) -> str:
    """Trim ``value`` if it is a string, else ``""`` (defensive parse of untrusted JSON)."""
    return value.strip() if isinstance(value, str) else ""


def _str_list(value: object) -> list[str]:
    """Keep only string members of a JSON array, else ``[]``."""
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _yc_slug(row: dict[str, Any]) -> str:
    """Return the company slug from ``slug`` or the trailing segment of ``url``, else ``""``."""
    slug = _text(row.get("slug"))
    if slug:
        return slug
    m = re.search(r"/companies/([a-z0-9][a-z0-9-]*)", _text(row.get("url")))
    return m.group(1) if m else ""


def _yc_company(row: dict[str, Any]) -> YcCompany | None:
    """Build a :class:`YcCompany` from one yc-oss row, or ``None`` if name/slug are unusable."""
    name = _text(row.get("name"))
    slug = _yc_slug(row)
    if not name or not slug:
        return None
    return YcCompany(
        name=name,
        slug=slug,
        batch=_text(row.get("batch")),
        hiring=bool(row.get("isHiring")),
        tags=_str_list(row.get("tags")),
    )


def parse_hiring(payload: object) -> list[YcCompany]:
    """Parse a yc-oss ``companies/*.json`` array into typed :class:`YcCompany` rows.

    Skips any row missing a usable ``name`` or ``slug`` (the job-page URL needs the slug), so a
    malformed record never yields a broken fetch target.
    """
    rows = payload if isinstance(payload, list) else []
    return [c for row in rows if isinstance(row, dict) if (c := _yc_company(row)) is not None]


def _matches(company: YcCompany, wanted: list[str]) -> bool:
    """True if any lowercased term appears in the company's name or tags."""
    hay = " ".join([company.name, *company.tags]).lower()
    return any(t in hay for t in wanted)


def select_relevant(companies: Iterable[YcCompany], terms: Iterable[str]) -> list[YcCompany]:
    """Keep hiring companies whose name or tags contain any of ``terms`` (case-insensitive).

    Empty ``terms`` keeps every hiring company (no relevance narrowing); non-hiring rows are always
    dropped -- the feed's whole purpose is the hiring signal.
    """
    wanted = [t.lower() for t in terms if t.strip()]
    hiring = [c for c in companies if c.hiring]
    if not wanted:
        return hiring
    return [c for c in hiring if _matches(c, wanted)]


def company_jobs_url(slug: str) -> str:
    """Public jobs-listing URL for a company slug (the CAUTION-tier clean path, no query params)."""
    return f"{YC_BASE}/companies/{slug}/jobs"


def _deslug(role: str) -> str:
    """Turn a URL role-slug (``founding-product-engineer``) into a display title."""
    return " ".join(w.capitalize() for w in role.split("-") if w)


def parse_job_links(html: str, company: YcCompany) -> list[dict[str, Any]]:
    """Extract per-role job links from a company jobs page into normalized record stubs.

    Deduplicates by job id (a page repeats the same href in card + heading) and ignores links for
    any other company. Stamps id ``yc:<slug>:<jobid>``, a title de-slugged from the URL, and the
    canonical detail URL; the description is filled later by :func:`fetch_jds` from the detail page.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for m in _JOB_HREF.finditer(html):
        jobid = m.group("jobid")
        if m.group("slug") != company.slug or jobid in seen:
            continue
        seen.add(jobid)
        out.append(
            record(
                id=f"yc:{company.slug}:{jobid}",
                source="yc",
                ats="yc",
                company=company.name,
                company_slug=company.slug,
                title=_deslug(m.group("role")),
                url=f"{YC_BASE}{m.group(0)}",
            )
        )
    return out


def _fill_description(stub: dict[str, Any]) -> None:
    """Fetch the detail page and flatten it into ``description`` (best-effort)."""
    from ajoa_kit.sources import get_bytes  # lazy: keeps this module offline-importable

    try:
        body, _ = get_bytes(stub["url"])
    except Exception as e:  # warn-and-continue: a dead detail page must not abort the sweep
        print(f"yc_jobs: no detail for {stub['id']}: {type(e).__name__}: {e}")
        return
    stub["description"] = html_to_text(body.decode("utf-8", "replace"))


def fetch_jds(companies: list[YcCompany]) -> list[dict[str, Any]]:
    """Fetch each company's public job pages into filled JD records (network, lazy import).

    Read-only public GET only (CAUTION tier). Warn-and-continue per company so one dead board never
    aborts the sweep. The pure logic above is what unit tests cover; this orchestrator is exercised
    by a live smoke test.
    """
    from ajoa_kit.sources import get_bytes  # lazy: keeps this module offline-importable

    out: list[dict[str, Any]] = []
    for c in companies:
        try:
            body, backend = get_bytes(company_jobs_url(c.slug))
        except Exception as e:  # warn-and-continue on any fetch failure
            print(f"yc_jobs: skipping {c.slug}: {type(e).__name__}: {e}")
            continue
        for stub in parse_job_links(body.decode("utf-8", "replace"), c):
            stub["fetched_backend"] = backend
            _fill_description(stub)
            out.append(stub)
    return out


def _yc_oss_url(sources: list[dict[str, Any]]) -> str:
    """Return the yc-oss discovery source URL from the seed's ``discovery`` array, or ``""``."""
    for s in sources:
        if s.get("format") == "yc-oss" or s.get("name") == "yc-oss":
            return _text(s.get("url"))
    return ""


def main(terms: list[str] | None = None, limit: int = 0) -> None:
    """Fetch relevant hiring YC companies' public JDs into ``results/yc-jobs.json`` (local-only).

    Reads the yc-oss discovery URL from the seed, screens the hiring feed by ``terms`` (lane
    keywords), optionally caps to ``limit`` companies, and follows each to its public job pages.
    Business data -> written under ``results/`` (git-ignored), never published. Network path.
    """
    import json

    from ajoa_kit.discover import _load_discovery_sources
    from ajoa_kit.settings import AppSettings
    from ajoa_kit.sources import get_json

    settings = AppSettings()
    url = _yc_oss_url(_load_discovery_sources(settings.config_dir))
    if not url:
        print("yc_jobs: no yc-oss discovery source in the seed - nothing to do")
        return
    payload, _ = get_json(url)
    companies = select_relevant(parse_hiring(payload), terms or [])
    if limit > 0:
        companies = companies[:limit]
    jobs = fetch_jds(companies)
    out_path = settings.results_dir / "yc-jobs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"jobs": jobs}, indent=2, ensure_ascii=False))
    print(f"yc_jobs: {len(companies)} hiring companies -> {len(jobs)} JDs -> {out_path}")
