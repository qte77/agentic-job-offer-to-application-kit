"""Re-probe the source registry and stamp ``_date_verified`` on live feeds/ats entries (#217).

The shipped ``config/default-seed.json`` lists ``feeds`` (RSS/Atom URLs) and ``ats`` boards (a
``slug`` + ATS platform). Over time slugs rot silently — boards move, companies get acquired → 404
/ empty. ``verify-sources`` GETs each source read-only (no auth, no body) and stamps
``_date_verified`` with today on the ones that answer, leaving the rest for a human to triage (a
normal ``ingest`` run already lists dead sources under "Failed"). Run via polyfetch's env::

    ajoa-kit verify-sources [--dry-run]

Two probe shapes, both "live → truthy / dead-or-unreachable → ``None``":

- ``feeds`` are probed by their ``url`` via :func:`ajoa_kit.slug_probe.fetch_status`, which returns
  the HTTP status — so a feed is live only on a 2xx/3xx (a 404 is not-``None`` but dead).
- ``ats`` boards are probed by ``(ats, slug)`` via :data:`ajoa_kit.slug_probe.PROBES` (Greenhouse /
  Ashby / Lever / Recruitee), which returns a role count or ``None``; a count (even ``0`` for a live
  but empty board) means live. Platforms outside ``PROBES`` (e.g. the single Personio board) aren't
  count-probeable and are reported as unconfirmed for manual review.

The decision core (:func:`reprobe`) takes the probes and ``today`` as arguments, so it is
deterministic and importable without the network — polyfetch is reached lazily via ``slug_probe``
only when :func:`main` binds the real probes. A ``None`` result is inconclusive: the entry is left
untouched and reported, never stamped, so a flaky network never re-dates a source (the #214 refresh
contract).
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _reachable(status: int | None) -> bool:
    """A 2xx/3xx GET means the URL is live; a 4xx/5xx or ``None`` (unreachable) does not."""
    return status is not None and 200 <= status < 400


def reprobe(
    feeds: list[dict],
    ats: list[dict],
    probe_feed: Callable[[str], int | None],
    probe_ats: Callable[[str, str], int | None],
    today: str,
) -> list[dict]:
    """Stamp ``_date_verified = today`` on every live entry (in place); return the unconfirmed ones.

    A feed is live on a reachable (2xx/3xx) GET of its ``url``; an ats board is live when its probe
    returns a role count (not ``None``). An unconfirmed entry (a dead 4xx/5xx feed, or a ``None``
    board / unreachable feed) is left untouched and collected for the caller to report.
    """
    unconfirmed: list[dict] = []
    for feed in feeds:
        if _reachable(probe_feed(feed.get("url", ""))):
            feed["_date_verified"] = today
        else:
            unconfirmed.append(feed)
    for board in ats:
        if probe_ats(board.get("ats", ""), board.get("slug", "")) is not None:
            board["_date_verified"] = today
        else:
            unconfirmed.append(board)
    return unconfirmed


def _resolve_seed(config_dir: Path) -> Path:
    """The seed to re-probe: ``config/seed.json`` if present, else ``default-seed.json``."""
    seed = config_dir / "seed.json"
    return seed if seed.is_file() else config_dir / "default-seed.json"


def _entry_line(line: str, entry: dict) -> str:
    """Re-serialize one entry, preserving the original line's indent, trailing comma and newline."""
    indent = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()) :]  # keep the exact line ending
    comma = "," if line.strip().endswith(",") else ""
    return f"{indent}{json.dumps(entry, ensure_ascii=False)}{comma}{trailing}"


def _opened_section(stripped: str, sections: dict[str, list[dict]]) -> list[dict] | None:
    """The entry list a ``"key": [`` line opens, or ``None`` if it isn't a feeds/ats opener."""
    return next((v for opener, v in sections.items() if stripped.startswith(opener)), None)


def _restamp_seed(original: str, feeds: list[dict], ats: list[dict]) -> str:
    """Rewrite only the one-line ``feeds``/``ats`` entries from the re-stamped lists.

    Every other line stays byte-identical — the ``_comment`` and the intentionally multi-line
    ``aggregators``/``_deferred`` doc blocks (long ToS notes, a nested ``sources`` array) never
    churn. The seed keeps each ``feeds``/``ats`` entry on its own line (``ajoa-kit`` never expands
    them), so re-serializing with default separators reproduces an unchanged entry byte-for-byte and
    only the stamped lines differ. A final parse-back guards against any layout drift corrupting the
    file (it would fail loud rather than write a mangled seed).
    """
    sections = {'"feeds": [': feeds, '"ats": [': ats}
    out: list[str] = []
    current: list[dict] | None = None
    idx = 0
    for line in original.splitlines(keepends=True):
        stripped = line.strip()
        if current is None:
            out.append(line)
            current, idx = _opened_section(stripped, sections), 0
        elif stripped.startswith("]"):
            out.append(line)
            current = None
        else:
            out.append(_entry_line(line, current[idx]))
            idx += 1

    result = "".join(out)
    reparsed = json.loads(result)
    if reparsed.get("feeds") != feeds or reparsed.get("ats") != ats:  # never write a corrupt seed
        raise ValueError("verify-sources: re-stamp would corrupt feeds/ats — aborted")
    return result


def _label(entry: dict) -> str:
    """A human label for the unconfirmed report — a feed ``url`` or an ``ats/slug`` board."""
    return entry.get("url") or f"{entry.get('ats', '?')}/{entry.get('slug', '?')}"


def _live_ats_probe() -> Callable[[str, str], int | None]:
    """The real ats board probe: reuse ``slug_probe.PROBES`` (lazy, so we import offline)."""
    from ajoa_kit.slug_probe import PROBES

    def probe(ats_name: str, slug: str) -> int | None:
        fn = PROBES.get(ats_name)
        return fn(slug) if fn is not None else None

    return probe


def main(
    *,
    dry_run: bool = False,
    today: str | None = None,
    probe_feed: Callable[[str], int | None] | None = None,
    probe_ats: Callable[[str, str], int | None] | None = None,
) -> None:
    """Re-probe the seed, stamp live sources, write it back (unless ``--dry-run``); print a report.

    ``probe_feed`` / ``probe_ats`` default to the live network probes (bound lazily from
    ``slug_probe`` so this module stays importable offline); tests inject fakes.
    """
    today = today or date.today().isoformat()
    if probe_feed is None:
        from ajoa_kit.slug_probe import fetch_status

        probe_feed = fetch_status
    ats_probe = probe_ats or _live_ats_probe()

    seed_path = _resolve_seed(AppSettings().config_dir)
    original = seed_path.read_text()
    cfg = json.loads(original)
    feeds, ats = cfg.get("feeds", []), cfg.get("ats", [])
    total = len(feeds) + len(ats)
    unconfirmed = reprobe(feeds, ats, probe_feed, ats_probe, today)
    if not dry_run:
        seed_path.write_text(_restamp_seed(original, feeds, ats))

    verb = "would stamp" if dry_run else "stamped"
    print(f"{verb} {total - len(unconfirmed)}/{total} live; {len(unconfirmed)} unconfirmed:")
    for entry in unconfirmed:
        print(f"  {_label(entry)}")


if __name__ == "__main__":
    main()
