"""Value-add tests for the trickiest adapter normalizations (Personio XML, RSS).

These exercise real parsing risk: XML/RSS structure, entity decoding + tag stripping,
URL canonicalization, and tolerance of missing fields. Synthetic fixtures only — no real
scraped JD data, so no personally identifiable information (PII) is committed. The network
boundary (`get_bytes`) is monkeypatched, so these run offline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ajoa_kit import ingest

if TYPE_CHECKING:
    import pytest

PERSONIO_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
  <position>
    <id>123</id>
    <name>Senior Backend Engineer</name>
    <department>Engineering</department>
    <office>Munich</office>
    <createdAt>2026-01-01</createdAt>
    <jobDescriptions>
      <jobDescription>
        <name>Role</name>
        <value>Build &lt;b&gt;backend&lt;/b&gt; systems.</value>
      </jobDescription>
    </jobDescriptions>
  </position>
  <position>
    <id>124</id>
    <name>Platform Engineer</name>
    <department>Engineering</department>
    <jobDescriptions/>
  </position>
</workzag-jobs>
"""

RSS_XML = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Software Engineer</title>
    <link>https://ex.co/jobs/1?utm_source=feed</link>
    <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
    <description>Do &lt;i&gt;stuff&lt;/i&gt; here.</description>
  </item>
