"""Config-driven pack-coverage policy — which shortlist rows earn a full tailored pack (arc-011).

Pack generation is otherwise fully manual: a human picks one shortlist row and runs the tailor
Workflow for that single ``offerId``. This composes a **work list** of every shortlist row a
:class:`~ajoa_kit.models.PackPolicy` selects but that has no pack on disk yet::

    ajoa-kit pack-plan --min-score 5 --json

writing ``results/pack-plan.json`` = ``[{offer_id, lane, score}]``, ready to feed the tailor
Workflow. The **coverage guarantee** is external to this module: an orchestrator loops
``pack-plan`` -> tailor Workflow per missing id -> ``persist-offer`` until ``missing == []``
(idempotent — a re-run after tailoring skips ids that already have a pack). See ADR-0005.
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

from ajoa_kit.ingest import load_lanes
from ajoa_kit.models import PackPolicy, ScoredItem
from ajoa_kit.persist_offer import _load_offer_index
from ajoa_kit.persist_scored import load_shortlist
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from pathlib import Path


def load_policy(config_dir: Path) -> PackPolicy:
    """Return the pack-selection policy; ``config_dir/pack-policy.json`` overrides defaults.

    Mirrors :func:`ajoa_kit.ingest.load_lanes` — an absent file is inert, not an error.

    Args:
        config_dir: The config root (from ``AppSettings``).

    Returns:
        The validated policy, or :class:`PackPolicy` defaults when the file is absent.
    """
    path = config_dir / "pack-policy.json"
    if not path.is_file():
        return PackPolicy()
    return PackPolicy.model_validate(json.loads(path.read_text()))


def _dedup_role_and_company(items: list[ScoredItem]) -> list[ScoredItem]:
    """Keep the first row per (title, company) pair, case-insensitive; later ones dropped.

    Called AFTER the score sort, so "first seen" is the highest-scoring instance of a role
    duplicated across sources (e.g. two aggregators surfacing the same posting).
    """
    seen: set[tuple[str, str]] = set()
    out: list[ScoredItem] = []
    for item in items:
        key = (item.title.strip().casefold(), item.company.strip().casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _apply_company_cap(items: list[ScoredItem], cap: int) -> list[ScoredItem]:
    """Keep at most ``cap`` items per company, walking in (already-ordered) input order."""
    counts: dict[str, int] = {}
    out: list[ScoredItem] = []
    for item in items:
        count = counts.get(item.company, 0)
        if count >= cap:
            continue
        counts[item.company] = count + 1
        out.append(item)
    return out


def select(shortlist_rows: list[ScoredItem], policy: PackPolicy) -> list[ScoredItem]:
    """Select + order the shortlist rows a pack policy targets for a full tailored pack.

    Pipeline: filter (score >= ``min_score``, lane membership) -> sort by score descending
    (stable — equal scores keep input order) -> dedup role x company (policy-gated) -> per-company
    cap -> ``max_packs`` cap.

    Args:
        shortlist_rows: Rows from one or more lanes' ``shortlist.json``.
        policy: The active pack policy.

    Returns:
        The selected rows, in priority order (highest score first).
    """
    candidates = [
        item
        for item in shortlist_rows
        if item.score is not None
        and item.score >= policy.min_score
        and (not policy.lanes or item.best_lane in policy.lanes)
    ]
    ordered = sorted(candidates, key=lambda item: -(item.score or 0))
    if policy.dedup == "role_x_company":
        ordered = _dedup_role_and_company(ordered)
    if policy.per_company_cap > 0:
        ordered = _apply_company_cap(ordered, policy.per_company_cap)
    if policy.max_packs > 0:
        ordered = ordered[: policy.max_packs]
    return ordered


def missing(targets: list[ScoredItem], offer_index: dict[str, Path]) -> list[str]:
    """Ids among the selected targets that have no pack directory yet.

    Args:
        targets: :func:`select`'s output.
        offer_index: JD id -> offer dir, from :func:`ajoa_kit.persist_offer._load_offer_index`.

    Returns:
        Target ids absent from ``offer_index``, in ``targets`` order.
    """
    return [item.id for item in targets if item.id not in offer_index]


def main(
    *,
    min_score: int | None = None,
    max_packs: int | None = None,
    lanes: list[str] | None = None,
    json_output: bool = False,
    dry_run: bool = False,
) -> None:
    """Write the missing-pack work list across every lane; CLI entry (ADR-0005).

    Args:
        min_score: Overrides the loaded policy's ``min_score`` when given.
        max_packs: Overrides the loaded policy's ``max_packs`` when given.
        lanes: Overrides the loaded policy's ``lanes`` when given.
        json_output: Print the work list as JSON instead of a one-line summary.
        dry_run: Report without writing ``results/pack-plan.json``.
    """
    settings = AppSettings()
    results = settings.results_dir
    policy = load_policy(settings.config_dir)
    overrides = {
        k: v
        for k, v in {"min_score": min_score, "max_packs": max_packs, "lanes": lanes}.items()
        if v is not None
    }
    if overrides:
        policy = policy.model_copy(update=overrides)

    shortlist_rows: list[ScoredItem] = []
    for lane in load_lanes(settings.config_dir):
        path = results / lane.key / "shortlist.json"
        if path.is_file():
            shortlist_rows.extend(load_shortlist(path))

    targets = select(shortlist_rows, policy)
    offer_index = _load_offer_index(results)
    missing_ids = set(missing(targets, offer_index))
    work_list = [
        {"offer_id": item.id, "lane": item.best_lane, "score": item.score}
        for item in targets
        if item.id in missing_ids
    ]

    if not dry_run:
        (results / "pack-plan.json").write_text(json.dumps(work_list, indent=2))

    if json_output:
        print(json.dumps(work_list, indent=2, ensure_ascii=False))
    else:
        covered = len(targets) - len(missing_ids)
        print(f"covered {covered}/{len(targets)}; missing: {sorted(missing_ids)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="ajoa-kit pack-plan")
    parser.add_argument("--min-score", type=int, default=None)
    parser.add_argument("--max-packs", type=int, default=None)
    parser.add_argument("--lanes", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()
    main(
        min_score=ns.min_score,
        max_packs=ns.max_packs,
        lanes=ns.lanes.split(",") if ns.lanes else None,
        json_output=ns.json,
        dry_run=ns.dry_run,
    )
