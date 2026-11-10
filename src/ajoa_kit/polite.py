"""Polite fetching: obey robots.txt and space requests per host (#454, ADR-0002).

Every network call goes through :func:`polite_fetch`. Per origin, robots.txt is read once and
checked for ``User-agent: *`` (polyfetch rotates browser User-Agents, so no named group applies).
Rules are matched by :class:`RobotsRules` per RFC 9309 (``*`` wildcards, ``$`` end anchor, longest
match wins, ``Allow`` wins a tie), not by ``urllib.robotparser``: before Python 3.14 that ignored
wildcards and applied the first matching rule, so it allowed paths a site disallows.
Policy per RFC 9309: a 4xx robots.txt means no rules; a 5xx or network error means assume
disallowed, so the URL is skipped with :class:`RobotsDisallowed` rather than fetched. Requests to
the same host are spaced by max(:data:`MIN_INTERVAL`, the host's ``Crawl-delay``). A skipped source
surfaces in ingest's ``sources ok / failed`` summary like any other fetch failure.

``polyfetch_scrape`` is imported lazily so this module stays importable offline.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

MIN_INTERVAL = 1.0
# A longer Crawl-delay skips the host rather than stalling a whole ingest run on it.
MAX_CRAWL_DELAY = 30.0
ROBOTS_TIMEOUT = 8.0

_ROBOTS: dict[str, RobotsRules | None] = {}
_LAST: dict[str, float] = {}


class Response(Protocol):
    """The slice of ``polyfetch_scrape``'s response the kit reads."""

    status: int
    body: bytes
    backend: str


class RobotsDisallowedError(Exception):
    """robots.txt forbids the URL, or could not be read (assumed disallowed)."""


def _fields(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """``(lowercased key, value)`` per robots.txt line, comments stripped, blank lines skipped."""
    for line in lines:
        key, sep, value = line.split("#", 1)[0].partition(":")
        if sep:
            yield key.strip().lower(), value.strip()


def _star_fields(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """The non-user-agent fields of every group whose user-agents include ``*`` (RFC 9309 2.2.1).

    Consecutive ``User-agent`` lines form one group; the first rule line after them closes it.
    """
    agents: list[str] = []
    in_rules = False
    for key, value in _fields(lines):
        if key == "user-agent":
            agents = [value] if in_rules else [*agents, value]
            in_rules = False
        else:
            in_rules = True
            if "*" in agents:
                yield key, value


def _matches(pattern: str, target: str) -> bool:
    """RFC 9309 2.2.3: ``*`` matches any characters; a trailing ``$`` anchors the end."""
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.match(body + ("$" if anchored else ""), target) is not None


class RobotsRules(BaseModel):
    """The ``User-agent: *`` rules of one robots.txt: ``(allow, pattern)`` pairs + Crawl-delay."""

    rules: list[tuple[bool, str]] = []
    crawl_delay: float | None = None

    @classmethod
    def parse(cls, lines: Iterable[str]) -> RobotsRules:
        """Collect the rules and Crawl-delay that apply to ``User-agent: *``."""
        out = cls()
        for key, value in _star_fields(lines):
            if key in ("allow", "disallow") and value:
                out.rules.append((key == "allow", value))
            elif key == "crawl-delay":
                out.crawl_delay = _float_or_none(value)
        return out

    def allows(self, url: str) -> bool:
        """Whether ``url`` may be fetched: the longest matching rule decides, ``Allow`` on ties."""
        parts = urlsplit(url)
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        hits = [(len(p), allow) for allow, p in self.rules if _matches(p, target)]
        return target == "/robots.txt" or not hits or max(hits)[1]


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _read_robots(origin: str, fetch: Callable[..., Response]) -> RobotsRules | None:
    """Parse ``origin``'s robots.txt; ``None`` when it is unreachable (5xx / network error)."""
    try:
        r = fetch(f"{origin}/robots.txt", timeout=ROBOTS_TIMEOUT)
    except Exception as exc:
        # polyfetch raises typed errors (AuthRequired, GoneError, ...) carrying `.status` for
        # terminal 4xx; those still mean "no robots.txt". Anything else is unreachable.
        status = getattr(exc, "status", None)
        if isinstance(status, int) and 400 <= status < 500:
            return RobotsRules()
        return None
    if r.status >= 500:
        return None
    body = r.body.decode("utf-8", errors="replace") if isinstance(r.body, bytes) else str(r.body)
    # A 4xx, or an HTML soft-404 served as 200, carries no rules.
    no_rules = r.status >= 400 or body.lstrip().startswith("<")
    return RobotsRules() if no_rules else RobotsRules.parse(body.splitlines())


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
    if not rp.allows(url):
        raise RobotsDisallowedError(f"robots.txt disallows {url}")
    delay = rp.crawl_delay or 0.0
    if delay > MAX_CRAWL_DELAY:
        raise RobotsDisallowedError(f"robots.txt Crawl-delay {delay:g}s for {origin} too long")
    _wait(origin, max(MIN_INTERVAL, delay))
    return fetch(url, **kwargs)
