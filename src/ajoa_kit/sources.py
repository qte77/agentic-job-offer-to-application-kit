"""Source adapters: fetch + parse each feed/ATS/aggregator into normalized records (#249 slice C).

One ``from_*`` generator per public, no-auth endpoint (Greenhouse / Ashby / Recruitee / Lever /
Workable / Personio / RSS / arbeitnow / The Muse), each yielding the
:func:`ajoa_kit.normalize.record` shape; ``ATS`` / ``AGGREGATORS`` map a seed entry to its adapter,
and :func:`load_sources` reads the seed. Adapters stay explicit per-API functions — long but simple;
a table-driven abstraction would obscure each API's quirks (AHA). ``polyfetch_scrape`` is imported
lazily inside the fetch helpers so the module stays importable offline. Sources are ToS-tiered per
ADR-0002.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from defusedxml.ElementTree import fromstring as xml_fromstring

from ajoa_kit.normalize import canonical_url, html_to_text, record

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Any


def get_json(url: str) -> tuple[Any, str]:
    """Fetch ``url`` as JSON; return (parsed_json, polyfetch_backend)."""
    # lazy: keep pure logic importable w/o polyfetch
    from polyfetch_scrape import FetchError, fetch  # pyright: ignore[reportMissingImports]

    r = fetch(url, headers={"Accept": "application/json"})
    if r.status != 200:
        raise FetchError(f"HTTP {r.status} ({r.backend})")
    return json.loads(r.body), r.backend


def get_bytes(url: str) -> tuple[bytes, str]:
    """Fetch ``url`` as raw bytes; return (body, polyfetch_backend)."""
    # lazy: keep pure logic importable w/o polyfetch
    from polyfetch_scrape import FetchError, fetch  # pyright: ignore[reportMissingImports]

    r = fetch(url)
    if r.status != 200:
        raise FetchError(f"HTTP {r.status} ({r.backend})")
    return r.body, r.backend


# --- adapters (each yields normalized records) ----------------------------------------
def from_greenhouse(c: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from a Greenhouse board."""
    slug = c["slug"]
    data, backend = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    for j in data.get("jobs", []):
        dept = ", ".join(d.get("name", "") for d in j.get("departments", []))
        yield record(
            id=f"greenhouse:{slug}:{j.get('id')}",
            source="greenhouse",
            ats="greenhouse",
            company=c["company"],
            company_slug=slug,
            lane_hint=c["lane"],
            department=dept,
            fetched_backend=backend,
            title=j.get("title", ""),
            location=(j.get("location") or {}).get("name", ""),
            url=j.get("absolute_url", ""),
            posted_at=j.get("first_published") or j.get("updated_at", "") or "",
            last_modified=j.get("updated_at", "") or "",
            description=html_to_text(j.get("content", "")),
        )


