"""Value-add tests for the company-hiring trend series (#2 / plan 006 S2a).

Sharp edges: the geo-x-field bucket key format (the permanent published contract), job-count
bucketing (each JD counted once in its first_seen bucket, undated skipped), day->week/month roll-up
agreement, and — the boundary guarantee — NO company name ever appears in the publishable geo
series (company names live only in the git-ignored local series).
"""

import json
from pathlib import Path

import pytest

from ajoa_kit import companies_trend, trend_snapshot


def _read_ndjson(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def test_geo_field_key_format() -> None:
    # region present -> "City, Region · field"; Remote (blank region) -> "Remote · field";
    # no lane -> the _field "unscored" fallback. This string is the permanent published counts key.
    berlin = {"location": "Berlin, DE", "lane_hint": "backend"}
    remote = {"location": "Remote", "remote": True, "lane_hint": "ml"}
    bare = {"location": ""}
    assert companies_trend.geo_field_key(berlin, {}) == "Berlin, DE · backend"
    assert companies_trend.geo_field_key(remote, {}) == "Remote · ml"
    assert companies_trend.geo_field_key(bare, {}) == "Unknown · unscored"
    # a scored lane refines the field over the coarse lane_hint
    assert companies_trend.geo_field_key({"id": "x", "location": "Berlin, DE"}, {"x": "ml"}) == (
        "Berlin, DE · ml"
    )
    # arc-010 item 12: a blank-location swissdevjobs job still surfaces a region via provenance,
    # instead of publishing an all-Swiss slice of the geo trend under a bare "Unknown" bucket.
    sdj = {"location": "", "source": "swissdevjobs"}
    assert companies_trend.geo_field_key(sdj, {}) == "Unknown, Switzerland · unscored"


def test_bucket_by_day_counts_jobs_once_and_skips_undated() -> None:
    jobs = [
        {
            "company": "Acme",
            "location": "Berlin, DE",
            "lane_hint": "backend",
            "first_seen": "2026-06-01",
        },
        {
            "company": "Acme",
            "location": "Berlin, DE",
            "lane_hint": "backend",
            "first_seen": "2026-06-01",
        },
        {
            "company": "Bolt",
            "location": "Remote",
            "remote": True,
            "lane_hint": "ml",
            "first_seen": "2026-06-02",
        },
        {
            "company": "Zeta",
            "location": "Munich",
            "lane_hint": "fe",
            "first_seen": "",
        },  # undated -> skip
    ]
    days, skipped = companies_trend.bucket_by_day(
        jobs, lambda j: companies_trend.geo_field_key(j, {})
    )
    assert days["2026-06-01"] == {"Berlin, DE · backend": 2}  # two roles, one bucket key
    assert days["2026-06-02"] == {"Remote · ml": 1}
    assert skipped == 1  # the undated JD cannot be placed in time
    # the local company view keys on company; a blank company is skipped (can't attribute)
    cdays, _ = companies_trend.bucket_by_day(
        [*jobs, {"company": "", "location": "X", "first_seen": "2026-06-01"}],
        companies_trend.company_key,
    )
    assert cdays["2026-06-01"] == {"Acme": 2}  # blank-company row not counted


def test_rollups_agree_with_days() -> None:
    # weekly/monthly are trend_snapshot roll-ups of the same days -> counts can never disagree.
    jobs = [
        {
            "company": "Acme",
            "location": "Berlin, DE",
            "lane_hint": "be",
            "first_seen": "2026-06-01",
        },  # Mon W23
        {
            "company": "Acme",
            "location": "Berlin, DE",
            "lane_hint": "be",
            "first_seen": "2026-06-03",
        },  # Wed W23
        {
            "company": "Bolt",
            "location": "Berlin, DE",
            "lane_hint": "be",
            "first_seen": "2026-06-29",
        },  # Mon W27, Jun
    ]
    key = lambda j: companies_trend.geo_field_key(j, {})  # noqa: E731
    days, _ = companies_trend.bucket_by_day(jobs, key)
    weeks = trend_snapshot.weekly_from_daily(days)
    months = trend_snapshot.monthly_from_daily(days)
    assert weeks["2026-W23"] == {"Berlin, DE · be": 2}  # two days summed
    assert weeks["2026-W27"] == {"Berlin, DE · be": 1}
    assert months["2026-06"] == {"Berlin, DE · be": 3}  # whole month summed
    assert sum(sum(c.values()) for c in weeks.values()) == sum(
        sum(c.values()) for c in days.values()
    )


def test_main_emits_public_geo_and_local_company_with_no_company_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = tmp_path / "results"
    results.mkdir()
    public = tmp_path / "public-data"
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    monkeypatch.setenv("AJOA_PUBLIC_DATA_DIR", str(public))
    companies = ["Acme", "Bolt", "Zeta"]
    (results / "corpus.json").write_text(
        json.dumps(
            [
                {
                    "id": "a",
                    "company": "Acme",
                    "location": "Berlin, DE",
                    "lane_hint": "backend",
                    "first_seen": "2026-06-01",
                },
                {
                    "id": "b",
                    "company": "Acme",
                    "location": "Berlin, DE",
                    "lane_hint": "backend",
                    "first_seen": "2026-06-02",
                },
                {
                    "id": "c",
                    "company": "Bolt",
                    "location": "Remote",
                    "remote": True,
                    "lane_hint": "ml",
                    "first_seen": "2026-06-03",
                },
                {
                    "id": "d",
                    "company": "",
                    "location": "",
                    "first_seen": "2026-06-03",
                },  # Unknown · unscored
                {
                    "id": "e",
                    "company": "Zeta",
                    "location": "Munich",
                    "lane_hint": "fe",
                    "first_seen": "",
                },  # skipped
            ]
        )
    )
    companies_trend.main()

    # Publishable geo-x-field trio (weekly rolled from days == monthly for a single month).
    weekly = _read_ndjson(public / "hiring-weekly.ndjson")
    assert len(weekly) == 1
    assert weekly[0]["counts"] == {
        "Berlin, DE · backend": 2,
        "Remote · ml": 1,
        "Unknown · unscored": 1,
    }
    daily = _read_ndjson(public / "hiring-daily.ndjson")
    assert {r["date"] for r in daily} == {"2026-06-01", "2026-06-02", "2026-06-03"}
    monthly = _read_ndjson(public / "hiring-monthly.ndjson")
    assert monthly[0]["month"] == "2026-06"
    assert monthly[0]["counts"]["Berlin, DE · backend"] == 2

    # BOUNDARY: no company name may appear in any publishable counts key.
    public_keys = {
        k
        for f in ("hiring-weekly", "hiring-daily", "hiring-monthly")
        for rec in _read_ndjson(public / f"{f}.ndjson")
        for k in rec["counts"]
    }
    assert not any(co in key for key in public_keys for co in companies)

    # Local per-company weekly (git-ignored results/) — company keys, never in public-data/.
    local = _read_ndjson(results / "hiring-companies.ndjson")
    assert local[0]["counts"] == {"Acme": 2, "Bolt": 1}  # blank-company row excluded
    assert not (public / "hiring-companies.ndjson").exists()
