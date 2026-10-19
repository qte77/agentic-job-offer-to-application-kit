"""Value-add tests for ``polite_fetch``: robots.txt enforcement and per-host spacing (#454).

The policy follows RFC 9309: a missing robots.txt (4xx) means no rules; an unreachable one (5xx or
network error) means "assume disallowed", so the source is skipped with a reason, never fetched.
``polyfetch_scrape`` is faked in ``sys.modules`` so these run offline.
"""

from __future__ import annotations

import sys
import types

import pytest

from ajoa_kit import polite


class _Resp:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self.body = body
        self.backend = "fake"


def _install(monkeypatch: pytest.MonkeyPatch, routes: dict[str, object]) -> list[str]:
    """Fake polyfetch: ``routes`` maps URL -> _Resp or an exception to raise. Returns call log."""
    calls: list[str] = []
    mod = types.ModuleType("polyfetch_scrape")

    def fetch(url: str, **_kw: object) -> _Resp:
        calls.append(url)
        hit = routes.get(url, _Resp(200, b"{}"))
        if isinstance(hit, Exception):
            raise hit
        assert isinstance(hit, _Resp)
        return hit

    mod.fetch = fetch
    monkeypatch.setitem(sys.modules, "polyfetch_scrape", mod)
    monkeypatch.setattr(polite, "_ROBOTS", {})
    monkeypatch.setattr(polite, "_LAST", {})
    return calls


def test_allowed_url_is_fetched_and_robots_read_once_per_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install(
        monkeypatch,
        {"https://a.example/robots.txt": _Resp(200, b"User-agent: *\nDisallow: /embed/\n")},
    )
    monkeypatch.setattr(polite.time, "sleep", lambda _s: None)
    polite.polite_fetch("https://a.example/v1/jobs")
    polite.polite_fetch("https://a.example/v1/other")
    assert calls.count("https://a.example/robots.txt") == 1
    assert "https://a.example/v1/other" in calls


def test_disallowed_url_is_skipped_without_fetching_it(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(
        monkeypatch,
        {"https://b.example/robots.txt": _Resp(200, b"User-agent: *\nDisallow: /api\n")},
    )
    with pytest.raises(polite.RobotsDisallowedError, match="disallows"):
        polite.polite_fetch("https://b.example/api/jobs")
    assert "https://b.example/api/jobs" not in calls


def test_missing_robots_means_no_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    # 4xx (incl. 401/403) = no robots.txt to obey (RFC 9309 2.3.1.3).
    calls = _install(monkeypatch, {"https://c.example/robots.txt": _Resp(401)})
    polite.polite_fetch("https://c.example/api/jobs")
    assert "https://c.example/api/jobs" in calls


class _StatusError(Exception):
    """Like polyfetch's typed terminal errors (AuthRequired, GoneError): carries ``.status``."""

    def __init__(self, status: int) -> None:
        super().__init__(f"terminal HTTP {status}")
        self.status = status


def test_robots_4xx_raised_as_an_error_still_means_no_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # polyfetch raises AuthRequired/GoneError for some 4xx instead of returning them; Ashby's
    # robots.txt answers 401, and 215 live sources were wrongly skipped before this.
    calls = _install(monkeypatch, {"https://g.example/robots.txt": _StatusError(401)})
    polite.polite_fetch("https://g.example/api/jobs")
    assert "https://g.example/api/jobs" in calls


@pytest.mark.parametrize("robots", [_Resp(503), _StatusError(502), OSError("connection reset")])
def test_unreachable_robots_skips_the_host(monkeypatch: pytest.MonkeyPatch, robots: object) -> None:
    # 5xx or a network error = assume complete disallow (RFC 9309 2.3.1.4); skip, never guess.
    calls = _install(monkeypatch, {"https://d.example/robots.txt": robots})
    with pytest.raises(polite.RobotsDisallowedError, match="unreachable"):
        polite.polite_fetch("https://d.example/api/jobs")
    assert "https://d.example/api/jobs" not in calls


def test_same_host_requests_are_spaced_by_crawl_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {"https://e.example/robots.txt": _Resp(200, b"User-agent: *\nCrawl-delay: 3\n")},
    )
    slept: list[float] = []
    monkeypatch.setattr(polite.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(polite.time, "sleep", slept.append)
    polite.polite_fetch("https://e.example/one")
    polite.polite_fetch("https://e.example/two")
    polite.polite_fetch("https://f.example/other-host")
    assert slept == [3.0]  # only the second same-host call waits; another host does not
