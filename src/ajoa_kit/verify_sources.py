"""Re-probe the source registry and stamp ``_date_verified`` on live seed entries (#217).

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

The other two seed sections are covered by the same URL probe: ``discovery`` entries carry a ``url``
like a feed, while ``aggregators`` carry none (one fixed endpoint spans many employers) and are
probed via :data:`ajoa_kit.sources.AGGREGATOR_ENDPOINTS` — the same constant the adapters fetch, so
the endpoint is never duplicated. An aggregator whose ``name`` has no endpoint there is reported,
never probed.

The decision core (:func:`reprobe`) takes the probes and ``today`` as arguments, so it is
deterministic and importable without the network — polyfetch is reached lazily via ``slug_probe``
only when :func:`main` binds the real probes. A ``None`` result is inconclusive: the entry is left
untouched and reported, never stamped, so a flaky network never re-dates a source (the #214 refresh
contract). Stamps are monotonic (see :func:`_stamp`).
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import TYPE_CHECKING

from ajoa_kit.settings import AppSettings
from ajoa_kit.sources import AGGREGATOR_ENDPOINTS

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    _Rewriter = Callable[[str, dict], str]  # (seed line, its re-stamped entry) -> the line to write
    _Section = tuple[list[dict], _Rewriter]  # one seed array plus how its lines are rewritten
    _LiveCheck = tuple[list[dict], Callable[[dict], bool]]  # one seed array plus its liveness test


def _reachable(status: int | None) -> bool:
    """A 2xx/3xx GET means the URL is live; a 4xx/5xx or ``None`` (unreachable) does not."""
    return status is not None and 200 <= status < 400


def _stamp(entry: dict, today: str) -> None:
    """Stamp ``_date_verified = today`` in place, but never move an existing stamp backwards.

    ``_date_verified`` is ISO ``YYYY-MM-DD`` — fixed-width and zero-padded, so plain ``str``
    comparison is exactly chronological order and no date parsing is needed. Monotonic because a
    stamp is a freshness claim: a manual sweep dated 2026-07-28 must not overwrite entries an
    automated probe had already confirmed on 2026-08-01 (it did, once).
    """
    previous = entry.get("_date_verified")
    if isinstance(previous, str) and previous > today:
        return
    entry["_date_verified"] = today


def _url_live(entry: dict, probe_feed: Callable[[str], int | None]) -> bool:
    """A ``url``-carrying entry (a feed or a discovery source) is live on a reachable GET."""
    return _reachable(probe_feed(entry.get("url", "")))


def _aggregator_live(entry: dict, probe_feed: Callable[[str], int | None]) -> bool:
    """An aggregator is live when its fixed endpoint answers; an unmapped ``name`` never is."""
    endpoint = AGGREGATOR_ENDPOINTS.get(entry.get("name", ""))
    return _reachable(probe_feed(endpoint)) if endpoint else False


def _stamp_section(entries: list[dict], is_live: Callable[[dict], bool], today: str) -> list[dict]:
    """Stamp every live entry of one seed section (in place); return the unconfirmed ones."""
    unconfirmed: list[dict] = []
    for entry in entries:
        if is_live(entry):
            _stamp(entry, today)
        else:
            unconfirmed.append(entry)
    return unconfirmed


def reprobe(
    feeds: list[dict],
    ats: list[dict],
    probe_feed: Callable[[str], int | None],
    probe_ats: Callable[[str, str], int | None],
    today: str,
    aggregators: list[dict] | None = None,
    discovery: list[dict] | None = None,
) -> list[dict]:
    """Stamp ``_date_verified = today`` on every live entry (in place); return the unconfirmed ones.

    A feed (and likewise a ``discovery`` source) is live on a reachable (2xx/3xx) GET of its
    ``url``; an ats board is live when its probe returns a role count (not ``None``); an aggregator
    is live when its :data:`ajoa_kit.sources.AGGREGATOR_ENDPOINTS` endpoint is reachable. An
    unconfirmed entry (a dead 4xx/5xx URL, or a ``None`` board / unreachable URL) is left untouched
    and collected for the caller to report. Stamping is monotonic — see :func:`_stamp`.
    """
    checks: tuple[_LiveCheck, ...] = (
        (feeds, lambda e: _url_live(e, probe_feed)),
        (ats, lambda e: probe_ats(e.get("ats", ""), e.get("slug", "")) is not None),
        (aggregators or [], lambda e: _aggregator_live(e, probe_feed)),
        (discovery or [], lambda e: _url_live(e, probe_feed)),
    )
    unconfirmed: list[dict] = []
    for entries, is_live in checks:
        unconfirmed += _stamp_section(entries, is_live, today)
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


_DATE_VALUE = re.compile(r'("_date_verified":\s*)"[^"]*"')


def _stamped_line(line: str, entry: dict) -> str:
    """Re-date one line of a multi-line entry, leaving every other byte of it untouched.

    Only the ``"_date_verified": "…"`` value is substituted — ``aggregators``/``discovery`` entries
    span several lines around a long ``_tos`` prose block, so re-serializing them (as the one-line
    ``feeds``/``ats`` entries are) would reflow that block and churn the whole seed. A line without
    the key comes back unchanged; an entry whose text carries no ``_date_verified`` at all therefore
    cannot be stamped, and :func:`_restamp_seed`'s parse-back guard fails loud rather than write a
    seed that disagrees with the probe result.
    """
    stamp = entry.get("_date_verified")
    if not stamp or not _DATE_VALUE.search(line):
        return line
    return _DATE_VALUE.sub(lambda m: f'{m.group(1)}"{stamp}"', line, count=1)


def _opened_section(stripped: str, sections: dict[str, _Section]) -> _Section | None:
    """The section a ``"key": [`` line opens, or ``None`` if it opens no rewritable section.

    Only a line *ending* in ``[`` opens one: an inline empty array (``"discovery": []``) holds no
    entries to rewrite and must be passed through with the lines that follow it.
    """
    if not stripped.endswith("["):
        return None
    return next((v for opener, v in sections.items() if stripped.startswith(opener)), None)


def _guard_round_trip(result: str, stamped: dict[str, list[dict]]) -> None:
    """Refuse a rewrite that does not parse back to the re-stamped sections.

    Covers all four source sections, so a layout the line walker cannot rewrite (e.g. an
    ``aggregators`` entry with no ``_date_verified`` field for :func:`_stamped_line` to substitute)
    fails loud instead of writing a seed whose text disagrees with the probe result.
    """
    reparsed = json.loads(result)
    if any(reparsed.get(key, []) != value for key, value in stamped.items()):
        raise ValueError(
            "verify-sources: re-stamp would corrupt feeds/ats/aggregators/discovery — aborted "
            "(every entry needs a `_date_verified` field for its stamp to be placed)",
        )


def _restamp_seed(
    original: str,
    feeds: list[dict],
    ats: list[dict],
    aggregators: list[dict],
    discovery: list[dict],
) -> str:
    """Rewrite the re-stamped entries of the four source sections, line by line.

    Every other line stays byte-identical — the ``_comment`` and the ``_blocked``/``_deferred`` doc
    blocks never churn. Two rewrite modes, because the seed's layout differs per section:

    - ``feeds``/``ats`` keep each entry on its own line (``ajoa-kit`` never expands them), so
      re-serializing with default separators reproduces an unchanged entry byte-for-byte via
      :func:`_entry_line` and only the stamped lines differ.
    - ``aggregators``/``discovery`` entries span several lines (a long ``_tos`` note), so
      :func:`_stamped_line` substitutes only the ``_date_verified`` value and never reflows them.

    A line whose stripped form starts with ``{`` opens the next entry of the current section (true
    of every line of a one-line section, and only of the first line of a multi-line entry), which is
    what keeps both modes on the same walk. A final parse-back guards all four sections against
    layout drift corrupting the file (it fails loud rather than write a mangled seed).
    """
    sections: dict[str, _Section] = {
        '"feeds": [': (feeds, _entry_line),
        '"ats": [': (ats, _entry_line),
        '"aggregators": [': (aggregators, _stamped_line),
        '"discovery": [': (discovery, _stamped_line),
    }
    out: list[str] = []
    current: _Section | None = None
    idx = -1
    for line in original.splitlines(keepends=True):
        stripped = line.strip()
        if current is None:
            out.append(line)
            current, idx = _opened_section(stripped, sections), -1
        elif stripped.startswith("]"):
            out.append(line)
            current = None
        else:
            entries, rewrite = current
            idx += 1 if stripped.startswith("{") else 0
            out.append(rewrite(line, entries[idx]))

    result = "".join(out)
    _guard_round_trip(
        result,
        {"feeds": feeds, "ats": ats, "aggregators": aggregators, "discovery": discovery},
    )
    return result


def _label(entry: dict) -> str:
    """A human label for the report — a feed/discovery ``url``, an aggregator ``name``, or a board.

    Aggregators carry neither a ``url`` nor an ``ats``/``slug``, so they fall back to ``name``.
    """
    return (
        entry.get("url") or entry.get("name") or f"{entry.get('ats', '?')}/{entry.get('slug', '?')}"
    )


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

    All four source sections are covered — ``feeds``, ``ats``, ``aggregators`` and ``discovery``.
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
    aggregators, discovery = cfg.get("aggregators", []), cfg.get("discovery", [])
    total = len(feeds) + len(ats) + len(aggregators) + len(discovery)
    unconfirmed = reprobe(feeds, ats, probe_feed, ats_probe, today, aggregators, discovery)
    if not dry_run:
        seed_path.write_text(_restamp_seed(original, feeds, ats, aggregators, discovery))

    verb = "would stamp" if dry_run else "stamped"
    print(f"{verb} {total - len(unconfirmed)}/{total} live; {len(unconfirmed)} unconfirmed:")
    for entry in unconfirmed:
        print(f"  {_label(entry)}")


if __name__ == "__main__":
    main()
