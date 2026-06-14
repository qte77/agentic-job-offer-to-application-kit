"""Persist a ``cc-workflow-tailor-offer.js`` result into a per-offer application pack.

The Workflow tool returns the tailored pack (it cannot write files); this turns that
returned JSON into on-disk markdown artifacts a human reviews before submitting. Run::

    python -m ajoa_kit.persist_offer <path-to-workflow-result.json> [--slug SLUG]

Writes ``results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md``. The
results root comes from ``AppSettings`` (``AJOA_RESULTS_DIR`` / CWD), so an alternate
workspace works.

No submission, no auto-apply: the prefill pack is a human-review artifact only — it lists
application fields for a person to fill and submit manually, never a script or link that
auto-submits (see ``research.md`` §Delivery for the safe/unsafe boundary, #8).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ajoa_kit.settings import AppSettings

# (pack key, output filename, rendered H1 heading) — the order files are written in.
ARTIFACTS: list[tuple[str, str, str]] = [
    ("match", "match.md", "Match assessment"),
    ("cv", "cv.md", "Tailored CV"),
    ("cover_letter", "cover-letter.md", "Cover letter"),
    ("gap_report", "gap-report.md", "Gap report"),
    ("prefill_pack", "prefill-pack.md", "Prefill pack (human review — do not auto-submit)"),
]

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def safe_slug(raw: str) -> str:
    """Reduce an arbitrary offer id to one confined path segment (no traversal).

    Lowercases, collapses every non-alphanumeric run to ``-``, and trims dashes — so
    separators, ``..`` and absolute paths cannot escape ``results/offers/``.

    Args:
        raw: Untrusted slug source (e.g. a JD id like ``ashby:acme-ai:101``).

    Returns:
        A safe single-segment slug.

    Raises:
        ValueError: If nothing slug-worthy remains after sanitizing.
    """
    slug = _NON_SLUG.sub("-", raw.lower()).strip("-")
    if not slug:
        raise ValueError(f"empty slug after sanitizing: {raw!r}")
    return slug


def render(pack: dict) -> list[tuple[str, str]]:
    """Validate the pack and render each artifact to ``(filename, markdown)``.

    Args:
        pack: The tailor result; must hold a non-empty string for every artifact key.

    Returns:
        One ``(filename, content)`` pair per artifact, in ``ARTIFACTS`` order.

    Raises:
        ValueError: If any artifact field is missing or not a non-empty string.
    """
    rendered: list[tuple[str, str]] = []
    for key, filename, heading in ARTIFACTS:
        value = pack.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"pack missing required artifact: {key}")
        rendered.append((filename, f"# {heading}\n\n{value.strip()}\n"))
    return rendered


def write_pack(pack: dict, slug: str, results_dir: Path) -> Path:
    """Write the validated pack to ``results_dir/offers/<safe-slug>/``.

    Validation happens before any write, so an incomplete pack leaves the disk untouched.

    Args:
        pack: The tailor result.
        slug: Untrusted offer slug (sanitized via :func:`safe_slug`).
        results_dir: The results root (from ``AppSettings``).

    Returns:
        The offer directory that was written.
    """
    files = render(pack)  # validate first — all-or-nothing
    offer_dir = results_dir / "offers" / safe_slug(slug)
    offer_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files:
        (offer_dir / filename).write_text(content)
    return offer_dir


def load_pack(src: Path) -> dict:
    """Parse the workflow output JSON, tolerating the ``result`` wrapper.

    Args:
        src: Path to the workflow-result JSON.

    Returns:
        The pack dict (unwrapped from ``result`` when present).
    """
    data = json.loads(src.read_text())
    if "match" not in data and isinstance(data.get("result"), dict):
        data = data["result"]
    return data


def main(src: Path | None = None, slug: str | None = None) -> None:
    """Write an offer pack to results/; reads args from argv when called directly.

    Args:
        src: Path to the workflow-result JSON (defaults to the first CLI arg).
        slug: Offer slug override (defaults to ``--slug`` or the pack's ``slug``/``id``).
    """
    if src is None:
        parser = argparse.ArgumentParser(prog="ajoa-kit persist-offer")
        parser.add_argument("file", metavar="FILE", help="Path to workflow-result.json.")
        parser.add_argument("--slug", default=None, help="Offer slug (default: pack slug/id).")
        ns = parser.parse_args()
        src = Path(ns.file)
        slug = ns.slug
    pack = load_pack(src)
    slug = slug or pack.get("slug") or pack.get("id") or pack.get("company")
    if not slug:
        raise ValueError("no slug: pass --slug or include slug/id/company in the pack")
    results = AppSettings().results_dir
    offer_dir = write_pack(pack, slug=slug, results_dir=results)
    print(f"wrote offer pack -> {offer_dir} ({len(ARTIFACTS)} artifacts)")


if __name__ == "__main__":
    main()
