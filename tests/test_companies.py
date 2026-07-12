"""Value-add tests for the local company-hiring tracker aggregation (``companies``, #284).

Cover the sharp edges the aggregation exists to solve: the free-text ``location`` parse that MERGES
duplicate spellings into one city bucket while KEEPING the region/country qualifier (nothing is
discarded — the raw corpus is untouched); the "active" recency filter; the field fallback chain
(scored lane -> ingest ``lane_hint`` -> ``unscored``); the momentum depth guard (no heating/cooling
tag until the history is deep enough); and deterministic ordering.
"""

from __future__ import annotations

from ajoa_kit import companies


def _jd(
    jid: str,
    *,
    company: str = "Acme",
    location: str = "Remote",
    remote: object = None,
    lane_hint: str = "engineering",
    first_seen: str = "2026-07-01",
    last_seen: str = "2026-07-10",
) -> dict:
    return {
        "id": jid,
        "company": company,
        "location": location,
        "remote": remote,
        "lane_hint": lane_hint,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


# --- parse_geo -------------------------------------------------------------------------


def test_parse_geo_keeps_city_and_region_qualifier() -> None:
    # The redundant qualifier is kept as region (not discarded) while the city is the group key.
    assert companies.parse_geo("San Francisco, CA") == ("San Francisco", "CA")
    assert companies.parse_geo("London, UK") == ("London", "UK")
    assert companies.parse_geo("Bengaluru, India") == ("Bengaluru", "India")


def test_parse_geo_merges_spelling_and_abbrev_variants_to_one_city() -> None:
    # Same place, different spelling/abbrev -> one canonical city (so the ranking isn't split).
    assert companies.parse_geo("San Francisco, California")[0] == "San Francisco"
    assert companies.parse_geo("SF")[0] == "San Francisco"
    assert companies.parse_geo("Bangalore, India")[0] == "Bengaluru"
    assert companies.parse_geo("München")[0] == "Munich"
    assert companies.parse_geo("New York City, NY")[0] == "New York"


def test_parse_geo_folds_the_whole_remote_family() -> None:
    # "remote" anywhere in the primary segment -> the Remote bucket (the ~5 variants collapse).
    for loc in ("Remote", "Remote - US", "Remote U.S.", "United States (Remote)"):
        assert companies.parse_geo(loc) == ("Remote", ""), loc
    # An empty location with the record's remote flag set is Remote too.
    assert companies.parse_geo("", remote=True) == ("Remote", "")


def test_parse_geo_empty_is_unknown_not_remote() -> None:
    assert companies.parse_geo("") == ("Unknown", "")
    assert companies.parse_geo("   ", remote=False) == ("Unknown", "")


def test_parse_geo_multi_location_takes_the_primary_segment() -> None:
    assert companies.parse_geo("San Francisco, CA | New York City, NY") == ("San Francisco", "CA")
    assert companies.parse_geo("Berlin • Munich")[0] == "Berlin"


def test_parse_geo_maps_placeholder_junk_to_unknown() -> None:
    # Scraped placeholder strings aren't real cities -> Unknown (folded into _CITY_ALIASES).
    for loc in ("LOCATION", "N/A", "na", "Please Update Office Field"):
        assert companies.parse_geo(loc) == ("Unknown", ""), loc


def test_parse_geo_strips_trailing_org_suffix_keeping_region() -> None:
    # "<city> Office/HQ/Hub" is the same place -> strip the trailing org suffix, keep the qualifier.
    assert companies.parse_geo("San Francisco Office") == ("San Francisco", "")
    assert companies.parse_geo("San Francisco HQ, CA") == ("San Francisco", "CA")
    assert companies.parse_geo("London Hub")[0] == "London"


def test_parse_geo_suffix_strip_composes_with_city_alias() -> None:
    # Strip runs before the alias lookup: "New York City Office" -> "New York City" -> "New York".
    assert companies.parse_geo("New York City Office")[0] == "New York"


# --- aggregate_companies ---------------------------------------------------------------


def test_aggregate_merges_city_variants_into_one_counted_row() -> None:
    corpus = [
        _jd("a", location="San Francisco"),
        _jd("b", location="San Francisco, CA"),
        _jd("c", location="San Francisco, California"),
    ]
    rows = companies.aggregate_companies(corpus)
    sf = [r for r in rows if r.city == "San Francisco"]
    assert len(sf) == 1  # three spellings collapsed to one bucket
    assert sf[0].count == 3
    assert sf[0].region == "CA"  # modal non-empty qualifier is surfaced for the merged city


def test_aggregate_counts_only_active_records() -> None:
    # Reference recency is the newest last_seen in the corpus; a long-delisted row drops out.
    corpus = [
        _jd("fresh", company="Acme", last_seen="2026-07-10"),
        _jd(
            "gone", company="Acme", last_seen="2026-05-01"
        ),  # >7d older than the newest -> inactive
    ]
    rows = companies.aggregate_companies(corpus, active_days=7)
    acme = [r for r in rows if r.company == "Acme"]
    assert sum(r.count for r in acme) == 1


def test_aggregate_field_fallback_prefers_scored_lane_then_hint_then_unscored() -> None:
    corpus = [
        _jd("scored", company="A", lane_hint="engineering"),
        _jd("hinted", company="B", lane_hint="cloud"),
        _jd("bare", company="C", lane_hint=""),
    ]
    rows = companies.aggregate_companies(corpus, lane_by_id={"scored": "architect"})
    field = {r.company: r.field for r in rows}
    assert field["A"] == "architect"  # scored lane wins over the hint
    assert field["B"] == "cloud"  # falls back to lane_hint
    assert field["C"] == "unscored"  # no signal at all


def test_aggregate_momentum_is_none_when_history_is_shallow() -> None:
    # first_seen spanning under ~4 weeks -> the snapshot ships without a heating/cooling claim.
    corpus = [
        _jd("a", first_seen="2026-07-01", last_seen="2026-07-10"),
        _jd("b", first_seen="2026-07-08", last_seen="2026-07-10"),
    ]
    rows = companies.aggregate_companies(corpus)
    assert rows
    assert all(r.momentum is None for r in rows)


def test_aggregate_momentum_lights_up_as_heating_once_history_is_deep() -> None:
    # history spanning ~4+ weeks: a company whose recent-window intake outweighs the prior heats.
    corpus = [
        _jd("old1", company="Heat", first_seen="2026-06-01", last_seen="2026-07-20"),
        _jd("recent1", company="Heat", first_seen="2026-07-15", last_seen="2026-07-20"),
        _jd("recent2", company="Heat", first_seen="2026-07-18", last_seen="2026-07-20"),
    ]
    row = next(r for r in companies.aggregate_companies(corpus) if r.company == "Heat")
    assert row.momentum == "heating"


def test_aggregate_output_is_deterministically_ordered() -> None:
    corpus = [
        _jd("1", company="Zeta", location="Berlin"),
        _jd("2", company="Alpha", location="Berlin"),
        _jd("3", company="Alpha", location="Berlin"),
    ]
    rows = companies.aggregate_companies(corpus)
    berlin = [(r.city, r.field, -r.count, r.company) for r in rows]
    assert berlin == sorted(berlin)  # stable (city, field, -count, company) order
