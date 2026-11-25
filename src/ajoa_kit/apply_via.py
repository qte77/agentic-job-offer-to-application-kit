"""Enforce the prefill pack's "Apply via" route and its links in code (#526).

The tailor agent writes the prefill pack from third-party JD text, and the candidate clicks what it
says, so prompt rules alone are not enough: an injected JD could steer the agent into a link that
carries planted values or local text. The check does not trust any label the agent writes. It scans
the WHOLE pack, default-deny:

1. Every line is normalised first (NFKC, then Unicode format characters such as zero-width spaces
   and the BOM are deleted), so lookalike or invisible variants cannot hide a link.
2. The exactly allowed items are removed from the line, matched as whole strings: the job record's
   url (as stored, or in canonical form from :func:`ajoa_kit.normalize.canonical_url`, which keeps
   ``gh_jid``), the exact host and path of a link in the JD text (no query, no fragment), an email
   address from the JD, and the candidate's own links from the local evidence library.
3. If anything link-like or address-like remains (``://``, ``//``, ``www.``, ``@``, ``<`` or ``>``,
   a markdown link or reference, a backslash, an HTML entity, a non-web scheme, or a ``host.tld``
   followed by ``/``, ``?``, ``#`` or ``:``), the line is replaced by a fixed note.

The code then writes the route line itself: ``**Apply via:** <route>``, where the route is the
first allowed item on the first line that starts with "apply via" (if that line passed), else the
record's url, else ``[NEEDS HUMAN INPUT]`` (fail closed). A JD route on another host than the
record's url is kept (the prompt contract: the posting names the route) but flagged.

Replacing, not raising: a failed persist leaves the offer "missing" for ``pack-plan``, which would
re-tailor an injected JD in a loop (ADR-0005). Warnings are fixed text and never repeat what was
removed. Known limit: re-checking a pack after its record has left ``jobs-raw.json`` fails closed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ajoa_kit.normalize import canonical_url

if TYPE_CHECKING:
    from pathlib import Path

NEEDS_HUMAN = "[NEEDS HUMAN INPUT]"
LABEL = "**Apply via:**"
REMOVED = "[removed: a link or address that is not from the job record or the posting]"
WARNING = (
    "a line of the prefill pack held a link or address that is neither the job record's url, a "
    "link (exact host and path, no query, no fragment) or email from the posting, nor one of your "
    "own links, so it was replaced; the route line names the record's url, or "
    f"{NEEDS_HUMAN} when there is none. This can be a false positive (a name such as Node.js "
    "reads like a link); check the posting before applying"
)
OFF_HOST = (
    "the Apply via route was taken from the posting text and is on another host than the job "
    "record's url; open the live posting and confirm the route before applying"
)

# A route line: one that starts (after markdown or list marks) with "apply via", however written.
_LABEL_RE = re.compile(r"^[\W_]*apply[\W_]*via", re.IGNORECASE)
_URL = re.compile(r"https?://[^\s<>\"'()\[\]]+", re.IGNORECASE)
_EMAIL = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.IGNORECASE)
_TRAIL = ".,;:!?)]}'\""
_RESIDUE = re.compile(
    r"://|//|www\.|@|<|>|\]\(|\]\[|^\s*\[[^\]]*\]:|\\|&#|&[a-z]+;"
    r"|\b(?:javascript|data|mailto|file|vbscript|tel|sms|ftp)\s*:"
    r"|\w\.\w{2,}[/?#:]",
    re.IGNORECASE,
)


def normalise(line: str) -> str:
    """NFKC, then delete Unicode format characters (zero-width, BOM, bidi controls)."""
    nfkc = unicodedata.normalize("NFKC", line)
    return "".join(c for c in nfkc if unicodedata.category(c) != "Cf")


def _host_path(url: str) -> tuple[str, str] | None:
    """``(scheme, host[:port] + path)`` of a clean http(s) url with no userinfo, else ``None``."""
    try:
        s = urlsplit(url)
    except ValueError:
        return None
    if s.scheme.lower() not in ("http", "https") or not s.netloc or "@" in s.netloc:
        return None
    return s.scheme.lower(), s.netloc.lower() + s.path


def _host(item: str) -> str:
    """The host an allowed item points at (an email's domain for an email)."""
    if "@" in item and "://" not in item:
        return item.rsplit("@", 1)[1].lower()
    hp = _host_path(item if "://" in item else f"https://{item}")
    return hp[1].split("/", 1)[0] if hp else ""


class Allowed:
    """The exact strings the record, its JD and the candidate's own links allow in the pack."""

    def __init__(self, record: dict | None, own_links: tuple[str, ...] = ()) -> None:
        """Collect the allowed strings from ``record`` (url, JD links, JD emails) and own links."""
        rec = record or {}
        raw = str(rec.get("url") or "")
        canon = canonical_url(raw, str(rec.get("ats") or ""))
        self.record_urls = [u for u in dict.fromkeys((canon, raw)) if _host_path(u)]
        self.record_host = _host(self.record_urls[0]) if self.record_urls else ""
        jd = normalise(str(rec.get("description") or ""))
        routes: list[str] = []
        for u in _URL.findall(jd):
            hp = _host_path(u.rstrip(_TRAIL))
            if hp:
                routes += [f"{hp[0]}://{hp[1]}", hp[1]]
        self.routes = list(dict.fromkeys(routes))
        self.emails = list(dict.fromkeys(e.lower() for e in _EMAIL.findall(jd)))
        self.own = [u for u in own_links if _host_path(u)]

    def items(self) -> list[str]:
        """Every allowed string, longest first, so a longer item is removed before its prefix."""
        every = {*self.record_urls, *self.routes, *self.emails, *self.own}
        return sorted(every, key=lambda s: (-len(s), s))


def _pattern(item: str) -> re.Pattern[str]:
    # Reason: a whole string between delimiters, so nothing can be glued on either side. After the
    # item only whitespace, the end, or closing punctuation that is itself followed by whitespace
    # or the end may come: an autolink would carry any other glued text (";x=1", ",x", "!x").
    return re.compile(
        rf"(?<![\w.%+/@:\-]){re.escape(item)}(?=$|\s|[.,;:!?)\]]+(?:\s|$))", re.IGNORECASE
    )


def scan(line: str, allowed: Allowed) -> tuple[bool, list[str]]:
    """``(clean, allowed items found, in order)`` for one normalised line."""
    found: list[tuple[int, str]] = []
    rest = line
    for item in allowed.items():
        pat = _pattern(item)
        found += [(m.start(), item) for m in pat.finditer(rest)]
        rest = pat.sub(lambda m: " " * len(m.group(0)), rest)
    return _RESIDUE.search(rest) is None, [item for _, item in sorted(found)]


def own_links(library: Path) -> tuple[str, ...]:
    """The candidate's own http(s) links from the local evidence library (trusted, owner-written).

    The tailor prompt lets portfolio links from the evidence library stay in the pack; they come
    from this local file, never from the JD or the pack. A missing or unreadable file yields none.
    """
    try:
        text = library.read_text()
    except (OSError, ValueError):
        return ()
    return tuple(dict.fromkeys(u.rstrip(_TRAIL) for u in _URL.findall(text)))


def _route(items: list[str], allowed: Allowed) -> str | None:
    """The first item usable as the route: a record url, a JD route or a JD email."""
    usable = {*allowed.record_urls, *allowed.routes, *allowed.emails}
    return next((i for i in items if i in usable), None)


class _Pass:
    """One pass over the pack's lines: replaced lines, the route candidate, the route line slot."""

    def __init__(self, allowed: Allowed) -> None:
        self.allowed = allowed
        self.out: list[str] = []
        self.replaced = 0
        self.route: str | None = None
        self.label_at: int | None = None

    def add(self, line: str) -> None:
        norm = normalise(line)
        clean, items = scan(norm, self.allowed)
        if _LABEL_RE.match(norm) is not None:
            self._label(clean, items)
            return
        if not clean:
            self.replaced += 1
        self.out.append(line if clean else REMOVED)

    def _label(self, clean: bool, items: list[str]) -> None:
        if not clean:
            self.replaced += 1
        if self.label_at is None:  # the first route line is the slot the code writes into
            self.label_at = len(self.out)
            self.route = _route(items, self.allowed) if clean else None
            self.out.append("")
        # Reason: any later route line is dropped; the code writes exactly one


def check_apply_via(
    text: str, record: dict | None, own_links: tuple[str, ...] = ()
) -> tuple[str, list[str]]:
    """Check every line of a prefill pack and write its route line in code.

    Args:
        text: The prefill pack markdown, as the tailor agent wrote it.
        record: The pack's job record from ``jobs-raw.json`` (``None`` when unknown).
        own_links: The candidate's own links, from the local evidence library (trusted).

    Returns:
        The checked text and its warnings: one per replaced line, plus one for an off-host route.
    """
    allowed = Allowed(record, own_links)
    run = _Pass(allowed)
    for line in text.split("\n"):
        run.add(line)
    fallback = allowed.record_urls[0] if allowed.record_urls else NEEDS_HUMAN
    route_line = f"{LABEL} {run.route or fallback}"
    lines = run.out
    if run.label_at is None:
        lines = [route_line, "", *lines]
    else:
        lines[run.label_at] = route_line
    warnings = [WARNING] * run.replaced
    if run.route and allowed.record_host and _host(run.route) != allowed.record_host:
        warnings.append(OFF_HOST)
    return "\n".join(lines), warnings