</channel></rss>
"""

# arbeitnow returns parsed JSON (get_json), not bytes. Second job omits tags/location.
ARBEITNOW_JSON = {
    "data": [
        {
            "slug": "senior-backend-engineer-acme-123",
            "company_name": "Acme AI",
            "title": "Senior Backend Engineer",
            "description": "Build <b>backend</b> systems &amp; APIs.",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/acme-123?utm_source=feed",
            "tags": ["engineering", "python"],
            "location": "Berlin",
            "created_at": 1767225600,
        },
        {
            "slug": "product-designer-acme-124",
            "company_name": "Acme AI",
            "title": "Product Designer",
            "description": "Design things.",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/acme-124",
        },
    ]
}


def test_personio_normalizes_and_tolerates_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest, "get_bytes", lambda _url: (PERSONIO_XML, "httpx"))
    recs = list(ingest.from_personio({"slug": "acme", "company": "Acme", "lane": "engineering"}))

    assert len(recs) == 2
    first = recs[0]
    assert first["id"] == "personio:acme:123"
    assert first["title"] == "Senior Backend Engineer"
    assert first["department"] == "Engineering"
    assert first["location"] == "Munich"
    assert first["url"] == "https://acme.jobs.personio.de/job/123"
    assert "backend" in first["description"].lower()
    assert "<b>" not in first["description"]  # tags stripped

    # second position: no <office>, empty descriptions -> tolerated, not skipped
    assert recs[1]["location"] == ""
    assert recs[1]["description"] == ""


def test_rss_normalizes_and_canonicalizes_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest, "get_bytes", lambda _url: (RSS_XML, "httpx"))
    recs = list(ingest.from_rss({"source": "demo", "url": "https://ex.co/rss"}))

    assert len(recs) == 1
    r = recs[0]
    assert r["ats"] == "rss"
    assert r["title"] == "Software Engineer"
    assert r["url"] == "https://ex.co/jobs/1"  # utm_source dropped
    assert r["id"] == "demo:https://ex.co/jobs/1"
    assert "stuff" in r["description"]


def test_arbeitnow_normalizes_and_tolerates_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest, "get_json", lambda _url: (ARBEITNOW_JSON, "httpx"))
    recs = list(ingest.from_arbeitnow({"name": "arbeitnow"}))

    assert len(recs) == 2
    first = recs[0]
    assert first["id"] == "arbeitnow:senior-backend-engineer-acme-123"
    assert first["source"] == "arbeitnow"
    assert first["ats"] == "arbeitnow"
    assert first["company"] == "Acme AI"
    assert first["title"] == "Senior Backend Engineer"
    assert first["remote"] is True
    assert first["department"] == "engineering, python"  # tags -> department for the pre-filter
    assert first["url"] == "https://www.arbeitnow.com/jobs/acme-123"  # utm_source dropped
    assert "backend" in first["description"].lower()
    assert "<b>" not in first["description"]  # tags stripped
    assert "&amp;" not in first["description"]  # entity decoded

    # second job: no tags / no location -> tolerated (empty), not skipped
    assert recs[1]["department"] == ""
    assert recs[1]["location"] == ""


def test_greenhouse_joins_departments_and_tolerates_null_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "Staff Engineer",
                "departments": [{"name": "Engineering"}, {"name": "Platform"}],
                "location": {"name": "Remote"},
                "absolute_url": "https://gh/jobs/1?utm_source=x",
                "first_published": "2025-12-20T10:00:00-05:00",
                "updated_at": "2026-01-01",
                "content": "Build &lt;b&gt;systems&lt;/b&gt;.",
            },
            {
                "id": 2,
                "title": "Designer",
                "departments": [],
                "location": None,
                "absolute_url": "https://gh/jobs/2",
                "updated_at": "2026-02-02",  # no first_published -> posted_at falls back to this
                "content": "",
            },
        ]
    }
    monkeypatch.setattr(ingest, "get_json", lambda _u: (payload, "httpx"))
    recs = list(ingest.from_greenhouse({"slug": "acme", "company": "Acme", "lane": "engineering"}))
    assert recs[0]["id"] == "greenhouse:acme:1"
    assert recs[0]["department"] == "Engineering, Platform"  # multi-dept join
    assert recs[0]["location"] == "Remote"
    assert recs[0]["url"] == "https://gh/jobs/1"  # utm dropped
    assert "<b>" not in recs[0]["description"]
    assert "systems" in recs[0]["description"]
    # posted_at = true publish date (first_published); last_modified = updated_at (greenhouse-only)
    assert recs[0]["posted_at"] == "2025-12-20T10:00:00-05:00"
    assert recs[0]["last_modified"] == "2026-01-01"
    # null location + empty departments tolerated (the `or {}` guard), not skipped
    assert recs[1]["location"] == ""
    assert recs[1]["department"] == ""
    # no first_published -> posted_at falls back to updated_at; last_modified still updated_at
    assert recs[1]["posted_at"] == "2026-02-02"
    assert recs[1]["last_modified"] == "2026-02-02"


def test_ashby_joins_dept_team_and_url_description_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "jobs": [
            {
                "id": "a1",
                "title": "Backend Eng",
                "department": "Engineering",
                "team": "Core",
                "location": "Berlin",
                "isRemote": True,
                "applyUrl": "https://ashby/apply/a1",
                "descriptionHtml": "<p>Hello</p>",
                "publishedAt": "2026-01-02",
            },
            {
                "id": "a2",
                "title": "SRE",
                "team": "Infra",
                "isRemote": False,
                "jobUrl": "https://ashby/a2",
                "descriptionPlain": "Plain text",
            },
        ]
    }
    monkeypatch.setattr(ingest, "get_json", lambda _u: (payload, "httpx"))
    recs = list(ingest.from_ashby({"slug": "acme", "company": "Acme", "lane": "engineering"}))
    assert recs[0]["department"] == "Engineering / Core"
    assert recs[0]["remote"] is True
    assert recs[0]["url"] == "https://ashby/apply/a1"  # no jobUrl -> applyUrl fallback
    assert "Hello" in recs[0]["description"]
    assert "<p>" not in recs[0]["description"]
    # only `team` present -> dept is team; descriptionPlain preferred; jobUrl used
    assert recs[1]["department"] == "Infra"
    assert recs[1]["remote"] is False
    assert recs[1]["url"] == "https://ashby/a2"
    assert recs[1]["description"] == "Plain text"


def test_lever_list_guard_and_workplace_remote_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "id": "l1",
            "text": "Platform Eng",
            "categories": {"department": "Eng", "location": "NYC"},
            "workplaceType": "remote",
            "hostedUrl": "https://lever/l1",
            "createdAt": 1700000000000,
            "descriptionPlain": "Do x.",
        },
        {
            "id": "l2",
            "text": "Onsite Eng",
            "categories": None,
            "workplaceType": "onsite",
            "applyUrl": "https://lever/apply/l2",
            "description": "<p>x</p>",
        },
        {"id": "l3", "text": "No WT", "categories": {"team": "Data"}},
    ]
    monkeypatch.setattr(ingest, "get_json", lambda _u: (payload, "httpx"))
    recs = list(ingest.from_lever({"slug": "acme", "company": "Acme", "lane": "engineering"}))
    assert recs[0]["department"] == "Eng"
    assert recs[0]["location"] == "NYC"
    assert recs[0]["remote"] is True
    assert recs[0]["posted_at"] == "1700000000000"
    assert recs[1]["remote"] is False
    assert recs[1]["department"] == ""  # categories null -> {}
    assert recs[1]["url"] == "https://lever/apply/l2"
    assert recs[2]["remote"] is None  # no workplaceType
    assert recs[2]["department"] == "Data"  # team fallback when no department


def test_lever_non_list_payload_yields_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    # The Lever endpoint returns a bare array; a dict (error/edge shape) must yield nothing,
    # not crash — the `isinstance(data, list)` guard.
    monkeypatch.setattr(ingest, "get_json", lambda _u: ({"unexpected": "dict"}, "httpx"))
    assert list(ingest.from_lever({"slug": "acme", "company": "Acme", "lane": "engineering"})) == []


def test_recruitee_joins_and_location_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "offers": [
            {
                "id": 1,
                "title": "Eng",
                "city": "Munich",
                "country_code": "DE",
                "department": "Engineering",
                "category": "Backend",
                "careers_url": "https://r/1",
                "description": "<p>Hi</p>",
                "created_at": "2026-01-03",
            },
            {
                "id": 2,
                "title": "Eng2",
                "location": "Remote EU",
                "careers_apply_url": "https://r/apply/2",
                "description": "",
            },
        ]
    }
    monkeypatch.setattr(ingest, "get_json", lambda _u: (payload, "httpx"))
    recs = list(ingest.from_recruitee({"slug": "acme", "company": "Acme", "lane": "engineering"}))
    assert recs[0]["location"] == "Munich, DE"  # city + country_code join
    assert recs[0]["department"] == "Engineering, Backend"  # department + category join
    assert recs[0]["url"] == "https://r/1"
    # no city/country -> the `location` field is the fallback; careers_apply_url is the url fallback
    assert recs[1]["location"] == "Remote EU"
    assert recs[1]["url"] == "https://r/apply/2"


def test_workable_shortcode_id_and_telecommuting(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "jobs": [
            {
                "shortcode": "ABC123",
                "id": 99,
                "title": "Eng",
                "city": "Lisbon",
                "country": "PT",
                "telecommuting": True,
                "url": "https://w/ABC123",
                "description": "<p>Hi</p>",
            },
            {
                "id": 100,
                "title": "Eng2",
                "telecommuting": False,
                "application_url": "https://w/apply/100",
                "description": "",
            },
        ]
    }
    monkeypatch.setattr(ingest, "get_json", lambda _u: (payload, "httpx"))
    recs = list(ingest.from_workable({"slug": "acme", "company": "Acme", "lane": "engineering"}))
    assert recs[0]["id"] == "workable:acme:ABC123"  # shortcode preferred over numeric id
    assert recs[0]["location"] == "Lisbon, PT"
    assert recs[0]["remote"] is True
    assert recs[0]["url"] == "https://w/ABC123"
    # no shortcode -> numeric id; url falls back to application_url
    assert recs[1]["id"] == "workable:acme:100"
    assert recs[1]["url"] == "https://w/apply/100"


THEMUSE_JSON = {
    "results": [
        {
            "id": 123,
            "name": " Senior Backend Engineer ",
            "company": {"id": 1, "short_name": "acme", "name": "Acme AI"},
            "locations": [{"name": "Flexible / Remote"}, {"name": "New York, NY"}],
            "categories": [{"name": "Software Engineering"}],
            "refs": {"landing_page": "https://www.themuse.com/jobs/acme/be?utm_source=x"},
            "publication_date": "2026-01-05T00:00:00Z",
            "contents": "Build <b>systems</b>.",
        },
        {
            "id": 124,
            "name": "Designer",
            "company": {"name": "Acme AI"},
            "locations": [],
            "categories": [],
            "refs": {},
            "contents": "",
        },
    ]
}


def test_themuse_normalizes_nested_fields_and_tolerates_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ingest, "get_json", lambda _u: (THEMUSE_JSON, "httpx"))
    recs = list(ingest.from_themuse({"name": "themuse"}))

    assert len(recs) == 2
    first = recs[0]
    assert first["id"] == "themuse:123"
    assert first["ats"] == "themuse"
    assert first["company"] == "Acme AI"  # nested company.name
    assert first["company_slug"] == "acme"  # nested company.short_name
    assert first["title"] == "Senior Backend Engineer"  # leading space stripped
    assert first["location"] == "Flexible / Remote, New York, NY"  # locations joined
    assert first["remote"] is True  # a "Remote" location is detected
    assert first["department"] == "Software Engineering"  # categories joined
    assert first["url"] == "https://www.themuse.com/jobs/acme/be"  # refs.landing_page, utm dropped
    assert "systems" in first["description"]
    assert "<b>" not in first["description"]
    # second job: missing company fields + empty locations/categories/refs -> tolerated
    assert recs[1]["company_slug"] == ""
    assert recs[1]["location"] == ""
    assert recs[1]["department"] == ""
    assert recs[1]["remote"] is None
    assert recs[1]["url"] == ""
