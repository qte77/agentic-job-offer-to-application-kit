"""Value-add tests for the source freshness re-probe (#217).

Cover the pure stamping core (:func:`verify_sources.reprobe`) with injected probes (no network):
a live feed (2xx/3xx) and a live ats board (a role count) get ``_date_verified`` stamped with
today; a 4xx feed, an unreachable feed (``None``), and a dead board (``None``) are left unstamped
and reported. Plus :func:`verify_sources.main`'s dry-run (writes nothing) and that the non-source
keys (``_comment`` / ``_blocked`` / ``_deferred``) survive the write round-trip.

Also cover the two extensions: ``aggregators`` (probed via the shared
:data:`ajoa_kit.sources.AGGREGATOR_ENDPOINTS` constants, since the entries carry no ``url``) and
``discovery`` (probed by ``url`` like a feed) are re-stamped too — surgically, so their multi-line
``_tos`` prose blocks stay byte-identical — and a stamp never moves backwards in time.
"""

from __future__ import annotations

import json

import pytest

from ajoa_kit import verify_sources
from ajoa_kit.sources import AGGREGATOR_ENDPOINTS

TODAY = "2026-07-04"


def test_reprobe_stamps_live_leaves_dead_and_reports() -> None:
    feeds = [
        {"source": "live", "url": "https://f/live"},  # 200 -> stamp
        {"source": "moved", "url": "https://f/moved"},  # 301 -> stamp (reachable)
        {"source": "gone", "url": "https://f/gone"},  # 404 -> unconfirmed (not-None but dead)
        {"source": "down", "url": "https://f/down"},  # None -> unconfirmed (unreachable)
    ]
    ats = [
        {"ats": "greenhouse", "slug": "live", "company": "L"},  # count 7 -> stamp
        {"ats": "greenhouse", "slug": "empty", "company": "E"},  # count 0 -> stamp (endpoint live)
        {"ats": "lever", "slug": "dead", "company": "D"},  # None -> unconfirmed
    ]

    def probe_feed(url: str) -> int | None:
        return {"https://f/live": 200, "https://f/moved": 301, "https://f/gone": 404}.get(url)

    def probe_ats(ats_name: str, slug: str) -> int | None:
        return {("greenhouse", "live"): 7, ("greenhouse", "empty"): 0}.get((ats_name, slug))

    unconfirmed = verify_sources.reprobe(feeds, ats, probe_feed, probe_ats, TODAY)

    assert feeds[0]["_date_verified"] == TODAY
    assert feeds[1]["_date_verified"] == TODAY  # a 3xx redirect is still reachable
    assert "_date_verified" not in feeds[2]  # 404 is not-None but dead
    assert "_date_verified" not in feeds[3]  # unreachable stays untouched
    assert ats[0]["_date_verified"] == TODAY
    assert ats[1]["_date_verified"] == TODAY  # an empty-but-live board is still a live source
    assert "_date_verified" not in ats[2]
    labels = {e.get("source") or e.get("slug") for e in unconfirmed}
    assert labels == {"gone", "down", "dead"}


def test_reprobe_refreshes_an_existing_stamp() -> None:
    feeds = [{"source": "s", "url": "https://f/s", "_date_verified": "2020-01-01"}]
    unconfirmed = verify_sources.reprobe(feeds, [], lambda _u: 200, lambda _a, _s: None, TODAY)
    assert feeds[0]["_date_verified"] == TODAY  # re-dated to today
    assert unconfirmed == []


