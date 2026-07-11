"""Aggregate the local corpus into a company-hiring snapshot for the dashboard (#284).

Thin glue for ``make preview`` only: writes a throwaway ``public/data/companies.json`` (who's hiring
by geo x field, per-company active-role counts) into the temp serve dir. LOCAL-ONLY — company + geo
are business data the ``data``-branch boundary guard forbids, so gh-pages bundles none: the
dashboard's Companies tab stays hidden on the published site and shows the real snapshot locally.

Mirrors ``scripts/build_ui_shortlist.py`` (the aggregate-for-preview pattern); all logic lives in
the tested :mod:`ajoa_kit.companies` module, so this script stays untested glue.
"""

import glob
import json
import pathlib
import sys

from ajoa_kit.companies import aggregate_companies


def lane_by_id(results_glob: str = "results/*/shortlist.json") -> dict[str, str]:
    """Map JD id -> scored ``best_lane`` from the non-stale shortlist rows (refines the field)."""
    out: dict[str, str] = {}
    for path in sorted(glob.glob(results_glob)):
        for item in json.loads(pathlib.Path(path).read_text()):
            if item.get("stale"):
                continue
            jid, lane = item.get("id"), item.get("best_lane")
            if jid and lane:
                out[jid] = lane
    return out


def main(out_path: str, corpus_path: str = "results/corpus.json") -> None:
    corpus_file = pathlib.Path(corpus_path)
    corpus = json.loads(corpus_file.read_text()) if corpus_file.exists() else []
    rows = aggregate_companies(corpus, lane_by_id=lane_by_id()) if corpus else []
    if rows:
        pathlib.Path(out_path).write_text(json.dumps([r.model_dump() for r in rows]))
        msg = f"preview: bundled {len(rows)} company rows -> {out_path}"
    else:
        msg = "preview: no corpus (results/corpus.json) -> companies tab stays hidden"
    sys.stdout.write(msg + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
