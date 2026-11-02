"""Collect headless relevance runs from their Claude Code workflow journals (#342).

``scripts/relevance_headless.sh`` runs ``cc-workflow-relevance.js`` as detached ``claude -p``
slices, each started with ``--session-id <uuid>`` and that id written to a sessions file BEFORE
launch, so a slice that dies (container stop, ``-p`` wait limit) is still found. Claude Code
appends one line per workflow agent event to
``~/.claude/projects/<cwd-slug>/<session>/subagents/workflows/<runId>/journal.jsonl``: a
``started`` line with the agent's ``label`` (``batch-NNN``), then ``result`` or ``failed``.

The journal is the one source that survives every outcome: a completed run, a run stopped by the
``-p`` background wait limit, and a container that died mid-run all leave their finished batches
there. The script's own return value is a plain concatenation of the per-batch ``relevant`` arrays,
so nothing is lost by reading batches instead. The journal format is not in the public docs
(observed with Claude Code 2.1.316); entries are parsed into models so a format change fails loud.

Run::

    make relevance_collect  # collect-relevance <sessions.txt> --out <file>, then persist
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ajoa_kit.models import ScoredItem  # noqa: TC001 -- pydantic resolves field types at runtime
from ajoa_kit.persist_scored import parse_relevant
from ajoa_kit.settings import AppSettings

BATCH_LABEL = re.compile(r"batch-(\d+)$")
SESSION_ID = re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")


class JournalEntry(BaseModel):
    """One workflow journal line (``launched``, then ``started`` / ``result`` / ``failed``)."""

    model_config = ConfigDict(extra="ignore")
    type: str
    key: str = ""  # absent on the run's opening ``launched`` line
    label: str = ""
    result: dict | None = None


class Collected(BaseModel):
    """Every JD the collected runs kept (one row per id) and the batch numbers that finished."""

    relevant: list[ScoredItem]
    done: set[int]


def cwd_slug(cwd: str | Path) -> str:
    """Claude Code's per-project folder name: the absolute cwd, non-alphanumerics as ``-``."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


def default_projects_dir(cwd: Path | None = None) -> Path:
    """``~/.claude/projects/<cwd-slug>`` for ``cwd`` (default: the current directory)."""
    return Path.home() / ".claude" / "projects" / cwd_slug((cwd or Path.cwd()).resolve())


def read_sessions(path: Path) -> list[str]:
    """Session ids from a sessions file: one UUID per line; blanks and ``#`` comments skipped."""
    ids = [line.split("#")[0].strip() for line in path.read_text().splitlines()]
    ids = [i for i in ids if i]
    bad = [i for i in ids if not SESSION_ID.fullmatch(i)]
    if bad or not ids:
        msg = f"{path}: expected one session UUID per line, got {bad or 'none'}"
        raise ValueError(msg)
    return ids


def _journal_results(journal: Path) -> list[tuple[int, list[ScoredItem]]]:
    """``(batch number, kept rows)`` for every finished batch agent in one journal."""
    labels: dict[str, str] = {}
    out: list[tuple[int, list[ScoredItem]]] = []
    for line in journal.read_text().splitlines():
        entry = JournalEntry.model_validate_json(line)
        if entry.type == "started":
            labels[entry.key] = entry.label
            continue
        match = BATCH_LABEL.match(labels.get(entry.key, ""))
        if entry.type == "result" and entry.result is not None and match:
            rows, _ = parse_relevant(entry.result)
            out.append((int(match.group(1)), rows))
    return out


def collect(sessions: list[str], projects: Path) -> Collected:
    """Gather finished batches across sessions; a JD seen twice keeps its higher-scored row."""
    journals = [
        journal
        for sid in sessions
        for journal in sorted((projects / sid).glob("subagents/workflows/*/journal.jsonl"))
    ]
    batches = [result for journal in journals for result in _journal_results(journal)]
    by_id: dict[str, ScoredItem] = {}
    for row in (row for _, rows in batches for row in rows):
        old = by_id.get(row.id)
        if old is None or (row.score or 0) > (old.score or 0):
            by_id[row.id] = row
    return Collected(relevant=list(by_id.values()), done={batch for batch, _ in batches})


def missing_ranges(done: set[int], batch_count: int) -> list[tuple[int, int]]:
    """Unfinished batches as ``(start, limit)`` runs, the form ``RANGES`` takes for a re-run."""
    ranges: list[tuple[int, int]] = []
    for batch in range(batch_count):
        if batch in done:
            continue
        if ranges and sum(ranges[-1]) == batch:
            ranges[-1] = (ranges[-1][0], ranges[-1][1] + 1)
        else:
            ranges.append((batch, 1))
    return ranges


def main(
    sessions_file: Path,
    *,
    out: Path,
    projects: Path | None = None,
    batch_count: int | None = None,
) -> int:
    """Write ``{"relevant": [...]}`` to ``out``; return 1 and print re-run ranges if batches miss.

    Args:
        sessions_file: The slices' session ids, one per line (written by the headless script).
        out: Where to write the combined result (feed it to ``ajoa-kit persist --merge``).
        projects: The Claude Code project folder (default: derived from the current directory).
        batch_count: Batches in the screened set (default: ``results/batches/manifest.json``).
    """
    got = collect(read_sessions(sessions_file), projects or default_projects_dir())
    if batch_count is None:
        manifest = AppSettings().results_dir / "batches" / "manifest.json"
        batch_count = int(json.loads(manifest.read_text())["batch_count"])
    out.write_text(json.dumps({"relevant": [r.model_dump() for r in got.relevant]}))
    print(f"{len(got.done)}/{batch_count} batches done, {len(got.relevant)} JDs kept -> {out}")
    gaps = missing_ranges(got.done, batch_count)
    if gaps:
        print("missing batches; re-run with:")
        print(f'  make relevance_headless RANGES="{" ".join(f"{s}:{n}" for s, n in gaps)}"')
        return 1
    return 0
