"""Probe candidate company slugs across ATS platforms; report which return live jobs.

Discovery helper for ``config/seed.json`` — instead of guessing one ATS per company, try
each candidate slug against Greenhouse / Ashby / Lever / Recruitee and print every hit
with its open-role count. Copy the winners into ``config/seed.json``.

Candidates are read from ``config/seed-candidates.json``. Run via polyfetch's env::

    uv run --directory "$POLYFETCH_DIR" python "$KIT_ROOT/src/ajoa_kit/slug_probe.py"
"""

from __future__ import annotations

import json

from ajoa_kit.settings import AppSettings

PROBE_TIMEOUT = 8.0


def _count(url: str, key: str | None) -> int | None:
    """GET ``url``; return the item count, or None if it is not a live board."""
    # lazy: keep this module importable without polyfetch
    from polyfetch_scrape import fetch  # pyright: ignore[reportMissingImports]

    try:
        r = fetch(url, headers={"Accept": "application/json"}, timeout=PROBE_TIMEOUT)
    except Exception:  # a dead/blocked board is just "not a hit"
        return None
    if r.status != 200:
        return None
    try:
        data = json.loads(r.body)
    except json.JSONDecodeError:
        return None
    if key is None:  # Lever returns a bare array
        return len(data) if isinstance(data, list) else None
    return len(data.get(key, [])) if isinstance(data, dict) else None


PROBES = {
    "greenhouse": lambda s: _count(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs", "jobs"),
    "ashby": lambda s: _count(f"https://api.ashbyhq.com/posting-api/job-board/{s}", "jobs"),
    "lever": lambda s: _count(f"https://api.lever.co/v0/postings/{s}?mode=json", None),
    "recruitee": lambda s: _count(f"https://{s}.recruitee.com/api/offers/", "offers"),
}


def load_candidates() -> list[str]:
    """Load candidate slugs from ``config/seed-candidates.json``; fail loud if missing."""
    path = AppSettings().config_dir / "seed-candidates.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing {path} — create it (key: candidates; see README)",
        )
    return json.loads(path.read_text()).get("candidates", [])


def main() -> None:
    """Probe every configured candidate slug and print live boards with role counts."""
    candidates = load_candidates()
    hits = 0
    for s in candidates:
        found = [(ats, n) for ats, fn in PROBES.items() if (n := fn(s)) is not None and n > 0]
        if found:
            hits += 1
            print(f"{s:16} -> " + ", ".join(f"{a}:{n}" for a, n in found))
        else:
            print(f"{s:16} -> (none)")
    print(f"\n{hits}/{len(candidates)} candidates have a live board")


if __name__ == "__main__":
    main()
