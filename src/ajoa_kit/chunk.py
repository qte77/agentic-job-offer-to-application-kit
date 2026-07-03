"""Split results/jobs-raw.json into results/batches/batch-NNN.json for the relevance workflow.

Pure stdlib (no polyfetch). Run::

    python -m ajoa_kit.chunk [batch_size]

The ``cc-workflow-relevance.js`` workflow fans out one agent per batch file; each agent
reads ~batch_size JDs and judges lane-fit in a single context. Re-run after re-ingesting.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_BATCH = 40


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
            json.dumps(jobs[i : i + batch], ensure_ascii=False, indent=2),
        )
        n += 1

    (out / "manifest.json").write_text(
        json.dumps({"total_jobs": len(jobs), "batch_size": batch, "batch_count": n}, indent=2),
    )
    print(f"wrote {n} batches of <= {batch} JDs -> {out}/  (manifest.json)")


if __name__ == "__main__":
    main(batch=int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BATCH)
