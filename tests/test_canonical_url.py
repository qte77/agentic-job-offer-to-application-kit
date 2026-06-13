"""Value-add tests for canonical_url tracking-param stripping."""

from __future__ import annotations

from ajoa_kit.ingest import canonical_url


def test_drops_tracking_keeps_meaningful() -> None:
    assert canonical_url("https://x.co/j?utm_source=li&id=5") == "https://x.co/j?id=5"
    assert canonical_url("https://x.co/j?gclid=abc&keep=1") == "https://x.co/j?keep=1"


def test_no_query_is_untouched() -> None:
    assert canonical_url("https://x.co/j") == "https://x.co/j"


def test_all_tracking_yields_clean_url() -> None:
    assert canonical_url("https://x.co/j?utm_a=1&gclid=2") == "https://x.co/j"
