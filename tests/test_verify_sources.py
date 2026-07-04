"""Value-add tests for the source freshness re-probe (#217).

Cover the pure stamping core (:func:`verify_sources.reprobe`) with injected probes (no network):
a live feed (2xx/3xx) and a live ats board (a role count) get ``_date_verified`` stamped with
today; a 4xx feed, an unreachable feed (``None``), and a dead board (``None``) are left unstamped
and reported. Plus :func:`verify_sources.main`'s dry-run (writes nothing) and that the non-source
keys (``_comment`` / ``_blocked`` / ``_deferred`` / ``aggregators``) survive the write round-trip.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit import verify_sources

if TYPE_CHECKING:
    import pytest

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
