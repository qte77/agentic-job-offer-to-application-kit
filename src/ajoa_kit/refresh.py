"""Reconcile a lane's shortlist with current reality — flag (or remove) dead offers (#214).

After a relevance run, ``results/<lane>/shortlist.json`` is a snapshot; offers get filled/closed and
go stale. ``refresh`` re-checks every entry two ways and marks the dead ones:

  - **corpus-delisted** — the #164 ``results/corpus.json`` no longer saw it in the latest pull
    (``last_seen`` frozen below the newest pull date), and
  - **URL re-probe** — a direct read-only GET returns a definitive non-2xx (catches offers whose
    source we stopped tracking, which the corpus can't mark).

Dead entries are flagged ``stale`` by default (kept as an audit trail; the dashboard hides them) or
dropped with ``--delete``. An inconclusive probe (network error / timeout) never flags an entry,
so a flaky network can't expire a live shortlist. Run::

    ajoa-kit refresh [--lane <name>] [--delete] [--dry-run]

The decision core (:func:`is_delisted`, :func:`classify`, :func:`mark`) takes the probe and
``today`` as arguments, so it is deterministic and importable without the network — polyfetch is
reached lazily via :func:`ajoa_kit.slug_probe.fetch_status` only when :func:`main` runs.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from ajoa_kit.ingest import load_lanes
from ajoa_kit.persist_scored import load_shortlist, write_lane
from ajoa_kit.settings import AppSettings
from ajoa_kit.slug_probe import fetch_status

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from ajoa_kit.models import ScoredItem


def is_delisted(corpus_rec: dict | None, latest_pull: str) -> bool:
    """True if the corpus has this entry but it missed the latest pull (``last_seen`` frozen).

    Absent from the corpus entirely (``corpus_rec is None`` — e.g. a source we stopped tracking)
    yields False here: the URL re-probe, not the corpus, decides those.
    """
    return corpus_rec is not None and corpus_rec.get("last_seen") != latest_pull


def classify(corpus_delisted: bool, status: int | None) -> bool:
    """Return True if an entry is stale: corpus-delisted or a definitive non-2xx re-probe.

    ``status is None`` (inconclusive — non-http(s), network error, timeout) and any 2xx are *not*
    stale, so a flaky network never expires a live entry.
    """
    return corpus_delisted or (status is not None and not 200 <= status < 300)


def mark(
    items: list[ScoredItem],
    corpus_by_id: dict[str, dict],
    latest_pull: str,
    probe: Callable[[str], int | None],
    today: str,
) -> tuple[list[ScoredItem], int]:
    """Annotate each shortlist entry with ``stale`` + ``last_checked``; return (items, stale count).

    Skips the URL re-probe for entries the corpus already marks delisted (they're stale regardless),
    so live entries and untracked-source entries are the only ones that hit the network.
    """
    n_stale = 0
    for it in items:
        delisted = is_delisted(corpus_by_id.get(it.id), latest_pull)
        status = None if delisted else probe(it.url)
        stale = classify(delisted, status)
        it.stale = stale
        it.last_checked = today
        if stale:
            n_stale += 1
    return items, n_stale


def refresh_lane(
    lane: str,
    results_dir: Path,
    corpus_by_id: dict[str, dict],
    latest_pull: str,
    probe: Callable[[str], int | None],
    today: str,
    *,
    delete: bool,
    dry_run: bool,
) -> dict:
    """Mark (or, with ``delete``, drop) one lane's stale shortlist entries; return a report."""
    path = results_dir / lane / "shortlist.json"
    if not path.is_file():
        return {"lane": lane, "live": 0, "stale": 0, "missing": True}
    items = load_shortlist(path)
    items, n_stale = mark(items, corpus_by_id, latest_pull, probe, today)
    out = [it for it in items if not it.stale] if delete else items
    if not dry_run:
        write_lane(lane, out, results_dir)
    return {"lane": lane, "live": len(items) - n_stale, "stale": n_stale, "missing": False}


def _lane_dirs(results_dir: Path) -> Iterable[str]:
    """Yield the lane names that actually have a ``shortlist.json`` under ``results_dir``."""
    return sorted(p.parent.name for p in results_dir.glob("*/shortlist.json"))


def _targets(lane: str | None, results_dir: Path, config_dir: Path) -> list[str]:
    """Resolve which lanes to sweep: a validated single ``--lane``, else every existing bucket."""
    if lane is None:
        return list(_lane_dirs(results_dir))
    valid = {ln.key for ln in load_lanes(config_dir)}
    if lane not in valid:
        raise SystemExit(f"unknown lane: {lane} (known: {', '.join(sorted(valid))})")
    return [lane]


def main(
    lane: str | None = None,
    *,
    delete: bool = False,
    dry_run: bool = False,
    today: str | None = None,
) -> None:
    """Refresh per-lane shortlists against the corpus + a live URL re-probe (CLI entry, #214)."""
    settings = AppSettings()
    results = settings.results_dir
    today = today or date.today().isoformat()
    corpus = (
        json.loads((results / "corpus.json").read_text())
        if (results / "corpus.json").is_file()
        else []
    )
    corpus_by_id = {r["id"]: r for r in corpus}
    latest_pull = max((r.get("last_seen", "") for r in corpus), default=today)

    verb = "would flag" if dry_run else ("deleted" if delete else "flagged")
    for ln in _targets(lane, results, settings.config_dir):
        rep = refresh_lane(
            ln,
            results,
            corpus_by_id,
            latest_pull,
            fetch_status,
            today,
            delete=delete,
            dry_run=dry_run,
        )
        if rep["missing"]:
            print(f"{ln}: no shortlist.json")
        else:
            print(f"{ln}: {rep['live']} live, {verb} {rep['stale']} stale")


if __name__ == "__main__":
    main()
