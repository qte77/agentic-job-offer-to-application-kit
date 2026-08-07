"""CLI entry point for ajoa-kit: dispatches subcommands to L1 library functions.

Usage::

    ajoa-kit ingest
    ajoa-kit chunk [--batch-size N] [--new]
    ajoa-kit persist <workflow-result.json> [--merge]
    ajoa-kit persist-offer <workflow-result.json> [--slug SLUG]
    ajoa-kit refresh [--lane NAME] [--delete] [--dry-run]
    ajoa-kit verify-sources [--dry-run]
    ajoa-kit ats-check <cv.md>
    ajoa-kit render-pdf <cv.md> [--out OUT.pdf]
    ajoa-kit lanes [--json]
    ajoa-kit style [--json]
    ajoa-kit prefill-fields [--ats greenhouse --slug S --job-id ID]
    ajoa-kit probe
    ajoa-kit trend-snapshot
    ajoa-kit discover
    ajoa-kit status <slug> [--stage S] [--date D] [--notes N]

Each subcommand delegates to the corresponding L1 module's ``main()`` via its ``func``
default, without reimplementing any logic. ``polyfetch_scrape`` is imported lazily inside
the L1 functions, so this module stays importable offline.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _ingest(args: argparse.Namespace) -> None:
    """Run the ingest step (optionally folding into the incremental corpus)."""
    from ajoa_kit.ingest import main as run

    run(merge=args.merge)


def _chunk(args: argparse.Namespace) -> None:
    """Run the chunk step with the chosen batch size."""
    from ajoa_kit.chunk import DEFAULT_BATCH
    from ajoa_kit.chunk import main as run

    run(batch=args.batch_size if args.batch_size is not None else DEFAULT_BATCH, new=args.new)


def _persist(args: argparse.Namespace) -> None:
    """Persist a relevance workflow result into scored artifacts."""
    from ajoa_kit.persist_scored import main as run

    run(src=Path(args.file), merge=args.merge)


def _persist_offer(args: argparse.Namespace) -> None:
    """Persist a tailor workflow result into a per-offer pack."""
    from ajoa_kit.persist_offer import main as run

    run(src=Path(args.file), slug=args.slug)


def _status(args: argparse.Namespace) -> None:
    """Set or read a local offer's application-outcome status (#273)."""
    from ajoa_kit.status import main as run

    run(offer=args.offer, stage=args.stage, date=args.date, notes=args.notes)


def _ats_check(args: argparse.Namespace) -> None:
    """Check a CV markdown file for ATS parse-safety."""
    from ajoa_kit.ats_check import main as run

    run(src=Path(args.file))


def _render_pdf(args: argparse.Namespace) -> None:
    """Render a tailored .md (cv/cover-letter) to an ATS-safe PDF (needs the [pdf] extra)."""
    from ajoa_kit.render_pdf import main as run

    run(src=Path(args.file), out=Path(args.out) if args.out else None)


def _style(args: argparse.Namespace) -> None:
    """Preview the resolved writing-style directives."""
    from ajoa_kit.settings import AppSettings
    from ajoa_kit.style import main as run

    run(config_dir=AppSettings().config_dir, as_json=args.json)


def _lanes(args: argparse.Namespace) -> None:
    """Emit the position lanes (config/lanes.json) as the workflow `lanes` arg."""
    import json

    from ajoa_kit.ingest import load_lanes
    from ajoa_kit.settings import AppSettings

    lanes = load_lanes(AppSettings().config_dir)
    if args.json:
        payload = [lane.model_dump(by_alias=True) for lane in lanes]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for lane in lanes:
        print(f"{lane.key}\t{lane.label}")


def _location(args: argparse.Namespace) -> None:
    """Emit the candidate location policy (config/location.json) as the workflow `location` arg."""
    import json

    from ajoa_kit.ingest import load_location
    from ajoa_kit.settings import AppSettings

    policy = load_location(AppSettings().config_dir)
    if args.json:
        print(json.dumps(policy.model_dump(by_alias=True), indent=2, ensure_ascii=False))
        return
    if not policy.is_active:
        print("no location policy — the relevance screen will not filter on location")
        print("create config/location.json (untracked; see README) to enable it")
        return
    print(f"based_in\t{policy.based_in}")
    print(f"authorized_in\t{', '.join(policy.authorized_in)}")
    print(f"remote_ok\t{policy.remote_ok}")
    print(f"relocate_to\t{', '.join(policy.relocate_to) or '-'}")


