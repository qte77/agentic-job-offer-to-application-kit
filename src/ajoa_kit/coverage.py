"""Render a JD must-have coverage report for a tailored offer pack.

The Stage-3 tailor pass (``cc-workflow-tailor-offer.js``) returns an optional
``must_haves`` list — one ``{requirement, covered, evidence}`` object per JD must-have.
This turns that (untrusted, possibly messy) list into a markdown table a human reviews
alongside the rest of the pack. Pure and defensive: it never raises on missing keys,
``None`` values, or table-breaking characters.
"""

from __future__ import annotations

_PLACEHOLDER = "—"


def _cell(value: object) -> str:
    """Make ``value`` safe for a single markdown table cell.

    Collapses all whitespace (so a newline can't split the row) and escapes ``|`` (so a
    value can't open a new column); ``None``/blank becomes a visible placeholder.

    Args:
        value: Arbitrary cell source from the (untrusted) must-have entry.

    Returns:
        A one-line, pipe-safe cell string.
    """
    if value is None:
        return _PLACEHOLDER
    text = " ".join(str(value).split()).replace("|", "\\|")
    return text or _PLACEHOLDER


def _resources_cell(resources: object) -> str:
    """Render an uncovered must-have's upskilling pointers into one pipe-safe cell.

    Each pointer is sanitized like any other cell and joined with ``; ``. A missing/``None``
    value, a non-list, or a list with no usable entries becomes the placeholder — so covered
    must-haves (which carry no ``resources``) render blank (#274).

    Args:
        resources: The entry's ``resources`` value (expected ``list[str]``, but untrusted).

    Returns:
        A one-line, pipe-safe cell listing the pointers, or the placeholder.
    """
    if not isinstance(resources, list):
        return _PLACEHOLDER
    cells = [_cell(r) for r in resources if r is not None and str(r).strip()]
    return "; ".join(cells) if cells else _PLACEHOLDER


def _row(item: dict) -> str:
    """Render one must-have entry as a pipe-safe markdown table row.

    Columns: ``| requirement | covered/gap | evidence | resources |``. Upskilling pointers are a gap
    aid — a covered must-have renders none, even if the match pass mistakenly emitted some (#274).
    """
    is_covered = bool(item.get("covered"))
    covered = "covered" if is_covered else "gap"
    req = _cell(item.get("requirement"))
    evidence = _cell(item.get("evidence"))
    resources = _PLACEHOLDER if is_covered else _resources_cell(item.get("resources"))
    return f"| {req} | {covered} | {evidence} | {resources} |"


def coverage_summary(must_haves: list[dict], gap_report: str) -> str:
    """Render the must-have coverage table plus the gap report as markdown.

    Args:
        must_haves: One ``{requirement, covered, evidence, resources?}`` dict per JD must-have;
            keys may be missing or ``None`` and values are sanitized. ``resources`` is an
            optional ``list[str]`` of upskilling pointers for an uncovered must-have (#274).
        gap_report: The pack's gap report, appended under its own heading when present.

    Returns:
        A markdown body (no top-level H1 — the caller adds it). Always emits exactly one
        table row per ``must_haves`` entry; an empty list yields a placeholder line.
    """
    lines = ["## Must-have coverage", ""]
    if not must_haves:
        lines.append("_No must-have requirements identified._")
    else:
        lines += [
            "| Must-have | covered/gap | Evidence | Resources |",
            "| --- | --- | --- | --- |",
        ]
        lines += [_row(item) for item in must_haves]
    gap = (gap_report or "").strip()
    if gap:
        lines += ["", "## Gap report", "", gap]
    return "\n".join(lines) + "\n"


_GAP_ONLY_FIELDS = ("resources", "mitigation", "suggestion")


def honesty_warnings(must_haves: list[dict]) -> list[str]:
    """Flag must-have entries where ``covered`` looks overstated (arc-011 Slice C).

    Two deterministic tells, both agent self-inconsistency rather than semantic judgement:
    a ``covered: true`` entry citing no real ``evidence`` (a coverage claim with nothing behind
    it), and a ``covered: true`` entry carrying a gap-closing field (``resources``/``mitigation``/
    ``suggestion``, all Slice A additions meant for an uncovered requirement only). The reverse —
    an uncovered entry missing ``mitigation``/``suggestion`` — is never flagged: those fields are
    optional by design (Slice A), so flagging their absence would fire on every legacy pack.

    Args:
        must_haves: One ``{requirement, covered, evidence, ...}`` dict per JD must-have; keys may
            be missing or ``None`` — never raises.

    Returns:
        One warning per flagged entry, or an empty list.
    """
    warnings: list[str] = []
    for item in must_haves or []:
        if not isinstance(item, dict) or not item.get("covered"):
            continue
        requirement = _cell(item.get("requirement"))
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            warnings.append(f"'{requirement}' is marked covered but cites no evidence")
        gap_fields = [f for f in _GAP_ONLY_FIELDS if item.get(f)]
        if gap_fields:
            warnings.append(
                f"'{requirement}' is marked covered but carries gap-only field(s) "
                f"({', '.join(gap_fields)}) — inconsistent with being covered"
            )
    return warnings
