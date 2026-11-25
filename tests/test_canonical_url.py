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


# --- per-ATS allowlist (#526): with an ATS, keep only the query keys it needs, drop the rest ---


def test_greenhouse_keeps_gh_jid_and_drops_everything_else() -> None:
    url = "https://jobs.example.com/careers/42?gh_jid=42&utm_source=x&planted=1#apply"
    assert canonical_url(url, "greenhouse") == "https://jobs.example.com/careers/42?gh_jid=42"


def test_greenhouse_embedded_board_keeps_board_and_gh_jid() -> None:
    url = "https://example.com/careers/job?4686665006=&board=acme&gh_jid=4686665006"
    assert (
        canonical_url(url, "greenhouse")
        == "https://example.com/careers/job?board=acme&gh_jid=4686665006"
    )


def test_an_ats_without_allowlisted_keys_drops_query_and_fragment() -> None:
    assert canonical_url("https://jobs.example.com/acme/1?id=5&x=y#top", "ashby") == (
        "https://jobs.example.com/acme/1"
    )


def test_without_an_ats_only_tracking_params_go() -> None:
    # Reason: callers that hold no ATS (scored rows) keep the old normalisation, so gh_jid survives
    assert canonical_url("https://x.co/j?gh_jid=7&utm_a=1#f") == "https://x.co/j?gh_jid=7#f"


def test_unparseable_url_is_returned_unchanged() -> None:
    assert canonical_url("http://[broken", "greenhouse") == "http://[broken"
    assert canonical_url("http://[broken") == "http://[broken"


def test_query_addressed_feeds_keep_their_item_keys_and_never_collapse() -> None:
    # Reason: RSS ids embed the link, so two items must keep two canonical urls (#526 review F8)
    a = canonical_url("https://blog.example.com/jobs?p=1&utm_source=x#top", "rss")
    b = canonical_url("https://blog.example.com/jobs?p=2", "rss")
    assert a == "https://blog.example.com/jobs?p=1"
    assert b == "https://blog.example.com/jobs?p=2"
    assert a != b
    assert canonical_url("https://example.com/about#join", "manual") == "https://example.com/about"


_PATH_ATS = {"greenhouse": {"gh_jid", "board"}, "ashby": set(), "lever": set()}


class TestAllowlistProperties:
    @given(u=st.text(), ats=st.sampled_from(["greenhouse", "ashby", "lever", "rss", "manual", ""]))
    @settings(deadline=None)
    def test_idempotent_never_raises_and_keeps_only_allowlisted_keys(
        self, u: str, ats: str
    ) -> None:
        once = canonical_url(u, ats)
        assert canonical_url(once, ats) == once
        try:
            parts = urlsplit(once)
        except ValueError:
            return  # unparseable input comes back unchanged
        keys = {k for k, _ in parse_qsl(parts.query, keep_blank_values=True)}
        if once != u:
            assert parts.fragment == ""
            if ats in _PATH_ATS:
                assert keys <= _PATH_ATS[ats]
            assert not any(k.lower().startswith("utm_") for k in keys)
