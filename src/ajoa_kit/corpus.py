"""Fold a fresh ingest pull into the running deduped corpus (#164).

Pure stdlib (no polyfetch, no network). The daily ingest keeps a corpus keyed by JD ``id`` so a
re-pull never loses history: each record carries ``first_seen`` (when it first appeared),
``last_seen`` (the most recent pull it was present in), and a ``content_hash`` of its JD content
(title + location + description). :func:`merge_corpus` is a four-state merge:

  - **new** — id absent from the prior corpus → ``first_seen = last_seen = today``.
  - **changed** — id present but ``content_hash`` differs → adopt the fresh content,
    ``last_seen = today``, ``first_seen`` preserved.
  - **unchanged** — id present, same content → only ``last_seen`` refreshes to ``today``.
  - **delisted** — a prior id absent from the fresh pull → kept as-is, ``last_seen`` frozen, so
    ``today - last_seen`` measures how long it has been gone.

``today`` is passed in (not read from the clock) so the merge is deterministic and testable.
"""

from __future__ import annotations

import hashlib

# JD content that defines a *material* change; tracking churn (url/posted_at) is deliberately
# excluded so a re-canonicalized URL alone does not flip a record to "changed".
_CONTENT_FIELDS = ("title", "location", "description")
_SEP = "\x1f"  # unit separator — unlikely in JD text, so fields can't collide across the boundary


def content_hash(rec: dict) -> str:
    """Return a stable hex digest of the JD content fields (title + location + description)."""
    payload = _SEP.join(str(rec.get(f, "")) for f in _CONTENT_FIELDS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def merge_corpus(prior: list[dict], fresh: list[dict], today: str) -> list[dict]:
    """Fold today's ``fresh`` ingest pull into the running ``prior`` corpus.

    Args:
        prior: The existing corpus (records carrying ``first_seen``/``last_seen``/``content_hash``);
            empty on the first run.
        fresh: Today's freshly-ingested JD records (``ingest.record()`` shape, no tracking fields).
        today: ISO date stamp (``YYYY-MM-DD``) for this pull.

    Returns:
        The merged corpus — every id ever seen (fresh + surviving delisted) — sorted by ``id`` so
        the on-disk artifact is deterministic across runs (stable cross-run diffs). "Delisted" is
        identified by ``last_seen``, not position, so ordering carries no meaning downstream.
    """
    prior_by_id = {r["id"]: r for r in prior}
    fresh_ids = {r["id"] for r in fresh}
    merged: list[dict] = []

    for rec in fresh:
        digest = content_hash(rec)
        old = prior_by_id.get(rec["id"])
        if old is None:  # new
            merged.append({**rec, "first_seen": today, "last_seen": today, "content_hash": digest})
        elif old.get("content_hash") != digest:  # changed — adopt fresh content, keep first_seen
            merged.append(
                {
                    **rec,
                    "first_seen": old.get("first_seen", today),
                    "last_seen": today,
                    "content_hash": digest,
                }
            )
        else:  # unchanged — only refresh last_seen
            merged.append({**old, "last_seen": today})

    # delisted — prior ids absent from today's pull: keep as-is, last_seen frozen.
    merged.extend(rec for rec in prior if rec["id"] not in fresh_ids)
    return sorted(merged, key=lambda r: r["id"])
