"""Value-add tests for the startups.gallery discovery adapter (:mod:`ajoa_kit.startups_gallery`).

Synthetic HTML fixtures modeling the confirmed card shape (anchor -> ATS url; middot text).
The render/network path is not exercised -- only the pure parse/derive/dedup logic.
"""

from __future__ import annotations

from ajoa_kit.models import SgFilters, SgJob
from ajoa_kit.startups_gallery import (
    build_jobs_url,
    derive_ats_ref,
    discover_ats_refs,
    parse_jobs,
)

_MID = "·"  # the middot delimiter between card fields


def test_build_jobs_url_encodes_only_nonempty_filters() -> None:
    url = build_jobs_url(SgFilters(location="San Francisco", job_title="designer"))
    assert url == "https://startups.gallery/jobs?location=San+Francisco&job-title=designer"
    assert build_jobs_url(SgFilters()) == "https://startups.gallery/jobs"


def test_derive_ats_ref_maps_known_hosts_and_rejects_others() -> None:
    ashby = derive_ats_ref("https://jobs.ashbyhq.com/method/abc-123?utm_source=x")
    assert ashby is not None
    assert (ashby.ats, ashby.slug) == ("ashby", "method")
    gh = derive_ats_ref("https://job-boards.greenhouse.io/blackforestlabs/jobs/456")
    assert gh is not None
    assert (gh.ats, gh.slug) == ("greenhouse", "blackforestlabs")
    lever = derive_ats_ref("https://jobs.lever.co/acme/xyz")
    assert lever is not None
    assert (lever.ats, lever.slug) == ("lever", "acme")
    assert derive_ats_ref("https://example.com/careers/eng") is None  # unknown host
    assert derive_ats_ref("https://jobs.ashbyhq.com/") is None  # no slug segment
    assert derive_ats_ref("https://jobs.ashbyhq.com/Civic%20Roundtable/x") is None  # encoded space


def test_parse_jobs_recovers_slug_location_posted_and_degrades() -> None:
    # Real structure: title is a separate node; the middot line is "Company . Location . Posted",
    # so html_to_text flattens title+company into the leading field (see ADR-0004 Phase 2).
    html = (
        '<a href="https://jobs.ashbyhq.com/method/abc">'
        "<div>Senior Software Engineer</div>"
        f"<div>Method {_MID} New York, NY {_MID} Posted on Aug 21, 2026</div>"
        "</a>"
        '<a href="https://startups.gallery/internal/x">Some internal link</a>'  # non-ATS -> skipped
        '<a href="https://job-boards.greenhouse.io/blackforestlabs/jobs/9">'
        "<div>Field Marketing Manager</div><div>Black Forest Labs</div>"  # degrade: no loc/posted
        "</a>"
    )
    jobs = parse_jobs(html)
    assert len(jobs) == 2
    first = jobs[0]
    assert first.ats_ref is not None
    assert first.ats_ref.slug == "method"
    assert first.location == "New York, NY"  # last non-posted field
    assert first.posted_at == "Posted on Aug 21, 2026"
    assert "Senior Software Engineer" in first.heading  # role+company flattened together
    assert jobs[1].ats_ref is not None
    assert jobs[1].ats_ref.slug == "blackforestlabs"
    assert jobs[1].location == ""  # single meta field -> location blank, not a crash
    assert jobs[1].posted_at == ""


def test_discover_ats_refs_dedupes_by_ats_and_slug() -> None:
    jobs = [
        SgJob(apply_url="u1", ats_ref=derive_ats_ref("https://jobs.ashbyhq.com/method/a")),
        SgJob(apply_url="u2", ats_ref=derive_ats_ref("https://jobs.ashbyhq.com/method/b")),  # dup
        SgJob(apply_url="u3", ats_ref=derive_ats_ref("https://jobs.lever.co/acme/c")),
        SgJob(apply_url="u4", ats_ref=None),
    ]
    refs = discover_ats_refs(jobs)
    assert [(r.ats, r.slug) for r in refs] == [("ashby", "method"), ("lever", "acme")]
