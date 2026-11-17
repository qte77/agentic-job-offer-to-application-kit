"""Value-add tests for ``slug_probe.fetch_status``, the liveness probe behind ``refresh`` (#214).

polyfetch reports some terminal 4xx (404/410 ``GoneError``, 401/403 ``AuthRequired``) by RAISING
a typed error that carries ``.status`` instead of returning a response. The probe used to swallow
every exception as "inconclusive", so ``refresh`` never marked a deleted posting stale: an audit
on 2026-11-10 found 8 score-5 ads answering 404/410 that ``refresh`` reported as live.
"""

from __future__ import annotations

import pytest

from ajoa_kit import refresh, slug_probe


class _StatusError(Exception):
    """Like polyfetch's typed terminal errors (GoneError, AuthRequired): carries ``.status``."""

    def __init__(self, status: int) -> None:
        super().__init__(f"terminal HTTP {status}")
        self.status = status


def _raise(exc: Exception):  # noqa: ANN202 -- test double
    def fetch(_url: str, **_kw: object) -> object:
        raise exc

    return fetch


@pytest.mark.parametrize("status", [404, 410])
def test_a_gone_posting_raised_as_an_error_is_reported_and_marked_stale(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    monkeypatch.setattr(slug_probe, "polite_fetch", _raise(_StatusError(status)))
    got = slug_probe.fetch_status("https://boards.example/jobs/1")
    assert got == status
    assert refresh.classify(corpus_delisted=False, status=got)


@pytest.mark.parametrize("exc", [OSError("connection reset"), _StatusError(503), ValueError("x")])
def test_network_errors_and_5xx_stay_inconclusive(
    monkeypatch: pytest.MonkeyPatch, exc: Exception
) -> None:
    # A flaky network or a server error must never expire a live entry.
    monkeypatch.setattr(slug_probe, "polite_fetch", _raise(exc))
    got = slug_probe.fetch_status("https://boards.example/jobs/1")
    assert got is None
    assert not refresh.classify(corpus_delisted=False, status=got)


class _Redirect:
    """A polyfetch response for an unfollowed 3xx: httpx/curl tiers set ``redirect_to`` (#260)."""

    def __init__(self, status: int, redirect_to: str | None) -> None:
        self.status = status
        self.redirect_to = redirect_to


POSTING = "https://job-boards.greenhouse.io/acme/jobs/123"


@pytest.mark.parametrize(
    "target",
    [
        "https://job-boards.greenhouse.io/acme?error=true",  # Greenhouse closed-posting bounce
        "https://job-boards.greenhouse.io/acme",  # board listing is the posting's parent
        "/acme/",  # relative Location, listing with trailing slash
    ],
)
def test_a_redirect_to_the_board_listing_is_gone_and_marked_stale(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    # #488: a closed posting 302s to the board listing instead of answering 404.
    monkeypatch.setattr(slug_probe, "polite_fetch", lambda *_a, **_k: _Redirect(302, target))
    got = slug_probe.fetch_status(POSTING)
    assert got == 404
    assert refresh.classify(corpus_delisted=False, status=got)


@pytest.mark.parametrize(
    "target",
    [
        "https://job-boards.greenhouse.io/acme/jobs/123",  # same URL, e.g. http -> https
        "https://job-boards.greenhouse.io/acme/jobs/123/",  # trailing slash
        "/acme/jobs/123?gh_jid=123",  # same posting, tracking query
        "https://job-boards.greenhouse.io/acme/jobs/456",  # canonical posting id: still a posting
    ],
)
def test_a_redirect_to_a_posting_stays_live(monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    monkeypatch.setattr(slug_probe, "polite_fetch", lambda *_a, **_k: _Redirect(301, target))
    got = slug_probe.fetch_status(POSTING)
    assert got == 301
    assert not refresh.classify(corpus_delisted=False, status=got)


@pytest.mark.parametrize(
    "target",
    [
        "https://other.example/",  # another host's root
        "https://other.example/acme",  # another host, an ancestor path of the posting
        "https://other.example/acme?error=true",  # error=true on another host
        "ftp://job-boards.greenhouse.io/acme",  # not an http(s) target
    ],
)
def test_a_redirect_off_the_posting_host_is_not_a_listing_bounce(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    # #499: only a redirect on the posting's own host can be its board listing.
    monkeypatch.setattr(slug_probe, "polite_fetch", lambda *_a, **_k: _Redirect(302, target))
    got = slug_probe.fetch_status(POSTING)
    assert got == 302
    assert not refresh.classify(corpus_delisted=False, status=got)


def test_a_same_host_redirect_to_the_root_is_a_listing_bounce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(slug_probe, "polite_fetch", lambda *_a, **_k: _Redirect(302, "/"))
    assert slug_probe.fetch_status(POSTING) == 404


def test_an_empty_location_keeps_the_redirect_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slug_probe, "polite_fetch", lambda *_a, **_k: _Redirect(302, ""))
    assert slug_probe.fetch_status(POSTING) == 302


def test_a_feed_moved_to_another_host_is_not_reported_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # verify_sources probes feeds through fetch_status: a feed moved to a CDN root stays live.
    monkeypatch.setattr(
        slug_probe, "polite_fetch", lambda *_a, **_k: _Redirect(301, "https://cdn.example.net/")
    )
    assert slug_probe.fetch_status("https://blog.example.org/news/feed.xml") == 301
