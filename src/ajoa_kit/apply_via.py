"""Enforce the prefill pack's "Apply via" route and its links in code (#526).

The tailor agent writes the prefill pack from third-party JD text, and the candidate clicks what it
says, so prompt rules alone are not enough: an injected JD could steer the agent into a link that
carries planted values or local text. The check does not trust any label the agent writes. It scans
the WHOLE pack, default-deny:

1. Every line is normalised (NFKC, then Unicode format characters such as zero-width spaces, tag
   characters, soft hyphens and the BOM are deleted), and the normalised line is what is written,
   so nothing the check did not see can reach the file or a link.
2. The exactly allowed items are blanked out, matched as whole strings with only a space, a tab,
   the end of the line, or a run of closing punctuation a renderer trims after them: the job
   record's url (as stored, or in canonical form from :func:`ajoa_kit.normalize.canonical_url`,
   which keeps ``gh_jid``), the exact host and path of a link in the JD text (no query, no
   fragment), an email address from the JD, and the candidate's own links from the local evidence
   library. Scheme and host match case-insensitively; the path matches exactly.
3. If anything that can become a link or carry hidden data remains, the line is replaced by a fixed
   note: ``://``, ``//``, ``www.``, any address shape (``x@y.z``, ``@[``), a tag-like ``<``, a
   markdown link or reference (``](``, ``][``, any ``]:``, so a ``[NEEDS HUMAN INPUT]:`` line too),
   a backslash, an HTML entity, ``http(s):``, a script or non-web scheme (``javascript:``,
   ``data:``, ``mailto:``, ``file:``, ``vbscript:``, ``tel:``, ``sms:``, ``ftp:``, ``vscode:``) not
   followed by a space, or a control character. Any other bare ``scheme:`` renders as text, since a
   scheme only becomes a link through ``](``, ``<...>`` or ``]:``, which all count. On a route line
   a bare ``host.tld`` followed by ``/``, ``?``, ``#`` or ``:`` also counts (elsewhere it is not
   auto-linked, so it is left as text).

The code then writes the route line itself: ``**Apply via:** <route>``, where the route is the
first allowed item on the first line that starts with "apply via" (if that line passed), else the
record's url, else ``[NEEDS HUMAN INPUT]`` (fail closed). A route that is not the record's url is
kept (the prompt contract: the posting names the route) but flagged.

Replacing, not raising: a failed persist leaves the offer "missing" for ``pack-plan``, which would
re-tailor an injected JD in a loop (ADR-0005). Warnings are fixed text and never repeat what was
removed. Known limits: re-checking a pack after its record has left ``jobs-raw.json`` fails closed;
the candidate's own links are kept only when the local evidence library holds them.
"""

from __future__ import annotations

import json
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
LINK_REMOVED = "[removed: a link or address that is not allowed in this document]"
WARNING = (
    "a line of the prefill pack held a link or address that is neither the job record's url, a "
    "link (exact host and path, no query, no fragment) or email from the posting, nor one of your "
    "own links from the evidence library, so it was replaced; the route line names the record's "
    f"url, or {NEEDS_HUMAN} when there is none. Your own links (GitHub, LinkedIn, website) are "
    "kept only when the evidence library holds them. This can be a false positive; check the "
    "posting before applying"
)
OFF_HOST = (
    "the Apply via route was taken from the posting text, not the job record's url (another host, "
    "or the record has none); open the live posting and confirm the route before applying"
)

# A route line: one that starts (after markdown or list marks) with the word pair "apply via".
_LABEL_RE = re.compile(r"^[\W_]*apply[\W_]*via\b", re.IGNORECASE)
_URL = re.compile(r"https?://[^\s<>\"'()\[\]]+", re.IGNORECASE)
_EMAIL = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.IGNORECASE)
_TRAIL = ".,;:!?)]}'\""
_BEFORE = r"(?<![\w.%+/@:\-])"
# Reason: only what marked trims from an autolink may follow; "]" is not trimmed, so it is not here
_AFTER = r"(?=$|[ \t]|[.,;:!?)]+(?:[ \t]|$))"
_RESIDUE = re.compile(
    "|".join(
        (
            r"://",
            r"//",
            r"www\.",
            r"[^\s@]@[^\s@]*\.[^\s@]|@\[",
            r"<[a-z/!?]",
            r"\]\(",
            r"\]\[",
            r"\]\s*:",
            r"\\",
            r"&#",
            r"&[a-z]+;",
            r"\bhttps?\s*:",
            # Reason: ":**" then a space or the end closes a bold label ("and data:**"), no link
            r"\b(?:javascript|data|mailto|file|vbscript|tel|sms|ftp|vscode):(?!\s|\*\*(?:\s|$))",
            r"[\x00-\x08\x0b-\x1f\x7f-\x9f]",
        )
    ),
    re.IGNORECASE,
)
_ROUTE_RESIDUE = re.compile(r"\w\.\w{2,}[/?#:]")


def normalise(line: str) -> str:
    """NFKC, then delete Unicode format characters (zero-width, tag, soft hyphen, BOM, bidi)."""
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


def _split(item: str) -> tuple[str, str]:
    """``(case-insensitive head, exact tail)``: scheme and host, then the path and query."""
    if "@" in item and "://" not in item:
        return item, ""
    start = item.find("://") + 3 if "://" in item else 0
    cut = item.find("/", start)
    return (item, "") if cut == -1 else (item[:cut], item[cut:])


