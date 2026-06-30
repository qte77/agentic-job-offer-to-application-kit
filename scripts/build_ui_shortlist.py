"""Flatten per-lane ``results/<lane>/shortlist.json`` into one array for the local dashboard.

Thin glue for ``make preview`` only: writes a throwaway ``public/data/shortlist.json`` into the
temp serve dir so the dashboard shows the REAL shortlist, not the synthetic demo set.

The real shortlist is PII: never committed, never published (gh-pages bundles no shortlist). No
``cv``/``cover_letter`` is attached here (those live per offer under ``results/offers/<slug>/`` and
are wired in a follow-up) — rows render with an empty detail.
"""

import glob
import json
import pathlib
import sys


def aggregate(results_glob: str = "results/*/shortlist.json") -> list[dict]:
    """Flatten per-lane shortlist arrays into one list, ordered by source path."""
    return [
        item
        for path in sorted(glob.glob(results_glob))
        for item in json.loads(pathlib.Path(path).read_text())
    ]


def main(out_path: str) -> None:
    items = aggregate()
    if items:
        pathlib.Path(out_path).write_text(json.dumps(items))
        msg = f"preview: bundled {len(items)} real shortlist rows -> {out_path}"
    else:
        msg = "preview: no real shortlist (results/*/shortlist.json) -> synthetic demo"
    sys.stdout.write(msg + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
