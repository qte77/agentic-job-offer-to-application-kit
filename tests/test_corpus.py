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
) -> dict:
    return {"id": jid, "title": title, "location": location, "description": desc, "url": url}


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
