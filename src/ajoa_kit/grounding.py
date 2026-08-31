"""Deterministic CV-grounding check against the evidence library (arc-011 Slice C).

Semantic claim verification ("is this sentence actually supported?") needs an LLM — but a
*distinctive* number is mechanically checkable: if it appears in the tailored CV and nowhere in
the evidence library's own text, it cannot be verified from the source data. A sibling of
``ats_check``/``stuffing`` — pure, no I/O, heuristic, non-blocking review aid.

Bare 1-3 digit integers ("3-tier", "24 repos") are too noisy to check and are skipped even though
it costs recall — a number NOT flagged here is not proof it's grounded, only that this check does
not cover it (never-guess, same contract as ``persist_offer.lane_angle_warning``).

Two more exclusions, found by calibrating against the real corpus (2026-08-31): a bare year
(1900-2099, no other marker) is a date, not a claim ("since 2019"); a number immediately preceded
by ``-``/``#`` is an id, not a claim ("ADR-0000", "PR-402"). Both cost recall the same
never-guess way — a real metric that happens to look like a year or sit after a hyphen slips
through unchecked, which is the safe direction to be wrong in.
"""

from __future__ import annotations

import re

# A number token: either a properly comma-grouped figure (1-3 digits, then one or more ",DDD"
# groups — so "19," in "React 19, TypeScript" never swallows the list-separator comma) or a plain
# digit run, each optionally decimal / %-or-x-suffixed. No trailing \b: % and x are non-word
# characters, so a boundary assertion right after them never matches.
_NUMBER_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?[xX]?|\d+(?:\.\d+)?%?[xX]?")
_ID_PREFIX = frozenset("-#")
_YEAR_LOW, _YEAR_HIGH = 1900, 2099


def _is_distinctive(token: str, preceded_by: str = "") -> bool:
    """A number worth checking: has a decimal, %, x-suffix, comma grouping, or >=4 digits.

    Excludes an id (``preceded_by`` is ``-``/``#``) and a bare year (exactly 4 digits, no other
    marker, in 1900-2099) regardless of digit count.
    """
    if preceded_by in _ID_PREFIX:
        return False
    if "." in token or "%" in token or "," in token:
        return True
    if token[-1] in "xX" and token[:-1].isdigit():
        return True
    digits = re.sub(r"\D", "", token)
    if len(digits) == 4 and _YEAR_LOW <= int(digits) <= _YEAR_HIGH:
        return False
    return len(digits) >= 4


def _normalize_number(token: str) -> str:
    """Strip the %/x suffix and comma grouping, leaving the bare digit(.digit) sequence."""
    return token.rstrip("xX%").replace(",", "")


def _distinctive_numbers(text: str) -> set[str]:
    """Normalized distinctive number tokens found anywhere in ``text``."""
    out: set[str] = set()
    for m in _NUMBER_TOKEN.finditer(text):
        preceded_by = text[m.start() - 1] if m.start() > 0 else ""
        if _is_distinctive(m.group(), preceded_by):
            out.add(_normalize_number(m.group()))
    return out


def _string_leaves(value: object) -> list[str]:
    """Recursively collect every string leaf in a JSON-like structure.

    A superset of the evidence library's known fields (``headline``, ``positioningSummary``,
    ``skillClusters``, ``masterCvBullets``, ``perProject``, every ``<lane>Angle``) — reaching
    every string regardless of nesting keeps this correct across schema drift without needing a
    lane parameter; over-inclusion is the safe direction for a grounding check.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _string_leaves(v)]
    if isinstance(value, list):
        return [s for v in value for s in _string_leaves(v)]
    return []


def grounding_warnings(cv_md: str, evidence_library: dict) -> list[str]:
    """Flag CV numbers that don't appear anywhere in the evidence library.

    Args:
        cv_md: The tailored CV as markdown.
        evidence_library: The parsed ``evidence-library.json`` (or any JSON-like dict).

    Returns:
        One warning per unverifiable distinctive number in the CV (deduplicated), or an empty
        list when the CV/library is empty, malformed, or every distinctive number is grounded.
    """
    if not cv_md or not isinstance(evidence_library, dict) or not evidence_library:
        return []  # an empty/malformed library is indeterminable, not evidence of ungrounding
    grounded = _distinctive_numbers(" ".join(_string_leaves(evidence_library)))
    warnings: list[str] = []
    seen: set[str] = set()
    for match in _NUMBER_TOKEN.finditer(cv_md):
        token = match.group()
        preceded_by = cv_md[match.start() - 1] if match.start() > 0 else ""
        if not _is_distinctive(token, preceded_by):
            continue
        norm = _normalize_number(token)
        if norm in grounded or norm in seen:
            continue
        seen.add(norm)
        warnings.append(
            f"CV cites '{token}' — this number does not appear anywhere in the evidence "
            "library; verify it's grounded before submitting"
        )
    return warnings
