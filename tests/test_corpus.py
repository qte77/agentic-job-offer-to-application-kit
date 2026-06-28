"""Value-add tests for the four-state corpus merge (``corpus.merge_corpus``, #164).

Cover the sharp edges: each of the four merge states (new / changed / unchanged / delisted), that
``content_hash`` keys on JD content (not tracking churn like url/posted_at), and that ``first_seen``
is preserved while ``last_seen`` advances — the dates the daily ingest relies on.
"""

from __future__ import annotations

from ajoa_kit import corpus


def _jd(
    jid: str,
    *,
    title: str = "Engineer",
    location: str = "Remote",
    desc: str = "Build things",
    url: str = "https://example.com/j/1",
    company: str = "Acme",
) -> dict:
    return {
        "id": jid,
        "company": company,
        "title": title,
        "location": location,
        "description": desc,
        "url": url,
    }


def test_content_hash_keys_on_content_not_tracking_fields() -> None:
    base = _jd("a", url="https://example.com/j/1?utm_source=x")
    same_content = _jd("a", url="https://example.com/j/2")
    assert corpus.content_hash(base) == corpus.content_hash(same_content)
    assert corpus.content_hash(base) != corpus.content_hash(_jd("a", desc="Different work"))


def test_new_records_are_stamped_with_today() -> None:
    merged = corpus.merge_corpus(prior=[], fresh=[_jd("a")], today="2026-06-27")
    assert len(merged) == 1
    rec = merged[0]
    assert rec["first_seen"] == "2026-06-27"
    assert rec["last_seen"] == "2026-06-27"
    assert rec["content_hash"] == corpus.content_hash(_jd("a"))


def test_unchanged_record_refreshes_last_seen_keeps_first_seen() -> None:
    prior = corpus.merge_corpus(prior=[], fresh=[_jd("a")], today="2026-06-01")
    merged = corpus.merge_corpus(prior=prior, fresh=[_jd("a")], today="2026-06-27")
    rec = next(r for r in merged if r["id"] == "a")
    assert rec["first_seen"] == "2026-06-01"  # preserved
    assert rec["last_seen"] == "2026-06-27"  # advanced


def test_changed_record_adopts_content_keeps_first_seen_advances_last_seen() -> None:
    prior = corpus.merge_corpus(prior=[], fresh=[_jd("a", desc="old")], today="2026-06-01")
    merged = corpus.merge_corpus(prior=prior, fresh=[_jd("a", desc="new")], today="2026-06-27")
    rec = next(r for r in merged if r["id"] == "a")
    assert rec["description"] == "new"
    assert rec["content_hash"] == corpus.content_hash(_jd("a", desc="new"))
    assert rec["first_seen"] == "2026-06-01"
    assert rec["last_seen"] == "2026-06-27"


def test_merge_corpus_output_is_sorted_by_id() -> None:
    # ids arrive out of order (prior delisted "b"; fresh "c","a") -> the merged corpus must be
    # id-sorted so the artifact is deterministic across runs (stable cross-run diffs).
    prior = corpus.merge_corpus(prior=[], fresh=[_jd("b")], today="2026-06-01")
    merged = corpus.merge_corpus(prior=prior, fresh=[_jd("c"), _jd("a")], today="2026-06-27")
    assert [r["id"] for r in merged] == ["a", "b", "c"]


def test_delisted_record_kept_with_frozen_last_seen() -> None:
    prior = corpus.merge_corpus(prior=[], fresh=[_jd("a"), _jd("b")], today="2026-06-01")
    # "b" is absent from today's pull → delisted.
    merged = corpus.merge_corpus(prior=prior, fresh=[_jd("a")], today="2026-06-27")
    by_id = {r["id"]: r for r in merged}
    assert set(by_id) == {"a", "b"}  # delisted record retained
    assert by_id["b"]["last_seen"] == "2026-06-01"  # frozen at last presence
    assert by_id["a"]["last_seen"] == "2026-06-27"


def test_summarize_changes_classifies_all_four_states() -> None:
    # Day 1: a, b, c all new. Day 2: a unchanged, b changed, c delisted (absent from pull), d new.
    day1 = corpus.merge_corpus(
        prior=[], fresh=[_jd("a"), _jd("b", desc="old"), _jd("c")], today="2026-06-01"
    )
    day2 = corpus.merge_corpus(
        prior=day1,
        fresh=[
            _jd("a"),
            _jd("b", desc="new"),
            _jd("d", company="NewCo", title="SRE", url="https://x/d"),
        ],
        today="2026-06-27",
    )
    s = corpus.summarize_changes(prior=day1, merged=day2, today="2026-06-27")
    assert s["date"] == "2026-06-27"
    assert (s["new"], s["changed"], s["unchanged"], s["delisted"]) == (1, 1, 1, 1)
    assert s["active"] == 3  # a (unchanged) + b (changed) + d (new); delisted c is not active
    assert s["new_offers"] == [{"company": "NewCo", "title": "SRE", "url": "https://x/d"}]


def test_summarize_changes_first_run_is_all_new() -> None:
    merged = corpus.merge_corpus(prior=[], fresh=[_jd("a"), _jd("b")], today="2026-06-01")
    s = corpus.summarize_changes(prior=[], merged=merged, today="2026-06-01")
    assert (s["new"], s["changed"], s["unchanged"], s["delisted"], s["active"]) == (2, 0, 0, 0, 2)
    assert len(s["new_offers"]) == 2


def test_render_daily_summary_handles_no_new_offers() -> None:
    md = corpus.render_daily_summary(
        {
            "date": "2026-06-27",
            "new": 0,
            "changed": 2,
            "unchanged": 5,
            "delisted": 1,
            "active": 7,
            "new_offers": [],
        }
    )
    assert "2026-06-27" in md
    assert "No new offers" in md


def test_render_daily_summary_caps_a_long_new_offer_list() -> None:
    offers = [{"company": f"Co{i}", "title": "Eng", "url": f"https://x/{i}"} for i in range(60)]
    md = corpus.render_daily_summary(
        {
            "date": "2026-06-27",
            "new": 60,
            "changed": 0,
            "unchanged": 0,
            "delisted": 0,
            "active": 60,
            "new_offers": offers,
        }
    )
    assert "Co0" in md  # first of the 50 listed
    assert "Co49" in md  # 50th (index 49) listed
    assert "Co50" not in md  # capped at 50
    assert "10 more" in md  # "…and 10 more"
