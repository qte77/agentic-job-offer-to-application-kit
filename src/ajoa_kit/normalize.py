"""Record normalization + the coarse keyword pre-filter (#249 slice C).

Pure text/URL/record logic shared by the source adapters and the orchestrator: the normalized JD
``record`` shape, HTML-to-text flattening, tracking-param URL canonicalization, and the
word-boundary keyword patterns (compiled from :mod:`ajoa_kit.defaults`; ``config/keywords.json``
overrides at run time via :func:`ajoa_kit.ingest.load_keywords`). No network, no file I/O.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ajoa_kit.defaults import (
    DESC_CAP,
    FILTER_ATS_BY_DEPARTMENT,
    FILTER_RSS_BY_TITLE,
    INTEREST,
    TITLE_ROLES,
)

if TYPE_CHECKING:
    from typing import Any

# --- helpers --------------------------------------------------------------------------
# Quote-aware so a '>' inside a quoted attribute value doesn't end the tag early.
_TAG = re.compile(r"<(?:\"[^\"]*\"|'[^']*'|[^'\">])*>")
_WS = re.compile(r"\s+")
_TRACKING = {"gclid", "fbclid", "mc_cid", "mc_eid", "igshid", "ref_src"}

# Token boundaries for keyword matching. A tech token continues across \w/+/# always, and across
# . or - only mid-token (flanked by word chars) — so "c++"/".net"/"node.js"/"ci-cd" match whole and
# "c" never leaks into "c++", while a plain word before sentence punctuation ("Go.") still matches.
# BEHIND is two stacked lookbehinds because re requires each lookbehind to be fixed-width.
_BOUNDARY_AHEAD = r"(?![\w+#])(?![.\-]\w)"
_BOUNDARY_BEHIND = r"(?<![\w+#])(?<!\w[.\-])"


def build_patterns(
    interest: list[str], title_roles: list[str]
) -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Compile case-insensitive, token-boundary match patterns for the two keyword sets.

    Tech terms with punctuation (``c++``, ``.net``, ``node.js``, ``ci-cd``) match as whole tokens;
    a short term never leaks into a larger token (``c`` not in ``c++``); plain words still match
    before ordinary sentence punctuation.
    """

    def _compile(terms: list[str]) -> re.Pattern[str]:
        body = "|".join(re.escape(t) for t in terms)
        return re.compile(rf"{_BOUNDARY_BEHIND}({body}){_BOUNDARY_AHEAD}", re.I)

    return _compile(interest), _compile(title_roles)


# Module-default compiled patterns (the in-code fallback when no keywords.json is supplied).
_INTEREST, _TITLE_ROLES = build_patterns(INTEREST, TITLE_ROLES)


def is_interesting(text: str | None, pattern: re.Pattern[str] = _INTEREST) -> bool:
    """Return True if ``text`` contains an interest term on a word boundary."""
    return bool(text and pattern.search(text))


def is_role_title(text: str | None, pattern: re.Pattern[str] = _TITLE_ROLES) -> bool:
    """Return True if ``text`` contains a core role noun on a word boundary."""
    return bool(text and pattern.search(text))


def keep(
    rec: dict[str, Any],
    pat_interest: re.Pattern[str] = _INTEREST,
    pat_title: re.Pattern[str] = _TITLE_ROLES,
) -> bool:
    """Coarse pre-filter. RSS keeps on title; ATS keeps on department OR title.

    The title fallback stops a whole board being dropped when its ``department`` field is
    empty or coarse, while still cutting non-eng roles (a "Sales" dept + "Account
    Executive" title miss both).
    """
    if rec["ats"] == "rss":
        return not FILTER_RSS_BY_TITLE or is_interesting(rec["title"], pat_interest)
    if not FILTER_ATS_BY_DEPARTMENT:
        return True
    return is_interesting(rec["department"], pat_interest) or is_role_title(rec["title"], pat_title)


def html_to_text(s: str | None) -> str:
    """Unescape entities, strip tags, collapse whitespace, and cap length."""
    if not s:
        return ""
    s = html.unescape(s)
    s = _TAG.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s[:DESC_CAP]


def canonical_url(url: str) -> str:
    """Drop tracking query params (utm_*, gclid, ...) for clean, stable URLs/ids."""
    if not url:
        return url
    s = urlsplit(url)
    if not s.query:
        return url
    kept = [
        (k, v)
        for k, v in parse_qsl(s.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING
    ]
    return urlunsplit((s.scheme, s.netloc, s.path, urlencode(kept), s.fragment))


def record(**kw: object) -> dict[str, Any]:
    """Build a normalized JD record; every adapter emits exactly this shape."""
    base = {
        "id": "",
        "source": "",
        "ats": "",
        "company": "",
        "company_slug": "",
        "lane_hint": "",
        "department": "",
        "fetched_backend": "",
        "title": "",
        "location": "",
        "remote": None,
        "url": "",
        "posted_at": "",
        "last_modified": "",
        "description": "",
    }
    base.update(kw)
    base["url"] = canonical_url(base["url"])
    return base
