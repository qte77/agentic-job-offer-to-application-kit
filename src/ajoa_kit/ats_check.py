"""Deterministic résumé parse-safety check for a tailored CV (issue #9).

ATS parsers choke on multi-column tables, embedded graphics, raw HTML, and hidden text, and
penalise résumés with no recognisable section structure (research.md §ATS). This flags those
constructs in a markdown CV — a cheap gate the human runs over the tailored pack::

    ajoa-kit ats-check results/offers/<slug>/cv.md

Exits non-zero when any warning is raised. Parse-safety only — JD must-have *coverage* is a
semantic check left to the tailor workflow, not this deterministic pass.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# A GFM table delimiter row (e.g. ``|---|:--:|``): the giveaway that a table is present. The
# leading lookahead requires a pipe on the line, so a bare ``---`` thematic break / Setext
# underline (which the tailor CV agent emits as a section separator) is not mistaken for a table.
_TABLE = re.compile(r"(?m)^(?=[^\n]*\|)[ \t]*\|?[ \t:|-]*-{3,}[ \t:|-]*$")
# A real HTML tag, incl. self-closing — but NOT a markdown autolink like ``<https://x>``.
_HTML_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^>]*)?/?>")
_IMAGE = re.compile(r"!\[[^\]]*\]\(")
_COMMENT = re.compile(r"<!--")  # hidden text / keyword stuffing vector
_HEADINGS = re.compile(
    r"(?i)\b(summary|profile|experience|education|skills|projects|"
    r"work history|employment)\b"
)


def parse_safety_warnings(cv_md: str) -> list[str]:
    """Return parse-safety warnings for a markdown CV (empty list = ATS-safe).

    Args:
        cv_md: The tailored CV as markdown.

    Returns:
        Human-readable warnings, one per detected ATS-hostile construct.
    """
    warnings: list[str] = []
    if _TABLE.search(cv_md):
        warnings.append("table detected — ATS parsers mangle multi-column layout")
    if _HTML_TAG.search(cv_md):
        warnings.append("raw HTML detected — use plain markdown, not tags")
    if _IMAGE.search(cv_md):
        warnings.append("image detected — ATS cannot read graphics/photos")
    if _COMMENT.search(cv_md):
        warnings.append("HTML comment detected — hidden text is penalised")
    if not _HEADINGS.search(cv_md):
        warnings.append("no recognizable section headings (e.g. Experience, Skills)")
    return warnings


def main(src: Path | None = None) -> None:
    """Check a CV file for parse-safety; exit non-zero if any warning is raised.

    Args:
        src: Path to the CV markdown (defaults to the first CLI arg).
    """
    if src is None:
        parser = argparse.ArgumentParser(prog="ajoa-kit ats-check")
        parser.add_argument("file", metavar="FILE", help="Path to a CV markdown file.")
        src = Path(parser.parse_args().file)
    warnings = parse_safety_warnings(src.read_text())
    if not warnings:
        print(f"ATS parse-safety: OK ({src})")
        return
    print(f"ATS parse-safety: {len(warnings)} issue(s) in {src}")
    for w in warnings:
        print(f"  - {w}")
    sys.exit(1)


if __name__ == "__main__":
    main()
