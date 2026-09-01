"""Tier 1 — open every selected shortlist offer's application URL in a browser tab (#417, plan 012).

The simplest of the three tiers issue #417 asks for: no ``render_session`` — verified in
``docs/plans/012-tiered-apply-prefill.md`` to hardcode ``headless=True``, which would show a human
nothing — just stdlib ``webbrowser.open()`` per selected offer's URL. Reuses
:func:`ajoa_kit.pack_plan.select` directly rather than re-implementing its filter/sort/dedup
pipeline, and reads ``.url`` off the in-memory :class:`~ajoa_kit.models.ScoredItem` rows *before*
``pack-plan.json``'s on-disk write would strip it. Run::

    ajoa-kit open-offers --min-score 5 --lanes engineering,ml
    ajoa-kit open-offers --dry-run   # print what would open, without opening a browser
"""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from ajoa_kit.ingest import load_lanes
from ajoa_kit.pack_plan import load_policy, select
from ajoa_kit.persist_scored import load_shortlist
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from ajoa_kit.models import PackPolicy, ScoredItem


def selected_urls(
    shortlist_rows: list[ScoredItem], policy: PackPolicy
) -> list[tuple[str, str, str, str]]:
    """Return ``(id, title, company, url)`` for every offer tier 1 would open.

    Reuses :func:`ajoa_kit.pack_plan.select` for the filter/sort/dedup pipeline; an item with an
    empty or missing ``url`` is skipped (nothing to open).

    Args:
        shortlist_rows: Rows from one or more lanes' ``shortlist.json``.
        policy: The active pack policy (same shape ``pack-plan`` uses).

    Returns:
        Selected rows as ``(id, title, company, url)`` tuples, in :func:`select`'s priority order.
    """
    return [
        (item.id, item.title, item.company, item.url)
        for item in select(shortlist_rows, policy)
        if item.url
    ]


def main(
    *,
    min_score: int | None = None,
    lanes: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    """Open every selected shortlist offer's URL in a browser tab; CLI entry (tier 1, #417).

    Args:
        min_score: Overrides the loaded policy's ``min_score`` when given.
        lanes: Overrides the loaded policy's ``lanes`` when given.
        dry_run: Print what would be opened (title/company/url) without calling
            ``webbrowser.open`` — the CLI invocation is itself the per-offer human trigger.
    """
    settings = AppSettings()
    results = settings.results_dir
    policy = load_policy(settings.config_dir)
    overrides = {k: v for k, v in {"min_score": min_score, "lanes": lanes}.items() if v is not None}
    if overrides:
        policy = policy.model_copy(update=overrides)

    shortlist_rows: list[ScoredItem] = []
    for lane in load_lanes(settings.config_dir):
        path = results / lane.key / "shortlist.json"
        if path.is_file():
            shortlist_rows.extend(load_shortlist(path))

    targets = selected_urls(shortlist_rows, policy)

    if not targets:
        print("no offers matched the policy — nothing to open")
        return

    for _id, title, company, url in targets:
        if dry_run:
            print(f"[dry-run] would open: {title} @ {company} -> {url}")
        else:
            print(f"opening: {title} @ {company} -> {url}")
            webbrowser.open(url)