def _prefill_fields(args: argparse.Namespace) -> None:
    """Print the application-field checklist for an offer (Greenhouse schema or generic)."""
    from ajoa_kit.prefill import main as run

    run(ats=args.ats, slug=args.slug, job_id=args.job_id)


def _probe(_args: argparse.Namespace) -> None:
    """Run the candidate-slug probe."""
    from ajoa_kit.slug_probe import main as run

    run()


def _trend_snapshot(_args: argparse.Namespace) -> None:
    """Snapshot keyword-only trends from the ingested corpus."""
    from ajoa_kit.trend_snapshot import main as run

    run()


def _companies_snapshot(_args: argparse.Namespace) -> None:
    """Snapshot company-hiring trends (geo-x-field public + local per-company) from the corpus."""
    from ajoa_kit.companies_trend import main as run

    run()


def _discover(_args: argparse.Namespace) -> None:
    """Derive an emerging/hiring company signal from the discovery source (local-only, #292)."""
    from ajoa_kit.discover import main as run

    run()


def _refresh(args: argparse.Namespace) -> None:
    """Reconcile per-lane shortlists: flag (or --delete) filled/closed offers (#214)."""
    from ajoa_kit.refresh import main as run

    run(lane=args.lane, delete=args.delete, dry_run=args.dry_run)


def _verify_sources(args: argparse.Namespace) -> None:
    """Re-probe seed feeds/ats and stamp _date_verified on the live ones (#217)."""
    from ajoa_kit.verify_sources import main as run

    run(dry_run=args.dry_run)