def from_ashby(c: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from an Ashby board."""
    slug = c["slug"]
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    data, backend = get_json(url)
    for j in data.get("jobs", []):
        dept = " / ".join(x for x in [j.get("department"), j.get("team")] if x)
        yield record(
            id=f"ashby:{slug}:{j.get('id')}",
            source="ashby",
            ats="ashby",
            company=c["company"],
            company_slug=slug,
            lane_hint=c["lane"],
            department=dept,
            fetched_backend=backend,
            title=j.get("title", ""),
            location=j.get("location", "") or "",
            remote=j.get("isRemote"),
            url=j.get("jobUrl", "") or j.get("applyUrl", ""),
            posted_at=j.get("publishedAt", "") or "",
            description=html_to_text(j.get("descriptionPlain") or j.get("descriptionHtml", "")),
        )


def from_recruitee(c: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from a Recruitee board."""
    slug = c["slug"]
    data, backend = get_json(f"https://{slug}.recruitee.com/api/offers/")
    for j in data.get("offers", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country_code")] if x)
        dept = ", ".join(x for x in [j.get("department"), j.get("category")] if x)
        yield record(
            id=f"recruitee:{slug}:{j.get('id')}",
            source="recruitee",
            ats="recruitee",
            company=c["company"],
            company_slug=slug,
            lane_hint=c["lane"],
            department=dept,
            fetched_backend=backend,
            title=j.get("title", ""),
            location=loc or j.get("location", ""),
            url=j.get("careers_url", "") or j.get("careers_apply_url", ""),
            posted_at=j.get("created_at", "") or "",
            description=html_to_text(j.get("description", "")),
        )


def from_lever(c: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from a Lever board."""
    slug = c["slug"]
    data, backend = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    for j in data if isinstance(data, list) else []:
        cat = j.get("categories") or {}
        wt = j.get("workplaceType")
        yield record(
            id=f"lever:{slug}:{j.get('id')}",
            source="lever",
            ats="lever",
            company=c["company"],
            company_slug=slug,
            lane_hint=c["lane"],
            department=cat.get("department") or cat.get("team") or "",
            fetched_backend=backend,
            title=j.get("text", ""),
            location=cat.get("location", "") or "",
            remote=(wt == "remote") if wt else None,
            url=j.get("hostedUrl", "") or j.get("applyUrl", ""),
            posted_at=str(j.get("createdAt", "") or ""),
            description=html_to_text(j.get("descriptionPlain") or j.get("description", "")),
        )


def from_workable(c: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from a Workable board."""
    slug = c["slug"]
    data, backend = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    for j in data.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        yield record(
            id=f"workable:{slug}:{j.get('shortcode') or j.get('id')}",
            source="workable",
            ats="workable",
            company=c["company"],
            company_slug=slug,
            lane_hint=c["lane"],
            department=j.get("department", "") or "",
            fetched_backend=backend,
            title=j.get("title", ""),
            location=loc,
            remote=j.get("telecommuting"),
            url=j.get("url", "") or j.get("application_url", ""),
            posted_at=j.get("published_on", "") or "",
            description=html_to_text(j.get("description", "")),
        )


def from_personio(c: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from a Personio XML board."""
    slug = c["slug"]
    raw, backend = get_bytes(f"https://{slug}.jobs.personio.de/xml?language=en")
    root = xml_fromstring(raw)
    for pos in root.iter("position"):
        pid = pos.findtext("id", "") or ""
        descs = [jd.findtext("value") or "" for jd in pos.iter("jobDescription")]
        yield record(
            id=f"personio:{slug}:{pid}",
            source="personio",
            ats="personio",
            company=c["company"],
            company_slug=slug,
            lane_hint=c["lane"],
            department=pos.findtext("department", "") or "",
            fetched_backend=backend,
            title=pos.findtext("name", "") or "",
            location=pos.findtext("office", "") or "",
            url=f"https://{slug}.jobs.personio.de/job/{pid}",
            posted_at=pos.findtext("createdAt", "") or "",
            description=html_to_text(" ".join(descs)),
        )


def from_rss(f: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from an RSS 2.0 feed."""
    raw, backend = get_bytes(f["url"])
    root = xml_fromstring(raw)
    for item in root.iter("item"):
        link = canonical_url((item.findtext("link") or "").strip())
        yield record(
            id=f"{f['source']}:{link}",
            source=f["source"],
            ats="rss",
            company="",
            lane_hint="",
            fetched_backend=backend,
            title=(item.findtext("title") or "").strip(),
            url=link,
            posted_at=(item.findtext("pubDate") or "").strip(),
            description=html_to_text(item.findtext("description")),
        )


def from_arbeitnow(a: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from the arbeitnow public job-board API (a broad aggregator).

    Aggregators span many employers from one endpoint and expose no department taxonomy, so the
    job ``tags`` populate ``department`` — that lets the existing pre-filter keep on tags OR title
    with no ``keep()`` change. ``a`` is the config entry (only the dispatch name); the endpoint is
    fixed. Attribution (a backlink to arbeitnow.com, ToS §11) is rendered in the dashboard footer.

    Page 1 only (~100 jobs): a deliberate v1 cut honoring the source's courtesy rate limit;
    bounded pagination is a follow-up if recall proves thin.
    """
    data, backend = get_json("https://www.arbeitnow.com/api/job-board-api")
    for j in data.get("data", []):
        yield record(
            id=f"arbeitnow:{j.get('slug', '')}",
            source="arbeitnow",
            ats="arbeitnow",
            company=j.get("company_name", ""),
            department=", ".join(j.get("tags") or []),
            fetched_backend=backend,
            title=j.get("title", ""),
            location=j.get("location", "") or "",
            remote=j.get("remote"),
            url=j.get("url", ""),
            posted_at=str(j.get("created_at", "") or ""),
            description=html_to_text(j.get("description", "")),
        )


def from_themuse(a: dict[str, str]) -> Iterable[dict[str, Any]]:
    """Yield normalized records from The Muse public job-board API (a broad aggregator).

    Like arbeitnow, a no-auth aggregator spanning many employers; nested fields (``company.name``,
    ``locations[]``, ``refs.landing_page``) are flattened into the record shape, and the job
    ``categories`` populate ``department`` so the existing pre-filter applies. ``a`` is the dispatch
    entry; the endpoint is fixed — page 1 + an eng-relevant ``category`` filter (a v1 cut). The API
    ToS requests attribution (a themuse.com link); the aggregate-only output reproduces no Muse
    content (Feist), so it is recorded in config/ADR, not rendered on the page.
    """
    params = [
        ("category", "Software Engineering"),
        ("category", "Data Science"),
        ("category", "Computer and IT"),
        ("category", "Engineering"),
        ("page", "1"),
    ]
    data, backend = get_json(f"https://www.themuse.com/api/public/jobs?{urlencode(params)}")
    for j in data.get("results", []):
        company = j.get("company") or {}
        locs = [loc.get("name", "") for loc in j.get("locations") or []]
        yield record(
            id=f"themuse:{j.get('id')}",
            source="themuse",
            ats="themuse",
            company=company.get("name", ""),
            company_slug=company.get("short_name", ""),
            department=", ".join(c.get("name", "") for c in j.get("categories") or []),
            fetched_backend=backend,
            title=(j.get("name") or "").strip(),
            location=", ".join(x for x in locs if x),
            remote=True if any("remote" in (x or "").lower() for x in locs) else None,
            url=(j.get("refs") or {}).get("landing_page", ""),
            posted_at=j.get("publication_date", "") or "",
            description=html_to_text(j.get("contents", "")),
        )


ATS: dict[str, Callable[[dict[str, str]], Iterable[dict[str, Any]]]] = {
    "greenhouse": from_greenhouse,
    "ashby": from_ashby,
    "recruitee": from_recruitee,
    "lever": from_lever,
    "workable": from_workable,
    "personio": from_personio,
}

# Aggregators are a third source type (one endpoint -> many employers); see ADR-0001/ADR-0002.
AGGREGATORS: dict[str, Callable[[dict[str, str]], Iterable[dict[str, Any]]]] = {
    "arbeitnow": from_arbeitnow,
    "themuse": from_themuse,
}


def load_sources(
    config_dir: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Load (feeds, ats, aggregators) from ``config/seed.json``, else ``default-seed.json``.

    The git-ignored ``config/seed.json`` holds your run's sources and wins when present; absent
    it, the tracked ``config/default-seed.json`` (a ToS-vetted default) is used. Fail loud only
    when neither exists. Keys beyond ``feeds`` / ``ats`` / ``aggregators`` (e.g. ``_blocked``,
    ``_deferred``) are ignored.
    """
    path = config_dir / "seed.json"
    if not path.is_file():
        path = config_dir / "default-seed.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing {config_dir}/seed.json (no default-seed.json either) — "
            "create it (keys: feeds, ats, aggregators; see README)",
        )
    cfg = json.loads(path.read_text())
    return cfg.get("feeds", []), cfg.get("ats", []), cfg.get("aggregators", [])
