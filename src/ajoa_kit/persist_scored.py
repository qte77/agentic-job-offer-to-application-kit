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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import ValidationError

from ajoa_kit.models import ScoredItem
from ajoa_kit.settings import AppSettings

_TRACKING = {"gclid", "fbclid", "mc_cid", "mc_eid", "igshid", "ref_src"}


def canonical_url(url: str) -> str:
    """Drop tracking query params (utm_*, gclid, ...) for clean clickthrough URLs.

    Duplicated from ``ingest`` by design (two stable call sites; AHA — not extracted to a
    shared module until a third consumer appears).
    """
    if not url:
        return url
    s = urlsplit(url)
    if not s.query:
        return url
    kept = [
        (k, v)
        for k, v in parse_qsl(s.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING
    ]
    return urlunsplit((s.scheme, s.netloc, s.path, urlencode(kept), s.fragment))


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


def parse_relevant(data: dict) -> tuple[list[dict], int]:
    """Parse-on-read the relevance result: fail loud if it isn't one; drop + count malformed items.

    JS validates each item at the ``agent()`` boundary, but that guarantee is lost when Python reads
    the file back (a human passes the path — hand-edited / truncated / wrong). Re-validating
    here stops a junk result writing junk artifacts: a structurally-wrong file fails loud; a single
    malformed item is dropped (not fatal).
    """
    if not isinstance(data.get("relevant"), list):
        msg = "no 'relevant' array — is this a cc-workflow-relevance.js result?"
        raise ValueError(msg)  # noqa: TRY004 — malformed data shape, not a wrong-typed arg
    kept: list[dict] = []
    dropped = 0
    for raw in data["relevant"]:
        try:
            kept.append(ScoredItem.model_validate(raw).model_dump())
        except ValidationError:
            dropped += 1
    return kept, dropped


def write_lane(lane: str, items: list[dict], results_dir: Path) -> None:
    """Write one lane's ``shortlist.{json,md}`` — score desc, stale rows (#214) sunk last + tagged.

    Shared by :func:`write_shortlists` (fresh persist) and the refresh sweep
    (:mod:`ajoa_kit.refresh`); fresh items carry no ``stale`` flag, so the order matches the prior
    score-only sort.
    """
    items = sorted(items, key=lambda x: (bool(x.get("stale")), -(x.get("score") or 0)))
    d = results_dir / lane
    d.mkdir(parents=True, exist_ok=True)
    (d / "shortlist.json").write_text(json.dumps(items, indent=2, ensure_ascii=False))
    lines = [f'---\ntitle: "{lane} — shortlist ({len(items)})"\n---', ""]
    for j in items:
        tag = f"{j.get('score')}/{j.get('verdict')}" + (" · stale" if j.get("stale") else "")
        lines.append(f"- [{tag}] {j.get('title', '')} @ {j.get('company', '')}")
        lines.append(f"  - {j.get('url', '')}")
        lines.append(f"  - {j.get('rationale', '')}")
    (d / "shortlist.md").write_text("\n".join(lines) + "\n")


def write_shortlists(rel: list[dict], results_dir: Path) -> dict[str, int]:
    """Write per-lane shortlist.{json,md}; return the per-lane counts."""
    by_lane: dict[str, list[dict]] = {}
    for j in rel:
        # `or "unsorted"`: an empty/absent best_lane (the LLM left it un-laned) must not become an
        # empty-string directory under results/ — it lands in unsorted/.
        by_lane.setdefault(j.get("best_lane") or "unsorted", []).append(j)
    for lane, items in by_lane.items():
        write_lane(lane, items, results_dir)
    return {k: len(v) for k, v in by_lane.items()}


def _union_by_id(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Union two scored-item lists by ``id`` — existing kept, incoming (re-scored) wins on a tie."""
    by_id = {j.get("id"): j for j in existing}
    for j in incoming:
        by_id[j.get("id")] = j
    return list(by_id.values())


def merge_shortlists(rel: list[dict], results_dir: Path) -> dict[str, int]:
    """Union ``rel`` by id into each existing per-lane bucket, then rewrite it (#226 ``--merge``).

    Only lanes present in ``rel`` are touched — a lane absent from this delta is left as-is. Groups
    by ``best_lane`` with the same ``or "unsorted"`` routing as :func:`write_shortlists`, reads the
    existing ``results/<lane>/shortlist.json`` (empty if new), and reuses :func:`write_lane`.
    """
    by_lane: dict[str, list[dict]] = {}
    for j in rel:
        by_lane.setdefault(j.get("best_lane") or "unsorted", []).append(j)
    counts: dict[str, int] = {}
    for lane, incoming in by_lane.items():
        path = results_dir / lane / "shortlist.json"
        existing = json.loads(path.read_text()) if path.is_file() else []
        merged = _union_by_id(existing, incoming)
        write_lane(lane, merged, results_dir)
        counts[lane] = len(merged)
    return counts


def main(src: Path | None = None, *, merge: bool = False) -> None:
    """Write scored artifacts to results/; src defaults to sys.argv[1] when called directly.

    With ``merge`` (the #226 incremental re-screen), the scored delta is unioned by id into the
    existing per-lane buckets and ``jobs-scored.json`` ``relevant`` rather than overwriting them.
    """
    if src is None:
        src = Path(sys.argv[1])
    settings = AppSettings()
    results = settings.results_dir
    data = load_result(src)
    rel, dropped = parse_relevant(data)  # parse-on-read: fail loud on a non-result; drop bad items
    for j in rel:
        j["url"] = canonical_url(j.get("url", ""))
    results.mkdir(parents=True, exist_ok=True)
    scored = results / "jobs-scored.json"
    if merge and scored.is_file():
        prior_rel = json.loads(scored.read_text()).get("relevant", [])
        data["relevant"] = _union_by_id(prior_rel, rel)
    else:
        data["relevant"] = rel
    scored.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    by_lane = merge_shortlists(rel, results) if merge else write_shortlists(rel, results)
    unlaned = sum(1 for j in rel if not j.get("best_lane"))
    summary = ", ".join(f"{k}={v}" for k, v in sorted(by_lane.items()))
    print(
        f"persisted {len(rel)} JDs -> results/jobs-scored.json; per-lane: {summary} "
        f"(dropped {dropped} malformed, {unlaned} un-laned)"
    )


if __name__ == "__main__":
    main()