def test_reprobe_covers_aggregators_and_discovery() -> None:
    # aggregators carry no url — the endpoint lives in sources.AGGREGATOR_ENDPOINTS; discovery does
    aggregators = [{"name": "arbeitnow"}, {"name": "themuse"}, {"name": "unknown-aggregator"}]
    discovery = [
        {"name": "yc-oss", "url": "https://d/live"},
        {"name": "rotten", "url": "https://d/gone"},
    ]
    probed: list[str] = []

    def probe_feed(url: str) -> int | None:
        probed.append(url)
        return {
            AGGREGATOR_ENDPOINTS["arbeitnow"]: 200,
            AGGREGATOR_ENDPOINTS["themuse"]: 503,
            "https://d/live": 200,
        }.get(url)

    unconfirmed = verify_sources.reprobe(
        [], [], probe_feed, lambda _a, _s: None, TODAY, aggregators=aggregators, discovery=discovery
    )

    assert aggregators[0]["_date_verified"] == TODAY  # endpoint answered 200
    assert "_date_verified" not in aggregators[1]  # 503 -> unconfirmed
    assert "_date_verified" not in aggregators[2]  # no known endpoint -> never probed nor stamped
    assert AGGREGATOR_ENDPOINTS["arbeitnow"] in probed  # one URL source of truth: sources.py
    assert discovery[0]["_date_verified"] == TODAY
    assert "_date_verified" not in discovery[1]
    assert {e["name"] for e in unconfirmed} == {"themuse", "unknown-aggregator", "rotten"}


def test_reprobe_never_moves_a_stamp_backwards() -> None:
    # the real incident: a manual sweep dated 2026-07-28 ran over probe-confirmed 2026-08-01 entries
    feeds = [
        {"source": "newer", "url": "https://f/a", "_date_verified": "2026-08-01"},
        {"source": "older", "url": "https://f/b", "_date_verified": "2026-06-01"},
    ]
    verify_sources.reprobe(feeds, [], lambda _u: 200, lambda _a, _s: None, "2026-07-28")
    assert feeds[0]["_date_verified"] == "2026-08-01"  # kept; a stamp is monotonic
    assert feeds[1]["_date_verified"] == "2026-07-28"  # older stamp still moves forward


# A realistic seed: feeds/ats entries are one-line each, but aggregators/_deferred are
# intentionally multi-line (a nested `sources` array) — the writer must touch only feeds/ats.
_AGG_LINE = '    {"name": "arb", "_date_verified": "2026-06-20", "sources": [{"n": 1}, {"n": 2}]}'
_SEED_TEXT = f"""{{
  "_comment": "keep me",
  "feeds": [
    {{"source": "a", "url": "https://f/a"}}
  ],
  "ats": [
    {{"ats": "greenhouse", "slug": "b", "company": "B"}},
    {{"ats": "lever", "slug": "c", "company": "C", "_date_verified": "2020-01-01"}}
  ],
  "aggregators": [
{_AGG_LINE}
  ],
  "_blocked": [
    {{"_platform": "linkedin", "_reason": "ToS"}}
  ]
}}
"""


def _seed(cfg_dir: object) -> object:
    seed_path = cfg_dir / "default-seed.json"  # type: ignore[operator]
    seed_path.write_text(_SEED_TEXT)
    return seed_path