_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def _item_re(item: str) -> str:
    # Reason: ASCII-only case folding, so a Unicode lookalike (dotless i, ...) never matches a host
    head, tail = _split(item)
    return f"(?ai:{re.escape(head)}){re.escape(tail)}"


def _same(item: str, text: str) -> bool:
    head, tail = _split(item)
    if len(text) != len(item) or text[len(head) :] != tail:
        return False
    return text[: len(head)].translate(_ASCII_LOWER) == head.translate(_ASCII_LOWER)


class Allowed:
    """The exact strings the record, its JD and the candidate's own links allow in the pack."""

    def __init__(self, record: dict | None, own: tuple[str, ...] = ()) -> None:
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
        self.own = [u for u in own if _host_path(u if "://" in u else f"https://{u}")]
        # Reason: one alternation compiled once (a JD can hold thousands of links), longest first
        self.items = sorted(
            {*self.record_urls, *self.routes, *self.emails, *self.own}, key=lambda s: (-len(s), s)
        )
        alts = "|".join(_item_re(i) for i in self.items)
        self.regex = re.compile(f"{_BEFORE}(?:{alts}){_AFTER}") if self.items else None

    def item_for(self, text: str) -> str | None:
        """The allowed item a match spells (scheme and host may differ in ASCII case), or None."""
        return next((i for i in self.items if _same(i, text)), None)


def scan(line: str, allowed: Allowed, route_line: bool = False) -> tuple[bool, list[str]]:
    """``(clean, allowed items found, in order)`` for one normalised line."""
    if allowed.regex is None:
        rest, found = line, []
    else:
        hits = [allowed.item_for(m.group(0)) for m in allowed.regex.finditer(line)]
        found = [h for h in hits if h is not None]
        if len(found) != len(hits):  # Reason: a match no item spells is never trusted, nor raises
            return False, []
        rest = allowed.regex.sub(lambda m: " " * len(m.group(0)), line)
    dirty = _RESIDUE.search(rest) is not None
    if route_line:
        dirty = dirty or _ROUTE_RESIDUE.search(rest) is not None
    return not dirty, found


def _strings(node: object) -> list[str]:
    """Every string inside a parsed JSON value."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return []


def own_links(library: Path) -> tuple[str, ...]:
    """The candidate's own http(s) links from the local evidence library (trusted, owner-written).

    The tailor prompt lets portfolio links from the evidence library stay in the pack; they come
    from this local file, never from the JD or the pack. Each link is allowed with its scheme and
    without it. A missing or unreadable file yields none.
    """
    try:
        data = json.loads(library.read_text())
    except (OSError, ValueError):
        return ()
    links: list[str] = []
    for text in _strings(data):
        for u in _URL.findall(normalise(text)):
            hp = _host_path(u.rstrip(_TRAIL))
            if hp:
                links += [f"{hp[0]}://{hp[1]}", hp[1]]
    return tuple(dict.fromkeys(links))


def check_links(text: str, allowed: Allowed) -> tuple[str, int]:
    """Check every line of another pack artifact (#530): the same scan, with no route line.

    Each line is normalised and kept when :func:`scan` finds it clean, else replaced by
    :data:`LINK_REMOVED`. The caller picks ``allowed``: a CV or cover letter gets only the
    candidate's own links, the match and gap report also the record and its JD.

    Returns:
        The checked text and the number of replaced lines.
    """
    out: list[str] = []
    replaced = 0
    for line in text.replace("\r\n", "\n").split("\n"):
        norm = normalise(line)
        clean = scan(norm, allowed)[0]
        replaced += not clean
        out.append(norm if clean else LINK_REMOVED)
    return "\n".join(out), replaced


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
        if _LABEL_RE.match(norm) is not None:
            self._label(*scan(norm, self.allowed, route_line=True))
            return
        clean, _ = scan(norm, self.allowed)
        if not clean:
            self.replaced += 1
        self.out.append(norm if clean else REMOVED)

    def _label(self, clean: bool, items: list[str]) -> None:
        if self.label_at is None:  # the first route line is the slot the code writes into
            self.label_at = len(self.out)
            self.route = _route(items, self.allowed) if clean else None
            self.out.append("")
            if not clean:
                self.replaced += 1
            return
        self.replaced += 1  # a later route line is dropped: the code writes exactly one


def check_apply_via(
    text: str, record: dict | None, own: tuple[str, ...] = ()
) -> tuple[str, list[str]]:
    """Check every line of a prefill pack and write its route line in code.

    Args:
        text: The prefill pack markdown, as the tailor agent wrote it.
        record: The pack's job record from ``jobs-raw.json`` (``None`` when unknown).
        own: The candidate's own links, from the local evidence library (trusted).

    Returns:
        The checked text and its warnings: one per replaced line, plus one for a route that is not
        the record's url.
    """
    allowed = Allowed(record, own)
    run = _Pass(allowed)
    for line in text.replace("\r\n", "\n").split("\n"):
        run.add(line)
    fallback = allowed.record_urls[0] if allowed.record_urls else NEEDS_HUMAN
    route_line = f"{LABEL} {run.route or fallback}"
    lines = run.out
    if run.label_at is None:
        lines = [route_line, "", *lines]
    else:
        lines[run.label_at] = route_line
    warnings = [WARNING] * run.replaced
    if (
        run.route
        and run.route not in allowed.record_urls
        and _host(run.route) != allowed.record_host
    ):
        warnings.append(OFF_HOST)
    return "\n".join(lines), warnings
