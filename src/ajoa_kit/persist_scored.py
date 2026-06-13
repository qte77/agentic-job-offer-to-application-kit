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


def write_shortlists(rel: list[dict], results_dir: Path) -> dict[str, int]:
    """Write per-lane shortlist.{json,md}; return the per-lane counts."""
    by_lane: dict[str, list[dict]] = {}
    for j in rel:
        by_lane.setdefault(j.get("best_lane", "unsorted"), []).append(j)
    for lane, items in by_lane.items():
        items.sort(key=lambda x: -(x.get("score") or 0))
        d = results_dir / lane
        d.mkdir(parents=True, exist_ok=True)
        (d / "shortlist.json").write_text(json.dumps(items, indent=2, ensure_ascii=False))
        lines = [f"# {lane} — shortlist ({len(items)})", ""]
        for j in items:
            tag = f"{j.get('score')}/{j.get('verdict')}"
            lines.append(f"- [{tag}] {j.get('title', '')} @ {j.get('company', '')}")
            lines.append(f"  - {j.get('url', '')}")
            lines.append(f"  - {j.get('rationale', '')}")
        (d / "shortlist.md").write_text("\n".join(lines) + "\n")
    return {k: len(v) for k, v in by_lane.items()}


def main(src: Path | None = None) -> None:
    """Write scored artifacts to results/; src defaults to sys.argv[1] when called directly."""
    if src is None:
        src = Path(sys.argv[1])
    settings = AppSettings()
    results = settings.results_dir
    data = load_result(src)
    rel = data.get("relevant", [])
    for j in rel:
        j["url"] = canonical_url(j.get("url", ""))
    results.mkdir(parents=True, exist_ok=True)
    (results / "jobs-scored.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    by_lane = write_shortlists(rel, results_dir=results)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(by_lane.items()))
    print(f"persisted {len(rel)} JDs -> results/jobs-scored.json; per-lane: {summary}")


if __name__ == "__main__":
    main()
