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
