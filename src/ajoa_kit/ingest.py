"""Stage-2 ingestion: pull job descriptions (JDs) from feed/API-first sources.

Deterministic only — fetch + parse + normalize + pre-filter + dedupe. No relevance
judgment here (that is the LLM pass in ``cc-workflow-relevance.js``).

Sources are feed/API-first and no-auth, loaded from ``config/seed.json``:
  - RSS/Atom feeds (broad, no slug)
  - Greenhouse / Ashby / Recruitee / Lever / Workable / Personio (per-company, slug-keyed)

Run via the wrapper (borrows polyfetch's uv env so ``polyfetch_scrape`` imports)::

    scripts/ingest.sh

Writes ``results/jobs-raw.json`` (the relevance pass's input) and
``results/jobs-raw.summary.md`` (per-source counts + any failures).
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ajoa_kit.corpus import merge_corpus, render_daily_summary, summarize_changes
from ajoa_kit.defaults import DEFAULT_LANES, INTEREST, TITLE_ROLES
from ajoa_kit.models import Lane, LocationPolicy, ManualJd, SeniorityPolicy
from ajoa_kit.normalize import _INTEREST, _TITLE_ROLES, build_patterns, keep, record
from ajoa_kit.settings import AppSettings
from ajoa_kit.sources import AGGREGATORS, ATS, from_rss, load_sources

if TYPE_CHECKING:
    import re
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Any


def load_keywords(config_dir: Path) -> tuple[list[str], list[str]]:
    """Return (interest, title_roles); the tracked ``config/keywords.json`` is canonical.

    The shipped file is the keyword SSOT (#249 slice B) — its terms become the published trend
    keys, so keep it generic; point ``AJOA_CONFIG_DIR`` at a private dir for a personal vocabulary.
    Absent the file, the in-code mirror in :mod:`ajoa_kit.defaults` applies (a drift-guard test
    keeps file and mirror equal).
    """
    path = config_dir / "keywords.json"
    if not path.is_file():
        return INTEREST, TITLE_ROLES
    data = json.loads(path.read_text())
    return data.get("interest", INTEREST), data.get("title_roles", TITLE_ROLES)


def load_lanes(config_dir: Path) -> list[Lane]:
    """Return the position lanes; ``config_dir/lanes.json`` overrides :data:`DEFAULT_LANES`.

    The shipped ``config/lanes.json`` is the cross-runtime lane SSOT (ADR-0003): loaded here for the
    Python side and emitted via ``ajoa-kit lanes --json`` to pass JS workflows as ``args.lanes``, so
    one file feeds both runtimes. Absent the file, the in-code defaults apply.

    Args:
        config_dir: The config root (from ``AppSettings``).

    Returns:
        The validated lanes, in file order.
    """
    path = config_dir / "lanes.json"
    if not path.is_file():
        return DEFAULT_LANES
    data = json.loads(path.read_text())
    return [Lane.model_validate(item) for item in data]


def load_location(config_dir: Path) -> LocationPolicy:
    """Return the candidate's location policy; an absent ``config_dir/location.json`` is inert.

    Emitted to the relevance workflow via ``ajoa-kit location --json`` (mirrors
    :func:`load_lanes`), so one file feeds both runtimes. The file is deliberately **not**
    committed — it describes a person, and the repo's no-PII rule keeps it under the ``config/``
    ignore. Its absence is the normal case for a fresh clone and must never fail: an empty policy
    reports :attr:`~ajoa_kit.models.LocationPolicy.is_active` False and the screen skips location
    filtering entirely.

    Args:
        config_dir: The config root (from ``AppSettings``).

    Returns:
        The validated policy, or an empty (inert) one when the file is absent.
    """
    path = config_dir / "location.json"
    if not path.is_file():
        return LocationPolicy()
    return LocationPolicy.model_validate(json.loads(path.read_text()))


def load_tenure(config_dir: Path) -> SeniorityPolicy:
    """Return the candidate's tenure policy; an absent ``config_dir/tenure.json`` is inert.

    Mirrors :func:`load_location` exactly (arc-010 item 8): emitted via ``ajoa-kit tenure --json``,
    deliberately **not** committed (describes a person), and an absent file is the normal case for
    a fresh clone — never a failure.

    Args:
        config_dir: The config root (from ``AppSettings``).

    Returns:
        The validated policy, or an empty (inert) one when the file is absent.
    """
    path = config_dir / "tenure.json"
    if not path.is_file():
        return SeniorityPolicy()
    return SeniorityPolicy.model_validate(json.loads(path.read_text()))


def load_manual_jds(config_dir: Path) -> list[dict[str, Any]]:
    """Return hand-captured JDs from ``config_dir/manual-jds.json`` as normalized records.

    Mirrors :func:`load_lanes` / :func:`load_location`: an absent file is inert and returns ``[]``,
    which is the normal case for a fresh clone. See :class:`ajoa_kit.models.ManualJd` for why these
    are config rather than rows in ``results/jobs-raw.json``.

    Args:
        config_dir: The config root (from ``AppSettings``).

    Returns:
        One :func:`ajoa_kit.normalize.record` per entry, in file order.

    Raises:
        ValueError: If any entry is malformed. Deliberately loud — skipping a bad entry would
            silently lose exactly the record this file exists to protect.
    """
    path = config_dir / "manual-jds.json"
    if not path.is_file():
        return []
    try:
        entries = [ManualJd.model_validate(item) for item in json.loads(path.read_text())]
    except ValidationError as exc:
        raise ValueError(f"malformed entry in {path.name} ({config_dir}): {exc}") from exc
    return [
        record(
            source="manual",
            ats="manual",
            fetched_backend="manual-capture",
            **e.model_dump(),
        )
        for e in entries
    ]


# --- run ------------------------------------------------------------------------------
def collect(
    sources: list[tuple[str, Callable[[], Iterable[dict[str, Any]]]]],
    pat_interest: re.Pattern[str] = _INTEREST,
    pat_title: re.Pattern[str] = _TITLE_ROLES,
) -> dict[str, Any]:
    """Pull every source (warn-and-continue), applying the pre-filter; return run state."""
    jobs: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    filtered: dict[str, int] = {}
    tiers: dict[str, str] = {}
    failures: list[str] = []
    for label, pull in sources:
        try:
            rows = list(pull())
        except Exception as e:  # warn-and-continue: one bad source must not abort the whole run
            failures.append(f"{label}: {type(e).__name__}: {e}")
            continue
        kept = [r for r in rows if keep(r, pat_interest, pat_title)]
        jobs += kept
        counts[label] = len(kept)
        filtered[label] = len(rows) - len(kept)
        tiers[label] = rows[0]["fetched_backend"] if rows else "-"
    return {
        "jobs": jobs,
        "counts": counts,
        "filtered": filtered,
        "tiers": tiers,
        "failures": failures,
    }


def dedupe(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate JDs by id (earlier sources win on collision)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for j in jobs:
        if j["id"] in seen:
            continue
        seen.add(j["id"])
        out.append(j)
    return out


def with_manual(pulled: list[dict[str, Any]], manual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append ``manual`` records to a ``pulled`` batch; a pulled record with the same id wins.

    Order carries the policy: :func:`dedupe` keeps the first occurrence, and once a board actually
    publishes a posting it is authoritative over the hand-captured copy. Injecting on every run is
    also what keeps :func:`ajoa_kit.corpus.merge_corpus` from delisting a manual record — it is
    never "absent from today's pull".

    Manual records join *after* :func:`collect`, so they deliberately bypass the keyword pre-filter:
    a human already decided this posting is worth keeping.
    """
    return dedupe(pulled + manual)


def build_summary(deduped: list[dict[str, Any]], state: dict[str, Any]) -> str:
    """Render the per-source ingestion summary markdown."""
    counts, filtered, tiers, failures = (
        state["counts"],
        state["filtered"],
        state["tiers"],
        state["failures"],
    )
    total_filtered = sum(filtered.values())
    tier_dist: dict[str, int] = {}
    for t in tiers.values():
        tier_dist[t] = tier_dist.get(t, 0) + 1
    lines = [
        "# jobs-raw — ingestion summary",
        "",
        f"Total JDs kept: **{len(deduped)}** (deduped) — pre-filter dropped {total_filtered} "
        "(department/title not in INTEREST).",
        "",
        "## polyfetch tier per source (escalation = anti-bot fallback)",
        "",
        "httpx = tier-1 · curl_cffi = tier-2 TLS impersonation · playwright = tier-3 headless",
        "",
    ]
    lines += [f"- `{t}` — {tier_dist[t]} sources" for t in sorted(tier_dist)]
    lines += ["", "## Per-source counts (kept | filtered-out | tier)", ""]
    for k in sorted(counts):
        lines.append(f"- `{k}` — {counts[k]} | {filtered.get(k, 0)} | {tiers.get(k, '-')}")
    if failures:
        lines += ["", "## Failed (prune/fix the slug, then re-run)", ""]
        lines += [f"- `{x}`" for x in failures]
    return "\n".join(lines) + "\n"


def _update_corpus(deduped: list[dict[str, Any]], results_dir: Path, today: str) -> None:
    """Fold the fresh deduped pull into ``results/corpus.json`` (the running #164 corpus).

    Reads the prior corpus (empty on the first run), runs the four-state
    :func:`ajoa_kit.corpus.merge_corpus`, writes it back, and emits a local-only
    ``results/daily-summary.md`` "what changed today" digest (#175; never a CI artifact).
    ``jobs-raw.json`` is left untouched —
    it stays today's active pull for the relevance screen; the corpus is the growing history
    (first_seen / last_seen / delisted) that the trends snapshot and the daily cron read.

    Args:
        deduped: Today's freshly-ingested, deduped JD records.
        results_dir: The results root (``AppSettings().results_dir``).
        today: ISO date stamp (``YYYY-MM-DD``) for this pull.
    """
    path = results_dir / "corpus.json"
    prior = json.loads(path.read_text()) if path.exists() else []
    merged = merge_corpus(prior, deduped, today)
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    print(f"corpus: {len(merged)} records -> {path} (prior {len(prior)})")
    # Local-only "what changed today" digest (#175). It names companies/titles/URLs (actual offer
    # data, not aggregate), so it is written under the git-ignored results/ and is NEVER uploaded by
    # CI or pushed to a branch — the daily cron publishes only the aggregate keyword trends.
    summary = summarize_changes(prior, merged, today)
    summary_path = results_dir / "daily-summary.md"
    summary_path.write_text(render_daily_summary(summary))
    print(
        f"digest: {summary['new']} new / {summary['changed']} changed / "
        f"{summary['delisted']} delisted -> {summary_path}"
    )


def main(*, merge: bool = False, today: str | None = None) -> None:
    """Ingest all configured sources into results/jobs-raw.json (+ summary).

    With ``merge=True`` (the daily-ingest path, #164) the deduped pull is also folded into
    ``results/corpus.json`` via the four-state merge, stamped ``today`` (defaults to the current
    date). ``jobs-raw.json`` is written the same way regardless of ``merge``.

    Args:
        merge: When True, additionally maintain the incremental ``results/corpus.json``.
        today: ISO date stamp for the merge; defaults to ``date.today()`` when omitted.
    """
    settings = AppSettings()
    results = settings.results_dir
    results.mkdir(parents=True, exist_ok=True)
    feeds, seed, aggregators = load_sources(settings.config_dir)
    pat_interest, pat_title = build_patterns(*load_keywords(settings.config_dir))
    sources: list[tuple[str, Callable[[], Iterable[dict[str, Any]]]]] = [
        (f"feed/{f['source']}", (lambda f=f: from_rss(f))) for f in feeds
    ]
    sources += [(f"{c['ats']}/{c['slug']}", (lambda c=c: ATS[c["ats"]](c))) for c in seed]
    sources += [
        (f"aggregator/{a['name']}", (lambda a=a: AGGREGATORS[a["name"]](a))) for a in aggregators
    ]

    state = collect(sources, pat_interest, pat_title)
    manual = load_manual_jds(settings.config_dir)
    deduped = with_manual(state["jobs"], manual)
    (results / "jobs-raw.json").write_text(json.dumps(deduped, indent=2, ensure_ascii=False))
    (results / "jobs-raw.summary.md").write_text(build_summary(deduped, state))
    if merge:
        _update_corpus(deduped, results, today or date.today().isoformat())

    total_filtered = sum(state["filtered"].values())
    print(
        f"wrote {len(deduped)} JDs -> results/jobs-raw.json "
        f"(dropped {total_filtered}, {len(manual)} manual)"
    )
    print(f"sources ok: {len(state['counts'])}  failed: {len(state['failures'])}")
    for x in state["failures"]:
        print(f"  FAIL {x}")


if __name__ == "__main__":
    main()
