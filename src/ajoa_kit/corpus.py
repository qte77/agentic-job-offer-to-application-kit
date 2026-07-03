"""Fold a fresh ingest pull into the running deduped corpus (#164).

Pure stdlib (no polyfetch, no network). The daily ingest keeps a corpus keyed by JD ``id`` so a
re-pull never loses history: each record carries ``first_seen`` (when it first appeared),
``last_seen`` (the most recent pull it was present in), and a ``content_hash`` of its JD content
(title + location + description); ``last_changed`` marks the pull it was last new or changed (#235).
:func:`merge_corpus` is a four-state merge:

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
            merged.append(
                {
                    **rec,
                    "first_seen": today,
                    "last_seen": today,
                    "last_changed": today,
                    "content_hash": digest,
                }
            )
        elif old.get("content_hash") != digest:  # changed — adopt fresh content, keep first_seen
            merged.append(
                {
                    **rec,
                    "first_seen": old.get("first_seen", today),
                    "last_seen": today,
                    "last_changed": today,
                    "content_hash": digest,
                }
            )
        else:  # unchanged — only refresh last_seen
            merged.append({**old, "last_seen": today})

    # delisted — prior ids absent from today's pull: keep as-is, last_seen frozen.
    merged.extend(rec for rec in prior if rec["id"] not in fresh_ids)
    return sorted(merged, key=lambda r: r["id"])


# How many new offers to enumerate in the rendered digest before truncating — the first incremental
# run stamps the whole backfill as "new" (thousands), which would otherwise dump an unreadable file.
_NEW_OFFERS_CAP = 50


def summarize_changes(prior: list[dict], merged: list[dict], today: str) -> dict:
    """Derive the daily "what changed today" digest from a :func:`merge_corpus` result (#175).

    Classifies every record in ``merged`` into the four merge states using the same signals
    ``merge_corpus`` stamps — ``last_seen`` / ``first_seen`` / ``content_hash`` — comparing against
    ``prior`` (the pre-merge corpus) to tell *changed* from *unchanged*:

      - **delisted** — ``last_seen != today`` (absent from today's pull, frozen).
      - **new** — ``first_seen == today``.
      - **changed** — seen today, ``content_hash`` differs from the prior record.
      - **unchanged** — seen today, same content.

    Args:
        prior: The corpus *before* today's merge (empty on the first run).
        merged: The :func:`merge_corpus` output for today's pull.
        today: ISO date stamp (``YYYY-MM-DD``) for this pull.

    Returns:
        ``{date, new, changed, unchanged, delisted, active, new_offers}`` where ``active`` is the
        count seen today (``new + changed + unchanged``) and ``new_offers`` lists ``{company, title,
        url}`` for each new record. Pure — no I/O; the caller persists/renders it.
    """
    prior_hash = {r["id"]: r.get("content_hash") for r in prior}
    counts = {"new": 0, "changed": 0, "unchanged": 0, "delisted": 0}
    new_offers: list[dict] = []
    for rec in merged:
        if rec.get("last_seen") != today:
            counts["delisted"] += 1
        elif rec.get("first_seen") == today:
            counts["new"] += 1
            new_offers.append({k: rec.get(k, "") for k in ("company", "title", "url")})
        elif rec.get("content_hash") != prior_hash.get(rec["id"]):
            counts["changed"] += 1
        else:
            counts["unchanged"] += 1
    return {
        "date": today,
        **counts,
        "active": counts["new"] + counts["changed"] + counts["unchanged"],
        "new_offers": new_offers,
    }


def render_daily_summary(summary: dict) -> str:
    """Render :func:`summarize_changes` output as a human-readable markdown digest (#175).

    Counts block + the list of new offers (``company`` — ``title`` (``url``)); the list is truncated
    at :data:`_NEW_OFFERS_CAP` with an "…and N more" line so a backfill run stays readable.

    **Local/artifact-only by construction:** the digest names companies/titles/URLs (actual offer
    data, not aggregate), so the caller writes it under the git-ignored ``results/`` and never to a
    branch — the daily CI run publishes only the aggregate keyword trends.
    """
    lines = [
        f"# Daily offer digest — {summary['date']}",
        "",
        f"- **New:** {summary['new']}",
        f"- **Changed:** {summary['changed']}",
        f"- **Unchanged:** {summary['unchanged']}",
        f"- **Delisted:** {summary['delisted']}",
        f"- **Active (seen today):** {summary['active']}",
        "",
        f"## New offers ({summary['new']})",
        "",
    ]
    offers = summary["new_offers"]
    if not offers:
        lines.append("No new offers today.")
        return "\n".join(lines) + "\n"
    for o in offers[:_NEW_OFFERS_CAP]:
        company = o.get("company") or "—"
        title = o.get("title") or "—"
        url = o.get("url") or ""
        lines.append(f"- **{company}** — {title}" + (f" ({url})" if url else ""))
    extra = len(offers) - _NEW_OFFERS_CAP
    if extra > 0:
        lines.append(f"- …and {extra} more")
    return "\n".join(lines) + "\n"
