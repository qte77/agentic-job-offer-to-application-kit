"""Value-add tests for the YC discovery->JD adapter (:mod:`ajoa_kit.yc_jobs`).

Synthetic fixtures only -- no real scraped JD data. Network is not exercised here; only the pure
parse/select/link-extraction logic, which is where correctness lives.
"""

from __future__ import annotations

from ajoa_kit.models import YcCompany
from ajoa_kit.yc_jobs import parse_hiring, parse_job_links, select_relevant


def test_parse_hiring_keeps_named_slugged_rows_and_derives_slug_from_url() -> None:
    payload = [
        {
            "name": "Acme",
            "slug": "acme",
            "batch": "Winter 2024",
            "isHiring": True,
            "tags": ["AI", "DevTools", 7],
        },
        {"name": "Beta", "url": "https://www.ycombinator.com/companies/beta", "isHiring": False},
        {"name": "  ", "slug": "blank"},  # blank name -> skipped
        {"slug": "noname", "isHiring": True},  # no name -> skipped
        {"name": "NoSlug", "isHiring": True},  # no slug and no url -> skipped
        "not-a-dict",
    ]
    out = parse_hiring(payload)
    assert [c.slug for c in out] == ["acme", "beta"]
    assert out[0].hiring is True
    assert out[0].batch == "Winter 2024"
    assert out[0].tags == ["AI", "DevTools"]  # non-str tag dropped
    assert out[1].slug == "beta"  # derived from url
    assert out[1].hiring is False


def test_parse_hiring_tolerates_non_list() -> None:
    assert parse_hiring({"not": "a list"}) == []


def test_select_relevant_filters_hiring_by_name_or_tag_terms() -> None:
    companies = [
        YcCompany(name="Agent Co", slug="agent-co", hiring=True, tags=["ml"]),
        YcCompany(name="Fintech Inc", slug="fintech", hiring=True, tags=["payments"]),
        YcCompany(name="Agent Off", slug="agent-off", hiring=False, tags=["ml"]),
    ]
    got = select_relevant(companies, ["agent", "ml"])
    assert [c.slug for c in got] == ["agent-co"]  # matches name/tag AND hiring; non-hiring dropped


def test_select_relevant_empty_terms_keeps_all_hiring() -> None:
    companies = [
        YcCompany(name="A", slug="a", hiring=True),
        YcCompany(name="B", slug="b", hiring=False),
    ]
    assert [c.slug for c in select_relevant(companies, [])] == ["a"]


def test_parse_job_links_extracts_dedupes_and_stamps_ids() -> None:
    company = YcCompany(name="Acme", slug="acme", hiring=True)
    html = (
        '<a href="/companies/acme/jobs/oBCZ7-founding-product-engineer">Founding</a>'
        '<a href="/companies/acme/jobs/oBCZ7-founding-product-engineer">dup jobid</a>'
        '<a href="/companies/acme/jobs/x9Q-senior-ml-engineer">ML</a>'
        '<a href="/companies/other/jobs/zz1-designer">other company</a>'  # wrong slug -> skipped
    )
    out = parse_job_links(html, company)
    assert [r["id"] for r in out] == ["yc:acme:oBCZ7", "yc:acme:x9Q"]
    assert out[0]["title"] == "Founding Product Engineer"
    assert out[0]["url"] == (
        "https://www.ycombinator.com/companies/acme/jobs/oBCZ7-founding-product-engineer"
    )
    assert out[0]["source"] == "yc"
    assert out[1]["title"] == "Senior Ml Engineer"