def main() -> None:
    """Parse the chosen subcommand and run the matching L1 pipeline step."""
    parser = argparse.ArgumentParser(
        prog="ajoa-kit",
        description="Agentic job-offer-to-application kit pipeline CLI.",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="SUBCOMMAND", required=True)

    ingest_p = sub.add_parser(
        "ingest", help="Fetch JDs into results/jobs-raw.json (needs polyfetch env)."
    )
    ingest_p.add_argument(
        "--merge",
        action="store_true",
        help="Also fold the pull into results/corpus.json (incremental dedup-merge, #164).",
    )
    ingest_p.set_defaults(func=_ingest)

    chunk_p = sub.add_parser("chunk", help="Split jobs-raw.json into results/batches/.")
    chunk_p.add_argument(
        "--batch-size", type=int, default=None, metavar="N", help="Records per batch (default: 40)."
    )
    chunk_p.add_argument(
        "--new",
        action="store_true",
        help="Batch only the latest-pull delta from results/corpus.json (#226 re-screen).",
    )
    chunk_p.set_defaults(func=_chunk)

    persist_p = sub.add_parser(
        "persist", help="Write scored artifacts from a workflow-result JSON."
    )
    persist_p.add_argument("file", metavar="FILE", help="Path to workflow-result.json.")
    persist_p.add_argument(
        "--merge",
        action="store_true",
        help="Union into existing shortlists / jobs-scored by id instead of overwriting (#226).",
    )
    persist_p.set_defaults(func=_persist)

    offer_p = sub.add_parser(
        "persist-offer", help="Write a per-offer application pack from a workflow-result JSON."
    )
    offer_p.add_argument("file", metavar="FILE", help="Path to workflow-result.json.")
    offer_p.add_argument("--slug", default=None, help="Offer slug (default: pack slug/id).")
    offer_p.set_defaults(func=_persist_offer)

    status_p = sub.add_parser(
        "status", help="Set/read a local application-outcome status per offer (#273)."
    )
    status_p.add_argument("offer", help="Offer slug (the results/offers/<slug>/ dir).")
    status_p.add_argument(
        "--stage", default=None, help="applied | responded | interview | offer | rejected."
    )
    status_p.add_argument("--date", default=None, help="Application/update date (YYYY-MM-DD).")
    status_p.add_argument("--notes", default=None, help="Free-text note.")
    status_p.set_defaults(func=_status)

    refresh_p = sub.add_parser(
        "refresh",
        help="Flag (or --delete) shortlist offers that are filled/closed (#214).",
    )
    refresh_p.add_argument("--lane", default=None, help="Only this lane (default: all buckets).")
    refresh_p.add_argument(
        "--delete", action="store_true", help="Remove stale rows instead of flagging them."
    )
    refresh_p.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    refresh_p.set_defaults(func=_refresh)

    verify_p = sub.add_parser(
        "verify-sources",
        help="Re-probe seed feeds/ats, stamp _date_verified on the live ones (#217).",
    )
    verify_p.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    verify_p.set_defaults(func=_verify_sources)

    ats_p = sub.add_parser(
        "ats-check", help="Check a CV markdown file for ATS parse-safety (non-zero if unsafe)."
    )
    ats_p.add_argument("file", metavar="FILE", help="Path to a CV markdown file.")
    ats_p.set_defaults(func=_ats_check)

    rp = sub.add_parser(
        "render-pdf", help="Render a tailored .md to an ATS-safe PDF. Needs the [pdf] extra."
    )
    rp.add_argument("file", metavar="FILE", help="Path to a tailored markdown file.")
    rp.add_argument("--out", default="", help="Output PDF path (default: <file>.pdf).")
    rp.set_defaults(func=_render_pdf)

    style_p = sub.add_parser("style", help="Preview the resolved writing-style directives (#16).")
    style_p.add_argument(
        "--json", action="store_true", help="Emit the workflow `style` arg object."
    )
    style_p.set_defaults(func=_style)

    lanes_p = sub.add_parser(
        "lanes", help="Emit position lanes (config/lanes.json) as the workflow lanes arg (#195)."
    )
    lanes_p.add_argument(
        "--json",
        action="store_true",
        help="Emit the JSON `args.lanes` payload (else a key->label list).",
    )
    lanes_p.set_defaults(func=_lanes)

    location_p = sub.add_parser(
        "location",
        help="Emit the candidate location policy (config/location.json) as the workflow arg.",
    )
    location_p.add_argument(
        "--json",
        action="store_true",
        help="Emit the JSON `args.location` payload (else a readable summary).",
    )
    location_p.set_defaults(func=_location)

    prefill_p = sub.add_parser(
        "prefill-fields",
        help="Print an offer's application-field checklist (Greenhouse or generic).",
    )
    prefill_p.add_argument(
        "--ats", default="", help="ATS name; 'greenhouse' fetches the live schema."
    )
    prefill_p.add_argument("--slug", default="", help="Greenhouse board slug.")
    prefill_p.add_argument("--job-id", default="", help="Greenhouse job id.")
    prefill_p.set_defaults(func=_prefill_fields)

    sub.add_parser(
        "probe",
        help=(
            "Probe candidate slugs across ATS platforms. "
            "Requires polyfetch env (run via scripts/ingest.sh or set POLYFETCH_DIR)."
        ),
    ).set_defaults(func=_probe)

    sub.add_parser(
        "trend-snapshot",
        help="Snapshot keyword-only trends into public-data/trends{,-daily,-monthly}.ndjson.",
    ).set_defaults(func=_trend_snapshot)

    sub.add_parser(
        "companies-snapshot",
        help=(
            "Snapshot company-hiring trends: geo-by-field into "
            "public-data/hiring-{weekly,daily,monthly}.ndjson + local per-company into "
            "results/hiring-companies.ndjson."
        ),
    ).set_defaults(func=_companies_snapshot)

    sub.add_parser(
        "discover",
        help=(
            "Derive an emerging/who's-hiring company signal from the config 'discovery' source "
            "into results/emerging-companies.json (local business data, never published). "
            "Requires polyfetch env (set POLYFETCH_DIR)."
        ),
    ).set_defaults(func=_discover)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
