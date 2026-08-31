"""Persist a ``cc-workflow-tailor-offer.js`` result into a per-offer application pack.

The Workflow tool returns the tailored pack (it cannot write files); this turns that
returned JSON into on-disk markdown artifacts a human reviews before submitting. Run::

    python -m ajoa_kit.persist_offer <path-to-workflow-result.json> [--slug SLUG]

Writes ``results/offers/<slug>/{match,cv,cover-letter,gap-report,prefill-pack}.md`` (plus a
``coverage-report.md`` when the pack carries ``must_haves``, a ``cv-ats-check.md`` when the CV
trips the parse-safety pass, #75, a ``cv-stuffing-check.md`` when it trips the keyword-stuffing
pass, #272, and a ``jd-truncation-check.md`` when the source JD sat at the ingest description
cap, #347), and a ``meta.json`` recording the JD id so the local dashboard
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
from typing import TYPE_CHECKING

from ajoa_kit.ats_check import parse_safety_warnings
from ajoa_kit.coverage import coverage_summary
from ajoa_kit.defaults import DESC_CAP
from ajoa_kit.settings import AppSettings
from ajoa_kit.stuffing import stuffing_warnings

if TYPE_CHECKING:
    from collections.abc import Callable

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
        # Tailor agents sometimes embed the title block inside the value itself (#351) — strip
        # any LEADING frontmatter block(s) so the canonical wrap below is the only one; a `---`
        # rule mid-body is content and stays.
        body = value.strip()
        stripped = strip_frontmatter(body)
        while stripped != body:
            body = stripped.strip()
            stripped = strip_frontmatter(body)
        # Title as YAML frontmatter (not a wrapping `# H1`) so each artifact keeps a single H1
        # from its own body — markdownlint strips frontmatter, so no MD025 "multiple H1" noise.
        rendered.append((filename, f'---\ntitle: "{heading}"\n---\n\n{body}\n'))
    return rendered


def _find_jd_record(jd_id: str, records: object) -> dict | None:
    """Find the ``jobs-raw.json`` record matching ``jd_id``, or ``None`` if absent/malformed."""
    for rec in records if isinstance(records, list) else []:
        if isinstance(rec, dict) and rec.get("id") == jd_id:
            return rec
    return None


def jd_truncation_warning(jd_id: str | None, results_dir: Path, cap: int = DESC_CAP) -> str | None:
    """Detect a source JD that sits at the legacy ingest description cap (#347).

    The tailor pass grounds on ``results/jobs-raw.json``. Ingest used to truncate ``description``
    at :data:`ajoa_kit.defaults.DESC_CAP` chars, so a pack built from such a record silently lost
    whatever requirements sat past the cap, and the Match agents notice it only sometimes. The cap
    has since moved to :func:`ajoa_kit.chunk.main`, so freshly pulled records are complete and this
    check goes quiet on its own — it still matters for rows not yet re-pulled (delisted postings
    can never be re-pulled, so theirs stay truncated permanently).

    The length test is ``== cap``, not ``>= cap``. While ingest truncated, the two were equivalent
    because nothing could exceed the cap; once full text is stored, ``>=`` fires on every long
    posting — ~80% of the corpus — flagging exactly the packs that are now complete. Only the exact
    cap length is evidence of the legacy truncation.

    Deterministic check: a warning when the recorded description length is exactly the cap,
    ``None`` when the JD is complete or indeterminable (missing corpus / unknown id — never
    raises, never claims either way without evidence).

    Args:
        jd_id: The pack's JD id (``offer_id``/``id``); ``None``/empty skips the check.
        results_dir: The results root holding ``jobs-raw.json``.
        cap: The ingest description cap to compare against.

    Returns:
        A human-facing warning string, or ``None``.
    """
    if not jd_id:
        return None
    try:
        records = json.loads((results_dir / "jobs-raw.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    rec = _find_jd_record(jd_id, records)
    if rec is None:
        return None
    desc = rec.get("description")
    if isinstance(desc, str) and len(desc) == cap:
        return (
            f"the ingested JD description sits at the {cap}-char ingest cap, so this "
            "pack was tailored from a truncated JD — open the live posting and check "
            "the requirements past the cut before submitting"
        )
    return None


def lane_angle_warning(lane: str | None, results_dir: Path) -> str | None:
    """Detect an evidence library that cannot ground the pack's lane (#348).

    ``cc-workflow-evidence-library.js`` derives a ``{lane}Angle`` field per lane in its ``lanes``
    arg, so a library built with a stale or partial lane set silently lacks angles that
    ``config/lanes.json`` defines. The 2026-06-29 library carried 5 of 7 — no ``mlAngle`` or
    ``fdeAngle`` — and the tailor agents fell back to a neighbouring lane's angle, only sometimes
    saying so. Deterministic check instead, in the same never-guess shape as
    :func:`jd_truncation_warning`: ``None`` when the angle is present or the situation is
    indeterminable (no lane, missing/unreadable library), a warning only on positive evidence.

    Args:
        lane: The pack's lane key (e.g. ``"ml"``); ``None``/empty skips the check.
        results_dir: The results root holding ``evidence-library.json``.

    Returns:
        A human-facing warning string, or ``None``.
    """
    if not lane:
        return None
    try:
        library = json.loads((results_dir / "evidence-library.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(library, dict):
        return None
    field = f"{lane}Angle"
    if isinstance(library.get(field), str) and library[field].strip():
        return None
    return (
        f"the evidence library has no `{field}`, so this pack could not be grounded in the "
        f"{lane} lane's positioning and the tailor pass fell back to another lane — rebuild the "
        "library with the full lane set before relying on this pack"
    )


def _cv_ats_check(pack: dict, results_dir: Path) -> list[str]:
    return parse_safety_warnings(pack["cv"])


def _cv_stuffing_check(pack: dict, results_dir: Path) -> list[str]:
    return stuffing_warnings(pack["cv"])


def _jd_truncation_check(pack: dict, results_dir: Path) -> list[str]:
    jd_id = pack.get("offer_id") or pack.get("id")
    warning = jd_truncation_warning(jd_id, results_dir)
    return [warning] if warning else []


def _lane_grounding_check(pack: dict, results_dir: Path) -> list[str]:
    warning = lane_angle_warning(pack.get("lane"), results_dir)
    return [warning] if warning else []


# (sidecar title, filename, check) — each check takes (pack, results_dir) and returns warnings;
# an empty list writes nothing. Registry so a new deterministic check is one more entry, not a
# new inline block (arc-011 Slice C) — see cv_grounding_check/honesty_check below for the
# same-shaped additions.
CHECKS: list[tuple[str, str, Callable[[dict, Path], list[str]]]] = [
    ("CV ATS parse-safety", "cv-ats-check.md", _cv_ats_check),
    ("CV keyword-stuffing check", "cv-stuffing-check.md", _cv_stuffing_check),
    ("Source JD truncation check", "jd-truncation-check.md", _jd_truncation_check),
    ("Lane grounding check", "lane-grounding-check.md", _lane_grounding_check),
]


def _emit_check(offer_dir: Path, title: str, filename: str, warnings: list[str]) -> None:
    """Write one sidecar review-aid file, only when its check flagged something."""
    if not warnings:
        return
    items = "\n".join(f"- {w}" for w in warnings)
    (offer_dir / filename).write_text(
        f'---\ntitle: "{title}"\n---\n\n'
        "Review before submitting — non-blocking warnings, not errors.\n\n"
        f"{items}\n"
    )


def write_pack(pack: dict, slug: str, results_dir: Path) -> Path:
    """Write the validated pack to ``results_dir/offers/<safe-slug>/``.

    Validation happens before any write, so an incomplete pack leaves the disk untouched.
    When the pack carries ``must_haves``, a ``coverage-report.md`` is also written — outside
    the all-or-nothing artifact set, so packs without it are unaffected. A ``cv-ats-check.md`` is
    written whenever the tailored CV trips the parse-safety check (#75), a
    ``cv-stuffing-check.md`` whenever it trips the keyword-stuffing check (#272), a
    ``jd-truncation-check.md`` whenever the source JD sat at the legacy ingest description cap
    (#347), and a ``lane-grounding-check.md`` whenever the evidence library lacks the pack's
    ``{lane}Angle`` (#348) — all non-blocking review aids, also outside the all-or-nothing set.

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
    # Deterministic review-aid sidecars (#75, #272, #347, #348; arc-011 Slice C) — each is
    # non-blocking, opt-out-free, and appears only when it flags something; never raises.
    for title, filename, check in CHECKS:
        _emit_check(offer_dir, title, filename, check(pack, results_dir))
    jd_id = pack.get("offer_id") or pack.get("id")
    # Sidecar for the local dashboard join (#209): the dir is named by the (maybe custom) slug, so
    # record the JD id -> this offer so build_ui_shortlist can attach cv/cover-letter by id.
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
