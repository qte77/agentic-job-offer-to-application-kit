"""Value-add tests for the startup-discovery layer (``discover``, #292).

Pin the pure extraction/normalization/signal edges and the local-only boundary: a company
name must land in ``results/`` and never in the published ``public-data/`` path.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import discover
from ajoa_kit.discover import emerging_signal, extract_companies, normalize_company

if TYPE_CHECKING:
    from pathlib import Path


def test_normalize_company_strips_legal_suffixes_and_casefolds() -> None:
    assert normalize_company("Acme, Inc.") == "acme"
    assert normalize_company("Acme Corp") == "acme"
    assert normalize_company("Foo Bar GmbH") == "foo bar"
    assert normalize_company("  Spaced   Out   Ltd. ") == "spaced out"
    assert normalize_company("Plain") == "plain"
    assert normalize_company("") == ""


def test_normalize_company_merges_surface_variants_to_one_key() -> None:
    # the whole point of the normalizer: a discovery name and a corpus name join on one key
    assert (
        normalize_company("Stripe, Inc.")
        == normalize_company("STRIPE")
        == normalize_company("Stripe")
    )


def test_extract_companies_yc_oss_keeps_named_companies_only() -> None:
    payload = [
        {"name": "Acme", "batch": "Winter 2012", "isHiring": True},
        {"name": "  ", "batch": "X"},  # blank name -> skipped
        {"batch": "Y", "isHiring": True},  # no name -> skipped
        "not-a-dict",  # skipped
    ]
    out = extract_companies(payload, "yc-oss")
    assert out == [{"name": "Acme", "batch": "Winter 2012", "hiring": True}]


def test_extract_companies_unknown_format_raises() -> None:
    with pytest.raises(ValueError, match="format"):
        extract_companies([], "not-a-source")


def test_emerging_signal_joins_corpus_and_carries_batch_and_hiring() -> None:
    by_source = {
        "yc-oss": [
            {"name": "Acme Inc", "batch": "Summer 2026", "hiring": True},
            {"name": "Bolt", "batch": "Winter 2012", "hiring": False},
        ]
    }
    signal = emerging_signal(by_source, corpus=["Acme", "Zeta"])
    assert signal["acme"]["in_corpus"] is True  # "Acme" is in the corpus
    assert signal["acme"]["hiring"] is True
    assert signal["acme"]["batch"] == "Summer 2026"
    assert signal["acme"]["sources"] == ["yc-oss"]
    assert signal["bolt"]["in_corpus"] is False  # discovered but not yet in the pipeline


def test_emerging_signal_dedups_one_company_across_sources() -> None:
    by_source = {
        "b-src": [{"name": "Acme", "batch": None, "hiring": False}],
        "a-src": [{"name": "Acme, Inc.", "batch": "Summer 2026", "hiring": True}],
    }
    signal = emerging_signal(by_source, corpus=[])
    assert list(signal) == ["acme"]  # one merged entry
    assert signal["acme"]["sources"] == ["a-src", "b-src"]  # sorted union
    assert signal["acme"]["hiring"] is True  # OR across sources
    assert signal["acme"]["batch"] == "Summer 2026"  # a source's batch fills the blank


def test_main_writes_local_only_never_a_public_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, results, public = tmp_path / "config", tmp_path / "results", tmp_path / "public"
    config.mkdir()
    (config / "seed.json").write_text(
        json.dumps({"discovery": [{"name": "yc-oss", "format": "yc-oss", "url": "https://x/api"}]})
    )
    monkeypatch.setenv("AJOA_CONFIG_DIR", str(config))
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    monkeypatch.setenv("AJOA_PUBLIC_DATA_DIR", str(public))
    monkeypatch.setattr(
        "ajoa_kit.sources.get_json",
        lambda url: ([{"name": "SecretCo", "batch": "Summer 2026", "isHiring": True}], "stub"),
    )

    discover.main()

    out = results / "emerging-companies.json"
    assert out.is_file()
    assert "secretco" in json.loads(out.read_text())["companies"]
    # the business-data boundary: nothing — and certainly no company name — under the published dir
    leaked = [p for p in public.rglob("*") if p.is_file()] if public.exists() else []
    assert leaked == []
