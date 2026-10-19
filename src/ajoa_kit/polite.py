"""Polite fetching: obey robots.txt and space requests per host (#454, ADR-0002).

Every network call goes through :func:`polite_fetch`. Per origin, robots.txt is read once and
checked for ``User-agent: *`` (polyfetch rotates browser User-Agents, so no named group applies).
Policy per RFC 9309: a 4xx robots.txt means no rules; a 5xx or network error means assume
disallowed, so the URL is skipped with :class:`RobotsDisallowed` rather than fetched. Requests to
the same host are spaced by max(:data:`MIN_INTERVAL`, the host's ``Crawl-delay``). A skipped source
surfaces in ingest's ``sources ok / failed`` summary like any other fetch failure.

``polyfetch_scrape`` is imported lazily so this module stays importable offline.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

if TYPE_CHECKING:
    from collections.abc import Callable

MIN_INTERVAL = 1.0
# A longer Crawl-delay skips the host rather than stalling a whole ingest run on it.
MAX_CRAWL_DELAY = 30.0
ROBOTS_TIMEOUT = 8.0

_ROBOTS: dict[str, RobotFileParser | None] = {}
_LAST: dict[str, float] = {}


class Response(Protocol):
    """The slice of ``polyfetch_scrape``'s response the kit reads."""

    status: int
    body: bytes
    backend: str


class RobotsDisallowedError(Exception):
    """robots.txt forbids the URL, or could not be read (assumed disallowed)."""


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _read_robots(origin: str, fetch: Callable[..., Response]) -> RobotFileParser | None:
    """Parse ``origin``'s robots.txt; ``None`` when it is unreachable (5xx / network error)."""
    rp = RobotFileParser()
    try:
        r = fetch(f"{origin}/robots.txt", timeout=ROBOTS_TIMEOUT)
    except Exception as exc:
        # polyfetch raises typed errors (AuthRequired, GoneError, ...) carrying `.status` for
        # terminal 4xx; those still mean "no robots.txt". Anything else is unreachable.
        status = getattr(exc, "status", None)
        if isinstance(status, int) and 400 <= status < 500:
            rp.parse([])
            return rp
        return None
    if r.status >= 500:
        return None
    body = r.body.decode("utf-8", errors="replace") if isinstance(r.body, bytes) else str(r.body)
    # A 4xx, or an HTML soft-404 served as 200, carries no rules.
    rp.parse([] if r.status >= 400 or body.lstrip().startswith("<") else body.splitlines())
    return rp


def _wait(origin: str, interval: float) -> None:
    last = _LAST.get(origin)
    if last is not None:
        remaining = interval - (time.monotonic() - last)
        if remaining > 0:
            time.sleep(remaining)
    _LAST[origin] = time.monotonic()


def polite_fetch(url: str, **kwargs: object) -> Response:
    """``polyfetch_scrape.fetch(url, **kwargs)`` after the robots.txt check and per-host spacing.

    Raises:
        RobotsDisallowedError: robots.txt forbids ``url`` or could not be read.
    """
    from polyfetch_scrape import fetch  # pyright: ignore[reportMissingImports]

    origin = _origin(url)
    if origin not in _ROBOTS:
        _ROBOTS[origin] = _read_robots(origin, fetch)
    rp = _ROBOTS[origin]
    if rp is None:
        raise RobotsDisallowedError(f"robots.txt unreachable for {origin}; skipped")
    if not rp.can_fetch("*", url):
        raise RobotsDisallowedError(f"robots.txt disallows {url}")
    delay = float(rp.crawl_delay("*") or 0)
    if delay > MAX_CRAWL_DELAY:
        raise RobotsDisallowedError(f"robots.txt Crawl-delay {delay:g}s for {origin} too long")
    _wait(origin, max(MIN_INTERVAL, delay))
    return fetch(url, **kwargs)
