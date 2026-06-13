"""Stage-2 ingestion: pull job descriptions (JDs) from feed/API-first sources.

Deterministic only — fetch + parse + normalize + pre-filter + dedupe. No relevance
judgment here (that is the LLM pass in ``cc-workflow-relevance.js``).

Sources are feed/API-first and no-auth, loaded from ``config/seed.json``:
  - RSS/Atom feeds (broad, no slug)
  - Greenhouse / Ashby / Recruitee / Lever / Workable / Personio (per-company, slug-keyed)

Run via the wrapper (borrows polyfetch's uv env so ``polyfetch_scrape`` imports)::

    scripts/ingest.sh

Writes ``results/jobs-raw.json`` (the relevance pass's input) and
``results/jobs-raw.summary.md`` (per-source counts + any failures).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from defusedxml.ElementTree import fromstring as xml_fromstring

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import Any

ROOT = Path(__file__).resolve().parents[2]  # repo root (src/ajoa_kit/ -> src -> root)
RESULTS = ROOT / "results"  # generated ingest data lives here (git-ignored)
CONFIG_DIR = ROOT / "config"  # user inputs (seed.json)
DESC_CAP = 4000  # chars of description kept per JD (bounds the later relevance-pass tokens)

# --- Structured pre-filter ------------------------------------------------------------
# Coarse, cheap cut BEFORE the LLM relevance pass: keep only JDs whose ATS department
# (or, for RSS, title) matches an interest term. Matched on WORD BOUNDARIES so "ai" does
# not match "maintenance". A deliberately generous cut on a clean taxonomy field — the
# LLM gate does the lane-level nuance.
FILTER_ATS_BY_DEPARTMENT = True  # Greenhouse/Ashby/Recruitee expose a clean `department`
FILTER_RSS_BY_TITLE = True  # RSS has no department; match the role title instead
INTEREST = [
    "engineer",
    "engineering",
    "software",
    "developer",
    "development",
    "entwickler",
    "entwicklung",
    "informatik",
    "ingenieur",  # DE
    "infrastructure",
    "platform",
    "devops",
    "sre",
    "site reliability",
    "architect",
    "architecture",
    "system",
    "systems",
    "backend",
    "fullstack",
    "full stack",
    "full-stack",
    "ai",
    "ml",
    "machine learning",
    "mlops",
    "data",
    "security",
    "cloud",
    "technical",
    "founding",
    "applied",
]
# Stricter set for the ATS *title* fallback (when department is empty/non-matching):
# core eng role nouns, so broad dept words do not pull in non-eng titles via the title.
TITLE_ROLES = [
    "engineer",
    "engineering",
    "developer",
    "entwickler",
    "software",
    "architect",
    "architecture",
    "devops",
    "sre",
    "site reliability",
    "platform",
    "infrastructure",
    "backend",
    "fullstack",
    "full stack",
    "full-stack",
    "mlops",
    "founding",
]

# --- helpers --------------------------------------------------------------------------
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_INTEREST = re.compile(r"\b(" + "|".join(re.escape(t) for t in INTEREST) + r")\b", re.I)
_TITLE_ROLES = re.compile(r"\b(" + "|".join(re.escape(t) for t in TITLE_ROLES) + r")\b", re.I)
_TRACKING = {"gclid", "fbclid", "mc_cid", "mc_eid", "igshid", "ref_src"}


def is_interesting(text: str | None) -> bool:
    """Return True if ``text`` contains an INTEREST term on a word boundary."""
    return bool(text and _INTEREST.search(text))


def is_role_title(text: str | None) -> bool:
    """Return True if ``text`` contains a core engineering role noun on a word boundary."""
    return bool(text and _TITLE_ROLES.search(text))


def keep(rec: dict[str, Any]) -> bool:
    """Coarse pre-filter. RSS keeps on title; ATS keeps on department OR title.

    The title fallback stops a whole board being dropped when its ``department`` field is
    empty or coarse, while still cutting non-eng roles (a "Sales" dept + "Account
    Executive" title miss both).
    """
    if rec["ats"] == "rss":
        return not FILTER_RSS_BY_TITLE or is_interesting(rec["title"])
    if not FILTER_ATS_BY_DEPARTMENT:
        return True
    return is_interesting(rec["department"]) or is_role_title(rec["title"])


def html_to_text(s: str | None) -> str:
    """Unescape entities, strip tags, collapse whitespace, and cap length."""
    if not s:
        return ""
    s = html.unescape(s)
    s = _TAG.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s[:DESC_CAP]


def canonical_url(url: str) -> str:
    """Drop tracking query params (utm_*, gclid, ...) for clean, stable URLs/ids."""
    if not url:
        return url
    s = urlsplit(url)
    if not s.query:
        return url
    kept = [
        (k, v)
        for k, v in parse_qsl(s.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING
    ]
    return urlunsplit((s.scheme, s.netloc, s.path, urlencode(kept), s.fragment))


def record(**kw: object) -> dict[str, Any]:
    """Build a normalized JD record; every adapter emits exactly this shape."""
    base = {
        "id": "",
        "source": "",
        "ats": "",
        "company": "",
        "company_slug": "",
        "lane_hint": "",
        "department": "",
        "fetched_backend": "",
        "title": "",
        "location": "",
        "remote": None,
        "url": "",
        "posted_at": "",
        "description": "",
    }
    base.update(kw)
    base["url"] = canonical_url(base["url"])
    return base


def get_json(url: str) -> tuple[Any, str]:
    """Fetch ``url`` as JSON; return (parsed_json, polyfetch_backend)."""
    from polyfetch_scrape import FetchError, fetch  # lazy: keep pure logic importable w/o polyfetch

    r = fetch(url, headers={"Accept": "application/json"})
    if r.status != 200:
        raise FetchError(f"HTTP {r.status} ({r.backend})")
    return json.loads(r.body), r.backend


def get_bytes(url: str) -> tuple[bytes, str]:
    """Fetch ``url`` as raw bytes; return (body, polyfetch_backend)."""
    from polyfetch_scrape import FetchError, fetch  # lazy: keep pure logic importable w/o polyfetch

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
            posted_at=j.get("updated_at", "") or "",
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


ATS: dict[str, Callable[[dict[str, str]], Iterable[dict[str, Any]]]] = {
    "greenhouse": from_greenhouse,
    "ashby": from_ashby,
    "recruitee": from_recruitee,
    "lever": from_lever,
    "workable": from_workable,
    "personio": from_personio,
}


# --- run ------------------------------------------------------------------------------
def load_sources() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Load (feeds, ats) from ``config/seed.json``; fail loud if it is missing."""
    path = CONFIG_DIR / "seed.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing {path} — create it (keys: feeds, ats; see README)",
        )
    cfg = json.loads(path.read_text())
    return cfg.get("feeds", []), cfg.get("ats", [])