def test_main_stamps_feeds_ats_and_leaves_other_sections_verbatim(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "config"  # type: ignore[operator]
    cfg_dir.mkdir()
    seed_path = _seed(cfg_dir)
    monkeypatch.setenv("AJOA_CONFIG_DIR", str(cfg_dir))

    verify_sources.main(today=TODAY, probe_feed=lambda _u: 200, probe_ats=lambda _a, _s: 3)

    raw = seed_path.read_text()
    # feeds/ats stamped, each still on one line (not exploded)
    assert '{"source": "a", "url": "https://f/a", "_date_verified": "2026-07-04"}' in raw
    out = json.loads(raw)
    assert out["ats"][0]["_date_verified"] == TODAY
    assert out["ats"][1]["_date_verified"] == TODAY  # existing stamp re-dated (was 2020-01-01)
    # the multi-line aggregators block is byte-identical — no churn outside feeds/ats
    assert _AGG_LINE in raw
    assert out["_comment"] == "keep me"
    assert out["_blocked"] == [{"_platform": "linkedin", "_reason": "ToS"}]


def test_main_dry_run_writes_nothing(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "config"  # type: ignore[operator]
    cfg_dir.mkdir()
    seed_path = _seed(cfg_dir)
    before = seed_path.read_text()
    monkeypatch.setenv("AJOA_CONFIG_DIR", str(cfg_dir))

    verify_sources.main(
        today=TODAY, dry_run=True, probe_feed=lambda _u: 200, probe_ats=lambda *_: 1
    )

    assert seed_path.read_text() == before  # reported, not written


# The real seed shape for aggregators/discovery: each entry spans two lines, the second holding a
# long `_tos` prose block. Re-serializing it with json.dumps would reflow that block onto one line
# and churn the whole seed, so only the `_date_verified` VALUE may be rewritten.
_ML_TOS_AGG = (
    '     "_tos": "Public job-board-api, robots-ALLOWED (200, x-ratelimit-limit:5); ToS §11 '
    'asks for a backlink. The dashboard emits only aggregate {week,counts} facts (Feist)."},'
)
_ML_TOS_DISC = (
    '     "_tos": "Community mirror of a public directory, robots-clean read-only GET; only '
    'non-copyrightable facts (Feist) are extracted and aggregated LOCALLY, never published."}'
)


def _agg_open(stamp: str) -> str:
    return '    {"name": "arbeitnow", "_date_verified": "' + stamp + '",'


def _disc_open(stamp: str) -> str:
    return (
        '    {"name": "yc-oss", "format": "yc-oss", "url": "https://d/live", '
        '"_date_verified": "' + stamp + '",'
    )


_ML_SEED_TEXT = "\n".join(
    [
        "{",
        '  "_comment": "keep me",',
        '  "feeds": [],',  # an inline empty array opens no section
        '  "ats": [',
        '    {"ats": "greenhouse", "slug": "b", "company": "B"}',
        "  ],",
        '  "aggregators": [',
        _agg_open("2026-06-20"),
        _ML_TOS_AGG,
        '    {"name": "themuse", "_date_verified": "2026-08-30",',
        '     "_tos": "a stamp NEWER than today — the monotonic guard must keep it."}',
        "  ],",
        '  "discovery": [',
        _disc_open("2026-06-13"),
        _ML_TOS_DISC,
        "  ]",
        "}",
        "",
    ]
)


def _probe_known(url: str) -> int | None:
    return 200 if url in {*AGGREGATOR_ENDPOINTS.values(), "https://d/live"} else None


def test_main_restamps_multiline_entries_without_reflowing_tos(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "config"  # type: ignore[operator]
    cfg_dir.mkdir()
    seed_path = cfg_dir / "default-seed.json"
    seed_path.write_text(_ML_SEED_TEXT)
    monkeypatch.setenv("AJOA_CONFIG_DIR", str(cfg_dir))

    verify_sources.main(today=TODAY, probe_feed=_probe_known, probe_ats=lambda _a, _s: 3)

    raw = seed_path.read_text()
    assert _ML_TOS_AGG in raw  # the prose block is byte-identical — never reflowed
    assert _ML_TOS_DISC in raw
    assert _agg_open(TODAY) in raw  # only the date VALUE changed on the entry's opening line
    assert _disc_open(TODAY) in raw
    assert len(raw.splitlines()) == len(_ML_SEED_TEXT.splitlines())  # layout preserved
    out = json.loads(raw)
    assert out["aggregators"][0]["_date_verified"] == TODAY
    assert out["aggregators"][1]["_date_verified"] == "2026-08-30"  # monotonic guard, via main()
    assert out["discovery"][0]["_date_verified"] == TODAY
    assert out["ats"][0]["_date_verified"] == TODAY
    assert out["_comment"] == "keep me"


_UNSTAMPED_SEED_TEXT = "\n".join(
    [
        "{",
        '  "aggregators": [',
        '    {"name": "arbeitnow",',
        '     "_tos": "no _date_verified line for the re-stamp to replace"}',
        "  ]",
        "}",
        "",
    ]
)


def test_main_refuses_to_write_a_seed_it_cannot_restamp(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the parse-back guard now covers aggregators/discovery: fail loud, never write a seed whose
    # text disagrees with the probe result
    cfg_dir = tmp_path / "config"  # type: ignore[operator]
    cfg_dir.mkdir()
    seed_path = cfg_dir / "default-seed.json"
    seed_path.write_text(_UNSTAMPED_SEED_TEXT)
    monkeypatch.setenv("AJOA_CONFIG_DIR", str(cfg_dir))

    with pytest.raises(ValueError, match="aborted"):
        verify_sources.main(today=TODAY, probe_feed=_probe_known, probe_ats=lambda _a, _s: 3)

    assert seed_path.read_text() == _UNSTAMPED_SEED_TEXT  # untouched
