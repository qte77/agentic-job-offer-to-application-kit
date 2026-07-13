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
        for item in must_haves:
            covered = "covered" if item.get("covered") else "gap"
            req = _cell(item.get("requirement"))
            evidence = _cell(item.get("evidence"))
            resources = _resources_cell(item.get("resources"))
            lines.append(f"| {req} | {covered} | {evidence} | {resources} |")
    gap = (gap_report or "").strip()
    if gap:
        lines += ["", "## Gap report", "", gap]
    return "\n".join(lines) + "\n"
