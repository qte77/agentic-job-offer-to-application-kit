"""Value-add tests for canonical_url tracking-param stripping."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit.normalize import canonical_url


def test_drops_tracking_keeps_meaningful() -> None:
    assert canonical_url("https://x.co/j?utm_source=li&id=5") == "https://x.co/j?id=5"
    assert canonical_url("https://x.co/j?gclid=abc&keep=1") == "https://x.co/j?keep=1"


def test_no_query_is_untouched() -> None:
    assert canonical_url("https://x.co/j") == "https://x.co/j"


def test_all_tracking_yields_clean_url() -> None:
    assert canonical_url("https://x.co/j?utm_a=1&gclid=2") == "https://x.co/j"


class TestCanonicalUrlProperties:
    # Reason: pure URL normalizer over arbitrary text; deadline off. (The former persist_scored
    # lockstep assertion is gone — #249 slice C collapsed that duplicate onto this single source.)
    @given(u=st.text())
    @settings(deadline=None)
    def test_idempotent_and_strips_utm(self, u: str) -> None:
        once = canonical_url(u)
        assert canonical_url(once) == once  # idempotent
        keys = [k.lower() for k, _ in parse_qsl(urlsplit(once).query, keep_blank_values=True)]
        assert not any(k.startswith("utm_") for k in keys)  # no tracking params survive
