"""Split results/jobs-raw.json into results/batches/batch-NNN.json for the relevance workflow.

Pure stdlib (no polyfetch). Run::

    python -m ajoa_kit.chunk [batch_size]

The ``cc-workflow-relevance.js`` workflow fans out one agent per batch file; each agent
reads ~batch_size JDs and judges lane-fit in a single context. Re-run after re-ingesting.
"""

from __future__ import annotations

import json
import re
import sys
from typing import TYPE_CHECKING

from ajoa_kit.defaults import DESC_CAP
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_BATCH = 40

# Headings that open the substantive body of a JD, and those that close it. These are NOT
# line-anchored: 99.9% of the corpus arrives as a single unbroken line (HTML is already stripped at
# ingest), so headings run straight into the following sentence — "About the role As our AI
# Operations Lead, you will...". Matching has to work mid-string, which makes a stray prose hit
# ("gather requirements from stakeholders") the real risk. The search windows below, not the
# patterns, are what bound that damage.
# Bare "the role" / "your role" / "your mission" are deliberately absent: they read as ordinary
# prose ("...your role, keeping our systems running...") and measured on the corpus they cut whole
# JDs down to a fragment. Only phrases that are heading-shaped on their own are listed.
_BODY_START = re.compile(
    r"\b(?:what you'?ll (?:do|be doing)|who you are|what we'?re looking for|"
    r"about the (?:role|job|position)|responsibilities|requirements|qualifications)\b",
    re.IGNORECASE,
)
_BODY_END = re.compile(
    r"\b(?:benefits|perks|what we offer|compensation|equal (?:employment )?opportunity|"
    r"eeo\b|our commitment to (?:diversity|inclusion))\b",
    re.IGNORECASE,
)

# An opening marker is only believed inside the preamble zone (p90 of pre-marker preamble is ~2,010
# chars); past that we assume the body has already started and keep the text whole. A closing marker
# is only believed in the last stretch, where wrap-up boilerplate actually lives.
PREAMBLE_WINDOW = 2500
TAIL_FRACTION = 0.6

# A marker can still land in prose. When the resulting slice keeps less than this share of the
# posting, treat the match as spurious and keep the text whole — losing the wrapper is worth it,
# losing the role is not.
MIN_KEEP_RATIO = 0.25


def _scoped(desc: str) -> str:
    """Return the substantive slice of ``desc`` — the role body, without the wrapper.

    Most of the corpus opens with an "About us" blurb and many close with EEO/benefits boilerplate.
    Neither carries lane signal, and with a median JD of 4,732 chars against a 4,000-char
    :data:`DESC_CAP`, the preamble is crowding out the requirements the screen exists to read.

    Conservative by construction: markers are only believed where those sections actually occur
    (see :data:`PREAMBLE_WINDOW` / :data:`TAIL_FRACTION`), no opening marker keeps the text whole,
    and a slice that strips to nothing falls back to the original. This narrows what the relevance
    screen reads; it never drops a JD and never changes a score.
    """
    head = _BODY_START.search(desc, 0, PREAMBLE_WINDOW)
    start = head.start() if head else 0
    tail = _BODY_END.search(desc, max(start + 1, int(len(desc) * TAIL_FRACTION)))
    end = tail.start() if tail else len(desc)
    scoped = desc[start:end].strip()
    if len(scoped) < len(desc) * MIN_KEEP_RATIO:
        return desc
    return scoped


def _capped(rec: dict) -> dict:
    """Return ``rec`` scoped to the role body and trimmed to :data:`DESC_CAP` for relevance.

    The cap lives here rather than at ingest (#347): it exists to bound the relevance screen's
    tokens, while ``results/jobs-raw.json`` keeps the whole posting so the stage-3 tailor pass —
    which reads that file directly — is grounded in the complete JD. Scoping runs first and applies
    at any length; the cap stays the hard backstop behind it.
    """
    desc = rec.get("description")
    if not isinstance(desc, str):
        return rec
    scoped = _scoped(desc)[:DESC_CAP]
    if scoped == desc:
        return rec
    return {**rec, "description": scoped}


def _new_offers(results: Path) -> list[dict]:
    """Return the corpus records new or changed in the latest pull — the delta (#226/#235).

    The most recent pull date is ``max(last_seen)``; a record is in the delta when its
    ``last_changed`` equals it — newly seen this pull or content-changed (#235). Pre-#235 corpora
    without ``last_changed`` fall back to ``first_seen`` (new-only, the #226 behaviour).
    """
    corpus_path = results / "corpus.json"
    if not corpus_path.is_file():
        msg = "no results/corpus.json — run `ajoa-kit ingest --merge` before `chunk --new`."
        raise FileNotFoundError(msg)
    corpus = json.loads(corpus_path.read_text())
    latest = max(rec["last_seen"] for rec in corpus)
    return [rec for rec in corpus if rec.get("last_changed", rec["first_seen"]) == latest]


def main(batch: int = DEFAULT_BATCH, *, new: bool = False) -> None:
    """Split the ingested corpus into fixed-size batch files plus a manifest.

    Args:
        batch: Number of JDs per batch file.  When called from the CLI the
            ``--batch-size`` argument is passed here; when invoked directly as
            ``python -m ajoa_kit.chunk [N]`` the module-level ``if __name__``
            block reads ``sys.argv[1]`` and passes it in.
        new: When true, batch only the latest-pull delta from ``results/corpus.json``
            (offers whose ``first_seen`` equals the most recent ``last_seen``) for an
            incremental re-screen (#226), instead of the full ``results/jobs-raw.json``.
    """
    results = AppSettings().results_dir
    jobs = _new_offers(results) if new else json.loads((results / "jobs-raw.json").read_text())
    out = results / "batches"
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("batch-*.json"):  # clear previous run
        stale.unlink()

    n = 0
    for i in range(0, len(jobs), batch):
        (out / f"batch-{i // batch:03d}.json").write_text(
            json.dumps([_capped(rec) for rec in jobs[i : i + batch]], ensure_ascii=False, indent=2),
        )
        n += 1

    (out / "manifest.json").write_text(
        json.dumps({"total_jobs": len(jobs), "batch_size": batch, "batch_count": n}, indent=2),
    )
    print(f"wrote {n} batches of <= {batch} JDs -> {out}/  (manifest.json)")


if __name__ == "__main__":
    main(batch=int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BATCH)
