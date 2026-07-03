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


def aggregate(results_glob: str = "results/*/shortlist.json") -> list[dict]:
    """Flatten per-lane shortlist arrays into one list, ordered by source path.

    Skips entries the refresh sweep flagged ``stale`` (#214) so the dashboard never shows a
    filled/closed offer; the flagged row stays in ``results/<lane>/shortlist.json`` (audit trail).
    """
    return [
        item
        for path in sorted(glob.glob(results_glob))
        for item in json.loads(pathlib.Path(path).read_text())
        if not item.get("stale")
    ]


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
