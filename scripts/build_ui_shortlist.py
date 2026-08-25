"""Flatten per-lane ``results/<lane>/shortlist.json`` into one array for the local dashboard.

Thin glue for ``make preview`` only: writes a throwaway ``public/data/shortlist.json`` into the
temp serve dir so the dashboard shows the REAL shortlist, not the synthetic demo set.

The real shortlist is PII: never committed, never published (gh-pages bundles no shortlist). For any
row whose offer has been tailored, its ``cv``/``cover_letter`` are attached from
``results/offers/<slug>/`` (joined by JD id via ``persist_offer.attach_tailor_docs``, #209); rows
without a tailored pack render with an empty detail.
"""

import glob
import json
import pathlib
import sys

from ajoa_kit.persist_offer import attach_tailor_docs


def _score_key(item: dict) -> float:
    """Sort key for one row: its numeric ``score``, or ``-inf`` when there is none to trust.

    ``bool`` is excluded deliberately — it is an ``int`` subclass, so a stray ``true`` would
    otherwise rank as a score of 1 instead of being treated as unusable.
    """
    score = item.get("score")
    if isinstance(score, bool) or not isinstance(score, int | float):
        return float("-inf")
    return float(score)


def aggregate(results_glob: str = "results/*/shortlist.json") -> list[dict]:
    """Flatten per-lane shortlist arrays into one list, ordered by ``score`` descending.

    Rows are collected in source-path order and then **stably** re-ordered by score, so equal-score
    rows keep that lane-path (and within a file, in-file) order — the output is snapshot-compared,
    so it has to stay deterministic. Ordering by path alone buried good offers: ``engineering``
    holds the large majority of rows, so a high-scoring row in a later lane landed hundreds of
    positions down the dashboard.

    A ``score`` that is missing, ``None`` or non-numeric is not an error here (this boundary reads
    raw JSON, and ``score`` is optional in :class:`ajoa_kit.models.ScoredItem`): such a row sorts to
    the bottom, below every scored row, rather than raising or displacing a real one.

    Skips entries the refresh sweep flagged ``stale`` (#214) so the dashboard never shows a
    filled/closed offer; the flagged row stays in ``results/<lane>/shortlist.json`` (audit trail).
    """
    items = [
        item
        for path in sorted(glob.glob(results_glob))
        for item in json.loads(pathlib.Path(path).read_text())
        if not item.get("stale")
    ]
    items.sort(key=_score_key, reverse=True)
    return items


def main(out_path: str) -> None:
    items = aggregate()
    if items:
        attach_tailor_docs(items, pathlib.Path("results"))
        pathlib.Path(out_path).write_text(json.dumps(items))
        msg = f"preview: bundled {len(items)} real shortlist rows -> {out_path}"
    else:
        msg = "preview: no real shortlist (results/*/shortlist.json) -> synthetic demo"
    sys.stdout.write(msg + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
