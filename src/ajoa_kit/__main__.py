"""CLI entry point for ajoa-kit: dispatches subcommands to L1 library functions.

Usage::

    ajoa-kit ingest
    ajoa-kit chunk [--batch-size N]
    ajoa-kit persist <workflow-result.json>
    ajoa-kit probe

Each subcommand delegates directly to the corresponding L1 module's ``main()``
without reimplementing any logic.  ``polyfetch_scrape`` is still imported lazily
inside the L1 functions, so this module is importable offline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    """Parse the chosen subcommand and run the matching L1 pipeline step."""
    parser = argparse.ArgumentParser(
        prog="ajoa-kit",
        description="Agentic job-offer-to-application kit pipeline CLI.",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="SUBCOMMAND")
    sub.required = True

    sub.add_parser("ingest", help="Fetch JDs into results/jobs-raw.json (needs polyfetch env).")

    chunk_p = sub.add_parser("chunk", help="Split jobs-raw.json into results/batches/.")
    chunk_p.add_argument(
        "--batch-size",
        type=int,
        default=None,
        metavar="N",
        help="Records per batch file (default: 40).",
    )

    persist_p = sub.add_parser(
        "persist", help="Write scored artifacts from a workflow-result JSON."
    )
    persist_p.add_argument("file", metavar="FILE", help="Path to workflow-result.json.")

    sub.add_parser(
        "probe",
        help=(
            "Probe candidate slugs across ATS platforms. "
            "Requires polyfetch env (run via scripts/ingest.sh or set POLYFETCH_DIR)."
        ),
    )

    args = parser.parse_args()

    if args.cmd == "ingest":
        from ajoa_kit.ingest import main as _main

        _main()

    elif args.cmd == "chunk":
        from ajoa_kit.chunk import DEFAULT_BATCH
        from ajoa_kit.chunk import main as _main

        batch = args.batch_size if args.batch_size is not None else DEFAULT_BATCH
        _main(batch=batch)

    elif args.cmd == "persist":
        from ajoa_kit.persist_scored import main as _main

        _main(src=Path(args.file))

    elif args.cmd == "probe":
        from ajoa_kit.slug_probe import main as _main

        _main()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
