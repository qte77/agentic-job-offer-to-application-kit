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
