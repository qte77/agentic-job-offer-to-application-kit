"""Enforce the prefill pack's "Apply via" line in code (#526).

The tailor agent writes that line from third-party JD text, and the candidate clicks it, so a
prompt rule alone is not enough: an injected JD could steer the agent into a link that carries
planted values or local text. Every line bearing the label is checked here, default-deny:

- a link must be http or https, with no userinfo, and either be exactly the job record's url (as
  stored, or in its canonical form from :func:`ajoa_kit.normalize.canonical_url`, which keeps
  ``gh_jid``) or be exactly the host (with port) and path of a link in the JD text, with no query
  and no fragment;
- an email must be a bare address that appears as an address in the JD text;
- any other token that looks like a link (a scheme, ``//host``, a markdown link target, or a
  ``host.tld/path`` route) must pass the link rule; plain words pass.

A line that fails is replaced by ``**Apply via:** <record url>``, or ``[NEEDS HUMAN INPUT]`` when
the record is unknown or has no http(s) url (fail closed). Replacing, not raising: a failed
persist leaves the offer "missing" for ``pack-plan``, which would re-tailor an injected JD in a
loop (ADR-0005). The warning never repeats the rejected text.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ajoa_kit.normalize import canonical_url

NEEDS_HUMAN = "[NEEDS HUMAN INPUT]"
LABEL = "**Apply via:**"
WARNING = (
    'an "Apply via" line named a link or address that is neither the job record\'s url nor a '
    "link (host and path only) or email from the JD, so it was replaced with the record's url, or "
    f"{NEEDS_HUMAN} when the record has none; check the route on the live posting before applying"
)

_LABEL_RE = re.compile(r"apply\s+via\s*:", re.IGNORECASE)
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_HOSTISH = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(:\d+)?(/|$)", re.IGNORECASE)
_EMAIL_CORE = r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+"
_EMAIL = re.compile(rf"^{_EMAIL_CORE}$", re.IGNORECASE)
_JD_EMAIL = re.compile(_EMAIL_CORE, re.IGNORECASE)
_JD_URL = re.compile(r"https?://[^\s<>\"'()\[\]]+", re.IGNORECASE)
_STRIP = "<>()[]*_`\"',.;!"


def _tokens(rest: str) -> list[str]:
    """Split the text after the label into candidate tokens; a markdown link yields both parts."""
    parts: list[str] = []
    rest = _MD_LINK.sub(lambda m: f" {m.group(1)} {m.group(2)} ", rest)
    for raw in rest.split():
        tok = raw.strip(_STRIP)
        if tok:
            parts.append(tok)
    return parts


def _host_path(url: str) -> tuple[str, str] | None:
    """``(host[:port], path)`` of a clean http(s) url with no userinfo, else ``None``."""
    try:
        s = urlsplit(url)
    except ValueError:
        return None
    if s.scheme.lower() not in ("http", "https") or not s.netloc or "@" in s.netloc:
        return None
    return s.netloc.lower(), s.path


class _Allowed:
    """What the record and its JD allow on the line: exact record urls, JD host+paths, JD emails."""

    def __init__(self, record: dict | None) -> None:
        rec = record or {}
        raw = str(rec.get("url") or "")
        canon = canonical_url(raw, str(rec.get("ats") or ""))
        self.record_urls = {u for u in (raw, canon) if _host_path(u)}
        self.replacement = canon if _host_path(canon) else NEEDS_HUMAN
        text = str(rec.get("description") or "")
        self.routes = {hp for u in _JD_URL.findall(text) if (hp := _host_path(u.rstrip(_STRIP)))}
        self.emails = {e.lower() for e in _JD_EMAIL.findall(text)}

    def link(self, tok: str) -> bool:
        url = tok if _SCHEME.match(tok) else f"https://{tok.removeprefix('//')}"
        hp = _host_path(url)
        if hp is None:
            return False
        if url in self.record_urls:
            return True
        s = urlsplit(url)
        return not s.query and not s.fragment and hp in self.routes

    def token(self, tok: str) -> bool:
        if _EMAIL.match(tok):
            return tok.lower() in self.emails
        if _SCHEME.match(tok) or tok.startswith("//") or _HOSTISH.match(tok):
            return self.link(tok)
        return True  # a plain word


def _line_ok(line: str, allowed: _Allowed) -> bool:
    m = _LABEL_RE.search(line)
    rest = line[m.end() :] if m else line
    return all(allowed.token(t) for t in _tokens(rest))


def check_apply_via(text: str, record: dict | None) -> tuple[str, list[str]]:
    """Check every "Apply via" line of a prefill pack against its job record.

    Args:
        text: The prefill pack markdown, as the tailor agent wrote it.
        record: The pack's job record from ``jobs-raw.json`` (``None`` when unknown).

    Returns:
        The text with each failing line replaced, and one warning per replaced line.
    """
    allowed = _Allowed(record)
    replacement = f"{LABEL} {allowed.replacement}"
    out, warnings = [], []
    for line in text.split("\n"):
        if _LABEL_RE.search(line) and not _line_ok(line, allowed):
            out.append(replacement)
            warnings.append(WARNING)
        else:
            out.append(line)
    return "\n".join(out), warnings
