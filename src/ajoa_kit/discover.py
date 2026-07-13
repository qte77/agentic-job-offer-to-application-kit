"""Curated startup-discovery layer (#292): read a public source, derive a company-hiring signal.

Reads one OK-tier public source, extracts company names, and derives an emerging / who's-hiring
signal joined to the local JD corpus.

**Aggregate-only + local-only.** The output names companies (business data), so it is written to
``results/emerging-companies.json`` and NEVER published — the ``make trends_data`` boundary guard
would refuse it on the ``data`` branch anyway. Reads public no-auth GETs only; the phase-1 source is
the yc-oss community mirror of YC's public directory, tiered OK-for-aggregate per ADR-0004.

Personal-tool utility, not a differentiator (2026-07-12 distillation) — kept deliberately small.

Pure extraction/normalization/signal is unit-tested; the network + I/O glue lazy-imports polyfetch
via :func:`ajoa_kit.sources.get_json`, so this module stays importable offline.

Run::

    ajoa-kit discover
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

# Trailing legal-entity designator stripped when canonicalizing a name, so "Acme, Inc." and "Acme"
# collapse to one key. Applied repeatedly for a compound tail ("Foo GmbH & Co. KG" → "Foo GmbH").
# Deliberately excludes brand-meaningful words ("Co", "Company", "Holdings") — stripping those would
# over-merge genuinely distinct companies ("The Honest Company" is not "The Honest").
_SUFFIX = re.compile(
    r"[\s,]+(?:inc|incorporated|llc|ltd|limited|corp|corporation|"
    r"gmbh|ag|plc|sa|srl|bv|oy|ab|as|pty|llp)\.?$",
    re.IGNORECASE,
)
_TOP_UNTRACKED = 15  # how many "hiring, not yet in your corpus" companies `discover` prints


def normalize_company(name: str) -> str:
    """Canonical join key for a company name (suffix-stripped, whitespace-collapsed, casefolded).

    Strips a trailing legal suffix and casefolds so ``"Acme, Inc."`` and ``"Acme"`` collapse to one
    key; blank/``None`` yields ``""``. A deterministic normalizer (analogue of
    :func:`ajoa_kit.companies.parse_geo`) so the same company from a discovery source and from the
    JD corpus lands on one key.

    Args:
        name: A raw company name from a source or the corpus.

    Returns:
        The canonical, casefolded key (``""`` when nothing name-worthy remains).
    """
    text = " ".join((name or "").split())
    prev = None
    while prev != text:
        prev = text
        text = _SUFFIX.sub("", text).strip(" ,.")
    return text.casefold()


def _batch_year(batch: str | None) -> int:
    """The 4-digit year in a YC batch label (``"Summer 2026" -> 2026``); ``0`` when there is none.

    Used to rank discovered companies most-recent-batch-first (recent batch == emerging).
    """
    match = re.search(r"(\d{4})\s*$", batch or "")
    return int(match.group(1)) if match else 0


def extract_companies(payload: object, fmt: str) -> list[dict]:
    """Extract minimal ``{name, batch, hiring}`` records from a discovery source payload.

    Args:
        payload: The parsed source response.
        fmt: The source-format key selecting the parser (only ``"yc-oss"`` in phase 1).

    Returns:
        One record per named company, in source order.

    Raises:
        ValueError: For an unknown ``fmt``.
    """
    if fmt == "yc-oss":
        return _extract_yc_oss(payload)
    raise ValueError(f"unknown discovery source format: {fmt!r}")


def _extract_yc_oss(payload: object) -> list[dict]:
    """Parse a yc-oss ``companies/*.json`` array (name / batch / isHiring per object)."""
    rows = payload if isinstance(payload, list) else []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        batch = row.get("batch")
        out.append(
            {
                "name": name.strip(),
                "batch": batch if isinstance(batch, str) else None,
                "hiring": bool(row.get("isHiring")),
            }
        )
    return out


def _merge_record(signal: dict[str, dict], source: str, rec: dict, corpus_keys: set[str]) -> None:
    """Fold one extracted record into ``signal`` under its normalized key (in place)."""
    key = normalize_company(rec.get("name", ""))
    if not key:
        return
    entry = signal.get(key)
    if entry is None:
        entry = {
            "name": rec.get("name", ""),
            "sources": [],
            "batch": rec.get("batch"),
            "hiring": False,
            "in_corpus": key in corpus_keys,
        }
        signal[key] = entry
    if source not in entry["sources"]:
        entry["sources"].append(source)
    entry["hiring"] = entry["hiring"] or bool(rec.get("hiring"))
    if not entry["batch"] and rec.get("batch"):
        entry["batch"] = rec.get("batch")


def emerging_signal(
    names_by_source: dict[str, list[dict]], corpus: Iterable[str]
) -> dict[str, dict]:
    """Aggregate discovered companies into a per-company signal, joined to the corpus.

    Args:
        names_by_source: ``{source_name: [records from extract_companies]}``.
        corpus: Company-name strings from the local JD corpus (the grounding join).

    Returns:
        ``{normalized_company: {name, sources, batch, hiring, in_corpus}}`` — ``in_corpus`` is True
        when the company already appears in the corpus; ``batch`` conveys emergence (recent batch).
        Deterministic: sources are sorted and there is one entry per normalized name.
    """
    corpus_keys = {normalize_company(c) for c in corpus if isinstance(c, str)}
    corpus_keys.discard("")
    signal: dict[str, dict] = {}
    for source, records in names_by_source.items():
        for rec in records:
            if isinstance(rec, dict):
                _merge_record(signal, source, rec, corpus_keys)
    for entry in signal.values():
        entry["sources"].sort()
    return signal


def _load_discovery_sources(config_dir: Path) -> list[dict]:
    """Read the seed's ``discovery`` array (``config/seed.json`` else ``default-seed.json``)."""
    path = config_dir / "seed.json"
    if not path.is_file():
        path = config_dir / "default-seed.json"
    cfg = json.loads(path.read_text())
    return cfg.get("discovery", [])


def _corpus_companies(results_dir: Path) -> list[str]:
    """Company names from the local JD corpus (``results/corpus.json``); ``[]`` when absent."""
    path = results_dir / "corpus.json"
    if not path.is_file():
        return []
    jobs = json.loads(path.read_text())
    return [j.get("company", "") for j in jobs if isinstance(j, dict)]


def _fetch_sources(sources: list[dict]) -> dict[str, list[dict]]:
    """Fetch each discovery source (lazy polyfetch via ``sources.get_json``) -> extracted records.

    Warn-and-continue on any source error, mirroring ingest — one bad source never aborts the run.
    """
    from ajoa_kit.sources import get_json  # lazy: keeps discover importable offline

    out: dict[str, list[dict]] = {}
    for src in sources:
        name = src.get("name", "?")
        try:
            payload, _backend = get_json(src["url"])
            out[name] = extract_companies(payload, src.get("format", ""))
        except Exception as e:  # warn-and-continue: one bad source must not abort the whole run
            print(f"discover: skipping {name}: {type(e).__name__}: {e}")
    return out


def main() -> None:
    """Fetch the discovery source(s), derive the signal, write results/emerging-companies.json.

    Joins the emerging/hiring signal to the local corpus and writes local business data (never
    published).
    """
    settings = AppSettings()
    sources = _load_discovery_sources(settings.config_dir)
    if not sources:
        print("no 'discovery' sources in the seed — nothing to do")
        return
    signal = emerging_signal(_fetch_sources(sources), _corpus_companies(settings.results_dir))
    out_path = settings.results_dir / "emerging-companies.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"companies": signal}, indent=2, ensure_ascii=False))
    hiring = sum(1 for v in signal.values() if v["hiring"])
    in_corpus = sum(1 for v in signal.values() if v["in_corpus"])
    print(
        f"discover: {len(signal)} companies "
        f"({hiring} hiring, {in_corpus} already in corpus) -> {out_path}"
    )
    # Surface the actionable slice: hiring companies NOT in your pipeline, most-recent batch first
    # (recent == emerging). The full ranked set is in the JSON; this is just the eyeball view.
    untracked = sorted(
        (v for v in signal.values() if not v["in_corpus"]),
        key=lambda v: (-_batch_year(v["batch"]), v["name"].casefold()),
    )
    if untracked:
        shown = untracked[:_TOP_UNTRACKED]
        print(f"  emerging/hiring not yet in your corpus (top {len(shown)} of {len(untracked)}):")
        for v in shown:
            print(f"    - {v['name']}  ({v['batch'] or '?'})")


if __name__ == "__main__":
    main()
