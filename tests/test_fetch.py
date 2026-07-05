"""Value-add tests for the network helpers ``get_json`` / ``get_bytes``.

Every adapter test monkeypatches these out, so the real status-check + parse logic in
``sources.get_json`` / ``sources.get_bytes`` is otherwise unexercised. The helpers
lazy-import ``polyfetch_scrape`` (deliberately absent from this repo's venv), so a fake
module is injected into ``sys.modules`` — these run fully offline, no ``network`` mark.
"""

from __future__ import annotations

import sys
import types

import pytest

from ajoa_kit import sources


class _Resp:
    def __init__(self, status: int, body: object, backend: str) -> None:
        self.status = status
        self.body = body
        self.backend = backend


def _install(
    monkeypatch: pytest.MonkeyPatch, resp: _Resp
) -> tuple[type[Exception], dict[str, object]]:
    """Inject a fake ``polyfetch_scrape`` whose ``fetch`` returns ``resp``; capture the call."""
    mod = types.ModuleType("polyfetch_scrape")

    class FetchError(Exception):
        pass

    calls: dict[str, object] = {}

    def fetch(url: str, headers: dict[str, str] | None = None) -> _Resp:
        calls["url"] = url
        calls["headers"] = headers
        return resp

    mod.FetchError = FetchError
    mod.fetch = fetch
    monkeypatch.setitem(sys.modules, "polyfetch_scrape", mod)
    return FetchError, calls


def test_get_json_parses_body_and_sends_accept_header(monkeypatch: pytest.MonkeyPatch) -> None:
    _, calls = _install(monkeypatch, _Resp(200, b'{"jobs": [1, 2]}', "curl_cffi"))
    data, backend = sources.get_json("https://api.example/jobs")
    assert data == {"jobs": [1, 2]}  # body parsed as JSON
    assert backend == "curl_cffi"  # polyfetch backend passed through, not swallowed
    assert calls["url"] == "https://api.example/jobs"
    assert calls["headers"] == {"Accept": "application/json"}  # JSON sources need this header


def test_get_json_raises_fetcherror_on_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    # A non-200 must raise (status + backend in the message) so a junk error body is never
    # fed to json.loads and collect() records the source as a failure.
    fetch_error, _ = _install(monkeypatch, _Resp(404, b"<html>not found</html>", "httpx"))
    with pytest.raises(fetch_error, match=r"404.*httpx"):
        sources.get_json("https://api.example/jobs")


def test_get_bytes_returns_raw_body_without_accept_header(monkeypatch: pytest.MonkeyPatch) -> None:
    _, calls = _install(monkeypatch, _Resp(200, b"<xml/>", "playwright"))
    body, backend = sources.get_bytes("https://api.example/feed.xml")
    assert body == b"<xml/>"  # raw bytes returned untouched (XML/RSS feeds)
    assert backend == "playwright"
    assert calls["headers"] is None  # unlike get_json, no JSON Accept header is forced


def test_get_bytes_raises_fetcherror_on_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_error, _ = _install(monkeypatch, _Resp(500, b"", "httpx"))
    with pytest.raises(fetch_error, match=r"500"):
        sources.get_bytes("https://api.example/feed.xml")
