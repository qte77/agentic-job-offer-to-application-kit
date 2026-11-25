"""Persist a ``cc-workflow-relevance.js`` result into jobs-scored.json + per-lane shortlists.

The Workflow tool returns the scored shortlist (it cannot write files); this turns that
returned JSON into on-disk artifacts. Run::

    python -m ajoa_kit.persist_scored <path-to-workflow-result.json>

Writes ``results/jobs-scored.json`` (the full result) and
``results/<lane>/shortlist.{json,md}`` for each best_lane (sorted by score desc).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from ajoa_kit.ingest import load_lanes
from ajoa_kit.models import ScoredItem, ScreenedJd

# The deliberate ingest-era duplicate collapsed here (#249 slice C): the lightweight
# normalize module removed the original reason to duplicate (avoiding ingest's heavy import).
from ajoa_kit.normalize import canonical_url
from ajoa_kit.pull import pull_date
from ajoa_kit.settings import AppSettings


def load_result(src: Path) -> dict:
    """Parse the workflow output JSON, tolerating surrounding text and the ``result`` wrapper."""
    raw = src.read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:  # tolerate surrounding text
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise
        data = json.loads(match.group(0))
    # The Workflow tool wraps the script's return value under "result".
    if "relevant" not in data and isinstance(data.get("result"), dict):
        data = data["result"]
    return data


def parse_relevant(data: dict) -> tuple[list[ScoredItem], int]:
    """Parse-on-read the relevance result: fail loud if it isn't one; drop + count malformed items.

    JS validates each item at the ``agent()`` boundary, but that guarantee is lost when Python reads
    the file back (a human passes the path — hand-edited / truncated / wrong). Re-validating
    here stops a junk result writing junk artifacts: a structurally-wrong file fails loud; a single
    malformed item is dropped (not fatal).
    """
    if not isinstance(data.get("relevant"), list):
        msg = "no 'relevant' array — is this a cc-workflow-relevance.js result?"
        raise ValueError(msg)  # noqa: TRY004 — malformed data shape, not a wrong-typed arg
    kept: list[ScoredItem] = []
    dropped = 0
    for raw in data["relevant"]:
        try:
            kept.append(ScoredItem.model_validate(raw))
        except ValidationError:
            dropped += 1
    return kept, dropped


def load_batches(results_dir: Path) -> dict[int, list[ScreenedJd]]:
    """Parse the batch files ``chunk`` wrote, keyed by batch index; fail loud if there are none."""
    files = sorted((results_dir / "batches").glob("batch-*.json"))
    if not files:
        msg = (
            "no results/batches/batch-*.json to match rows against; run `chunk` before the screen."
        )
        raise FileNotFoundError(msg)
    return {
        int(f.stem.removeprefix("batch-")): [
            ScreenedJd.model_validate(r) for r in json.loads(f.read_text())
        ]
        for f in files
    }


def match_batches(
    rel: list[ScoredItem], records: list[ScreenedJd]
) -> tuple[list[ScoredItem], list[ScoredItem]]:
    """Tie each row to the batch record it was screened from (#513); return (matched, unmatched).

    Screen agents mangle ids and urls, so the record, not the agent, supplies id, url, company
    and title. A row whose id matches no record falls back to an exact (company, title) match,
    taken only when exactly one record has that pair and no other row already holds it by id.
    """
    by_id = {r.id: r for r in records}
    by_name: dict[tuple[str, str], list[ScreenedJd]] = {}
    for r in records:
        by_name.setdefault((r.company, r.title), []).append(r)
    claimed = {j.id for j in rel if j.id in by_id}
    matched: list[ScoredItem] = []
    unmatched: list[ScoredItem] = []
    for j in rel:
        rec = by_id.get(j.id)
        if rec is None:
            hits = by_name.get((j.company, j.title), [])
            rec = hits[0] if len(hits) == 1 and hits[0].id not in claimed else None
        if rec is None:
            unmatched.append(j)
            continue
        claimed.add(rec.id)
        j.id, j.url, j.company, j.title = rec.id, rec.url, rec.company, rec.title
        matched.append(j)
    return matched, unmatched


def _dropped_ids(
    data: dict, batches: dict[int, list[ScreenedJd]], rel: list[ScoredItem], unmatched: int
) -> tuple[set[str], str]:
    """Ids the re-screen read but did not keep (#515), or none plus the reason removal is skipped.

    Only the batches the result names in ``screenedBatches`` were read: a sliced run or a failed
    batch agent leaves the rest unscreened. An unmatched row may be a kept JD whose id the agent
    garbled, so its real id would look dropped; any unmatched row skips removal for the run.
    """
    if "screenedBatches" not in data:
        return set(), "no screenedBatches in the result, none removed"
    if unmatched:
        return set(), f"{unmatched} unmatched rows, none removed"
    screened = TypeAdapter(list[int]).validate_python(data["screenedBatches"])
    read = {r.id for i in screened for r in batches.get(i, [])}
    return read - {j.id for j in rel}, ""


def load_shortlist(path: Path) -> list[ScoredItem]:
    """Validate a per-lane ``shortlist.json`` off disk into ``ScoredItem`` models (fail-loud).

    These files are Python-written from validated models (unlike the human-supplied result path
    :func:`parse_relevant` guards), so a failed row means corruption — surfacing it beats silently
    dropping an audit-trail entry. Reused by the merge sweep and :mod:`ajoa_kit.refresh`.
    """
    return [ScoredItem.model_validate(r) for r in json.loads(path.read_text())]


def load_all_shortlists(settings: AppSettings) -> list[ScoredItem]:
    """Load every lane's shortlist.json (skipping lanes with none yet) into ScoredItem rows."""
    results = settings.results_dir
    rows: list[ScoredItem] = []
    for lane in load_lanes(settings.config_dir):
        path = results / lane.key / "shortlist.json"
        if path.is_file():
            rows.extend(load_shortlist(path))
    return rows


def _flags(item: ScoredItem) -> tuple[str, str]:
    """Render the #271 human-flag annotations: (tag suffix, deal-breaker bullet; "" when unset)."""
    deadline, breaker = item.deadline.strip(), item.deal_breaker.strip()
    suffix = (f" · due {deadline}" if deadline else "") + (" · deal-breaker" if breaker else "")
    bullet = f"  - deal-breaker: {breaker}" if breaker else ""
    return suffix, bullet


def write_lane(lane: str, items: list[ScoredItem], results_dir: Path) -> None:
    """Write one lane's ``shortlist.{json,md}`` — score desc, stale rows (#214) sunk last + tagged.

    Shared by :func:`write_shortlists` (fresh persist), the merge sweep, and the refresh sweep
    (:mod:`ajoa_kit.refresh`); fresh items carry no ``stale`` flag, so the order matches the prior
    score-only sort.
    """
    items = sorted(items, key=lambda x: (x.stale, -(x.score or 0)))
    d = results_dir / lane
    d.mkdir(parents=True, exist_ok=True)
    (d / "shortlist.json").write_text(
        json.dumps([it.model_dump() for it in items], indent=2, ensure_ascii=False)
    )
    lines = [f'---\ntitle: "{lane} — shortlist ({len(items)})"\n---', ""]
    for j in items:
        suffix, bullet = _flags(j)
        tag = f"{j.score}/{j.verdict}" + (" · stale" if j.stale else "") + suffix
        lines.append(f"- [{tag}] {j.title} @ {j.company}")
        lines.append(f"  - {j.url}")
        lines.append(f"  - {j.rationale}")
        if bullet:
            lines.append(bullet)
    (d / "shortlist.md").write_text("\n".join(lines) + "\n")


def write_shortlists(rel: list[ScoredItem], results_dir: Path) -> dict[str, int]:
    """Write per-lane shortlist.{json,md}; return the per-lane counts."""
    by_lane: dict[str, list[ScoredItem]] = {}
    for j in rel:
        # `or "unsorted"`: an empty/absent best_lane (the LLM left it un-laned) must not become an
        # empty-string directory under results/ — it lands in unsorted/.
        by_lane.setdefault(j.best_lane or "unsorted", []).append(j)
    for lane, items in by_lane.items():
        write_lane(lane, items, results_dir)
    return {k: len(v) for k, v in by_lane.items()}


def _union_by_id(existing: list[ScoredItem], incoming: list[ScoredItem]) -> list[ScoredItem]:
    """Union two scored-item lists by ``id`` — existing kept, incoming (re-scored) wins on a tie."""
    by_id = {j.id: j for j in existing}
    for j in incoming:
        by_id[j.id] = j
    return list(by_id.values())


def _evict_ids(incoming_ids: set[str], skip_lanes: set[str], results_dir: Path) -> None:
    """Evict ``incoming_ids`` from every existing bucket except ``skip_lanes`` (#236)."""
    for path in results_dir.glob("*/shortlist.json"):
        lane = path.parent.name
        if lane in skip_lanes:
            continue
        existing = load_shortlist(path)
        kept = [it for it in existing if it.id not in incoming_ids]
        if len(kept) != len(existing):
            write_lane(lane, kept, results_dir)


def merge_shortlists(
    rel: list[ScoredItem], results_dir: Path, *, drop: frozenset[str] = frozenset()
) -> dict[str, int]:
    """Union ``rel`` by id into each per-lane bucket; evict re-laned ids from their old lane (#236).

    An incoming id ends up in its new lane only, so a re-laned offer never double-buckets. Groups by
    ``best_lane`` (``or "unsorted"``) and reuses :func:`write_lane`; untouched lanes stay as-is.
    ``drop`` ids (dropped by the re-screen, #515) leave every lane.
    """
    by_lane: dict[str, list[ScoredItem]] = {}
    for j in rel:
        by_lane.setdefault(j.best_lane or "unsorted", []).append(j)
    evict = {j.id for j in rel} | drop
    _evict_ids(evict, set(by_lane), results_dir)
    counts: dict[str, int] = {}
    for lane, incoming in by_lane.items():
        path = results_dir / lane / "shortlist.json"
        existing = load_shortlist(path) if path.is_file() else []
        cleaned = [it for it in existing if it.id not in evict]
        merged = _union_by_id(cleaned, incoming)
        write_lane(lane, merged, results_dir)
        counts[lane] = len(merged)
    return counts


def _load_prior_relevant(scored: Path) -> list[ScoredItem]:
    """Validate the prior ``jobs-scored.json`` relevant array into models for the merge union."""
    prior = json.loads(scored.read_text()).get("relevant", [])
    return [ScoredItem.model_validate(r) for r in prior]


def _merge_scored(
    scored: Path, rel: list[ScoredItem], gone: set[str], skipped: str
) -> tuple[list[ScoredItem], str]:
    """Union ``rel`` into the stored rows less ``gone``; return them and the removal note."""
    prior = _load_prior_relevant(scored) if scored.is_file() else []
    kept = [p for p in prior if p.id not in gone]
    note = skipped or f"{len(prior) - len(kept)} removed as dropped on re-screen"
    return _union_by_id(kept, rel), f"; {note}"


def _flag_counts(data: dict) -> str:
    """The workflow's location/tenure flag totals for the summary; "" for a policy not evaluated."""
    flagged = ""
    if (loc := data.get("locationFlaggedCount")) is not None:
        flagged += f", {loc} location-flagged"
    if (ten := data.get("tenureFlaggedCount")) is not None:
        flagged += f", {ten} tenure-flagged"
    return flagged


def _unmatched_note(unmatched: list[ScoredItem]) -> str:
    """Name the rows no batch record matched (not stored), so the owner can look them up."""
    if not unmatched:
        return ""
    rows = "; ".join(f"{j.id} {j.title} @ {j.company}" for j in unmatched)
    return f"; {len(unmatched)} unmatched, not stored: {rows}"


def _normalize(rel: list[ScoredItem], stamp: str) -> None:
    """Canonicalize each URL and stamp the pull it was scored against (#346), when known."""
    for j in rel:
        j.url = canonical_url(j.url)
        if stamp:
            j.scored_against = stamp


def _route_lanes(rel: list[ScoredItem], valid: set[str]) -> tuple[int, int]:
    """Blank a hallucinated best_lane (routes to unsorted/) and tally unlaned/invalid counts."""
    unlaned = sum(1 for j in rel if not j.best_lane)
    invalid = 0
    for j in rel:
        if j.best_lane and j.best_lane not in valid:
            j.best_lane = ""
            invalid += 1
    return unlaned, invalid


def main(src: Path | None = None, *, merge: bool = False) -> None:
    """Write scored artifacts to results/; src defaults to sys.argv[1] when called directly.

    A ``best_lane`` not in :func:`ajoa_kit.ingest.load_lanes` is blanked (routed to ``unsorted/`` —
    never a junk ``results/<bogus>/`` dir) and tallied (#195). With ``merge`` (the #226 incremental
    re-screen), the scored delta is unioned by id into the existing per-lane buckets and
    ``jobs-scored.json`` ``relevant`` rather than overwriting them; a stored row the re-screen read
    but did not keep is removed, as a fresh screen would drop it (#515, see :func:`_dropped_ids`).

    Every row is first matched to the batch record it was screened from (:func:`match_batches`,
    #513); unmatched rows are reported, not stored, and a result that matches none fails loud.
    """
    if src is None:
        src = Path(sys.argv[1])
    settings = AppSettings()
    results = settings.results_dir
    data = load_result(src)
    rel, dropped = parse_relevant(data)  # parse-on-read: fail loud on a non-result; drop bad items
    batches = load_batches(results)
    rel, unmatched = match_batches(rel, [r for recs in batches.values() for r in recs])
    if unmatched and not rel:
        msg = "the result matched no record in results/batches; re-chunked after the screen?"
        raise ValueError(msg)
    _normalize(rel, pull_date(results))
    valid = {lane.key for lane in load_lanes(settings.config_dir)}
    unlaned, invalid = _route_lanes(rel, valid)
    gone, skipped = _dropped_ids(data, batches, rel, len(unmatched))
    scored = results / "jobs-scored.json"
    merged, removal = _merge_scored(scored, rel, gone, skipped) if merge else (rel, "")
    data["relevant"] = [m.model_dump() for m in merged]
    scored.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    if merge:
        by_lane = merge_shortlists(rel, results, drop=frozenset(gone))
    else:
        by_lane = write_shortlists(rel, results)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(by_lane.items()))
    print(
        f"persisted {len(rel)} JDs -> results/jobs-scored.json; per-lane: {summary} "
        f"(dropped {dropped} malformed, {unlaned} un-laned, {invalid} invalid-lane"
        f"{_flag_counts(data)}){_unmatched_note(unmatched)}{removal}"
    )


if __name__ == "__main__":
    main()
