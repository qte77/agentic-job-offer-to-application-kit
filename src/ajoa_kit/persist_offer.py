"""Persist a ``cc-workflow-tailor-offer.js`` result into a per-offer application pack.

The Workflow tool returns the tailored pack (it cannot write files); this turns that
returned JSON into on-disk markdown artifacts a human reviews before submitting. Run::

    python -m ajoa_kit.persist_offer <path-to-workflow-result.json> [--slug SLUG]

Writes ``results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md`` (plus a
``coverage-report.md`` when the pack carries ``must_haves``, a ``cv-ats-check.md`` when the CV
trips the parse-safety pass, #75, and a ``cv-stuffing-check.md`` when it trips the keyword-stuffing
pass, #272), and a ``meta.json`` recording the JD id so the local dashboard
can join the pack back to its shortlist row (#209). The results root comes from
``AppSettings`` (``AJOA_RESULTS_DIR`` / CWD), so an alternate workspace works.

No submission, no auto-apply: the prefill pack is a human-review artifact only — it lists
application fields for a person to fill and submit manually, never a script or link that
auto-submits (see ``research.md`` §Delivery for the safe/unsafe boundary, #8).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ajoa_kit.ats_check import parse_safety_warnings
from ajoa_kit.coverage import coverage_summary
from ajoa_kit.settings import AppSettings
from ajoa_kit.stuffing import stuffing_warnings

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
        # Title as YAML frontmatter (not a wrapping `# H1`) so each artifact keeps a single H1
        # from its own body — markdownlint strips frontmatter, so no MD025 "multiple H1" noise.
        rendered.append((filename, f'---\ntitle: "{heading}"\n---\n\n{value.strip()}\n'))
    return rendered


def write_pack(pack: dict, slug: str, results_dir: Path) -> Path:
    """Write the validated pack to ``results_dir/offers/<safe-slug>/``.

    Validation happens before any write, so an incomplete pack leaves the disk untouched.
    When the pack carries ``must_haves``, a ``coverage-report.md`` is also written — outside
    the all-or-nothing artifact set, so packs without it are unaffected. A ``cv-ats-check.md`` is
    written whenever the tailored CV trips the parse-safety check (#75), and a
    ``cv-stuffing-check.md`` whenever it trips the keyword-stuffing check (#272) — both non-blocking
    review aids, also outside the all-or-nothing set.

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
    # Optional 6th artifact — kept OUT of ARTIFACTS so render()'s all-or-nothing
    # validation never requires it (older packs carry no must_haves).
    if pack.get("must_haves"):
        body = coverage_summary(pack["must_haves"], pack.get("gap_report", ""))
        cov = f'---\ntitle: "Coverage report"\n---\n\n{body}'
        (offer_dir / "coverage-report.md").write_text(cov)
    # Auto parse-safety on the tailored CV (#75): surface ATS-hostile constructs for human review.
    # Non-blocking — a warning file appears only when there is something to fix; never raises.
    warnings = parse_safety_warnings(pack["cv"])
    if warnings:
        items = "\n".join(f"- {w}" for w in warnings)
        (offer_dir / "cv-ats-check.md").write_text(
            '---\ntitle: "CV ATS parse-safety"\n---\n\n'
            "Review before submitting — non-blocking warnings, not errors.\n\n"
            f"{items}\n"
        )
    # Auto keyword-stuffing check on the tailored CV (#272): surface dishonest keyword-density /
    # copy-paste / skills-wall constructs for human review. Same non-blocking, opt-out-free backstop
    # as cv-ats-check — a file appears only when there is something to trim; never raises.
    stuffing = stuffing_warnings(pack["cv"])
    if stuffing:
        items = "\n".join(f"- {w}" for w in stuffing)
        (offer_dir / "cv-stuffing-check.md").write_text(
            '---\ntitle: "CV keyword-stuffing check"\n---\n\n'
            "Review before submitting — non-blocking warnings, not errors.\n\n"
            f"{items}\n"
        )
    # Sidecar for the local dashboard join (#209): the dir is named by the (maybe custom) slug, so
    # record the JD id -> this offer so build_ui_shortlist can attach cv/cover-letter by id.
    jd_id = pack.get("offer_id") or pack.get("id")
    if jd_id:
        (offer_dir / "meta.json").write_text(json.dumps({"id": jd_id, "slug": safe_slug(slug)}))
    return offer_dir


def strip_frontmatter(md: str) -> str:
    r"""Drop the ``---\ntitle: "..."\n---`` block :func:`render` prepends, returning the body."""
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            return md[end + len("\n---\n") :].lstrip("\n")
    return md


# The artifacts the dashboard expand shows (cv, cover letter, prefill pack); filenames sourced from
# ARTIFACTS (single source). The prefill pack is the human-review field list — a local Copy target
# for manual paste, never auto-submitted (research.md §Delivery).
_JOIN_KEYS = {"cv", "cover_letter", "prefill_pack"}
_JOIN_DOCS = {key: filename for key, filename, _ in ARTIFACTS if key in _JOIN_KEYS}


def _load_offer_index(results_dir: Path) -> dict[str, Path]:
    """Map each offer's JD id to its dir, from ``results_dir/offers/*/meta.json`` (#209)."""
    index: dict[str, Path] = {}
    for meta_path in (results_dir / "offers").glob("*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(meta, dict) and meta.get("id"):
            index[str(meta["id"])] = meta_path.parent
    return index


def _read_offer_docs(offer_dir: Path) -> dict[str, str]:
    """Read + strip the ``offer_dir`` join docs (cv / cover_letter / prefill_pack bodies)."""
    docs: dict[str, str] = {}
    for key, filename in _JOIN_DOCS.items():
        doc = offer_dir / filename
        if doc.is_file():
            docs[key] = strip_frontmatter(doc.read_text())
    return docs


def attach_tailor_docs(rows: list[dict], results_dir: Path) -> list[dict]:
    """Attach each row's cv / cover_letter / prefill_pack from its offer pack, joined by id (#209).

    Uses :func:`_load_offer_index` (id -> offer dir) + :func:`_read_offer_docs`; rows without a
    tailored pack stay untouched.
    """
    index = _load_offer_index(results_dir)
    for row in rows:
        rid = str(row.get("id") or "")
        offer_dir = index.get(rid) if rid else None
        if offer_dir is not None:
            row.update(_read_offer_docs(offer_dir))
    return rows


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