def collect(sources: list[tuple[str, Callable[[], Iterable[dict[str, Any]]]]]) -> dict[str, Any]:
    """Pull every source (warn-and-continue), applying the pre-filter; return run state."""
    jobs: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    filtered: dict[str, int] = {}
    tiers: dict[str, str] = {}
    failures: list[str] = []
    for label, pull in sources:
        try:
            rows = list(pull())
        except Exception as e:  # warn-and-continue: one bad source must not abort the whole run
            failures.append(f"{label}: {type(e).__name__}: {e}")
            continue
        kept = [r for r in rows if keep(r)]
        jobs += kept
        counts[label] = len(kept)
        filtered[label] = len(rows) - len(kept)
        tiers[label] = rows[0]["fetched_backend"] if rows else "-"
    return {
        "jobs": jobs,
        "counts": counts,
        "filtered": filtered,
        "tiers": tiers,
        "failures": failures,
    }


def dedupe(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate JDs by id (earlier sources win on collision)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for j in jobs:
        if j["id"] in seen:
            continue
        seen.add(j["id"])
        out.append(j)
    return out


def build_summary(deduped: list[dict[str, Any]], state: dict[str, Any]) -> str:
    """Render the per-source ingestion summary markdown."""
    counts, filtered, tiers, failures = (
        state["counts"],
        state["filtered"],
        state["tiers"],
        state["failures"],
    )
    total_filtered = sum(filtered.values())
    tier_dist: dict[str, int] = {}
    for t in tiers.values():
        tier_dist[t] = tier_dist.get(t, 0) + 1
    lines = [
        "# jobs-raw — ingestion summary",
        "",
        f"Total JDs kept: **{len(deduped)}** (deduped) — pre-filter dropped {total_filtered} "
        "(department/title not in INTEREST).",
        "",
        "## polyfetch tier per source (escalation = anti-bot fallback)",
        "",
        "httpx = tier-1 · curl_cffi = tier-2 TLS impersonation · playwright = tier-3 headless",
        "",
    ]
    lines += [f"- `{t}` — {tier_dist[t]} sources" for t in sorted(tier_dist)]
    lines += ["", "## Per-source counts (kept | filtered-out | tier)", ""]
    for k in sorted(counts):
        lines.append(f"- `{k}` — {counts[k]} | {filtered.get(k, 0)} | {tiers.get(k, '-')}")
    if failures:
        lines += ["", "## Failed (prune/fix the slug, then re-run)", ""]
        lines += [f"- `{x}`" for x in failures]
    return "\n".join(lines) + "\n"


def main() -> None:
    """Ingest all configured sources into results/jobs-raw.json (+ summary)."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    feeds, seed = load_sources()
    sources: list[tuple[str, Callable[[], Iterable[dict[str, Any]]]]] = [
        (f"feed/{f['source']}", (lambda f=f: from_rss(f))) for f in feeds
    ]
    sources += [(f"{c['ats']}/{c['slug']}", (lambda c=c: ATS[c["ats"]](c))) for c in seed]

    state = collect(sources)
    deduped = dedupe(state["jobs"])
    (RESULTS / "jobs-raw.json").write_text(json.dumps(deduped, indent=2, ensure_ascii=False))
    (RESULTS / "jobs-raw.summary.md").write_text(build_summary(deduped, state))

    total_filtered = sum(state["filtered"].values())
    print(f"wrote {len(deduped)} JDs -> results/jobs-raw.json (dropped {total_filtered})")
    print(f"sources ok: {len(state['counts'])}  failed: {len(state['failures'])}")
    for x in state["failures"]:
        print(f"  FAIL {x}")


if __name__ == "__main__":
    main()
