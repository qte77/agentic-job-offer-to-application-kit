"""Value-add tests for `chunk --new` incremental delta batching (#226).

`chunk` normally splits the whole `results/jobs-raw.json`; `--new` instead batches only the offers
first seen in the latest ingest pull (`first_seen == max(last_seen)` in `results/corpus.json`), so a
daily re-screen fans relevance out over just the delta. These pin the two behaviours a unit test can
own: the filter keys on `first_seen` (not merely "seen today"), and a missing corpus fails loud.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ajoa_kit import chunk
from ajoa_kit.defaults import DESC_CAP

if TYPE_CHECKING:
    from pathlib import Path


def _rec(jid: str, first: str, last: str) -> dict:
    """A corpus.json record (JD fields + the merge-stamped first_seen/last_seen/content_hash)."""
    return {
        "id": jid,
        "title": f"{jid} role",
        "first_seen": first,
        "last_seen": last,
        "content_hash": jid,
    }


# latest pull date = max(last_seen) = 2026-06-30. `new1`/`new2` are first seen then (the delta);
# `old` is seen in that pull but first seen earlier (must be excluded — proves we key on first_seen,
# not last_seen); `gone` is delisted (last_seen frozen in the past).
CORPUS = [
    _rec("old", "2026-06-01", "2026-06-30"),
    _rec("new1", "2026-06-30", "2026-06-30"),
    _rec("new2", "2026-06-30", "2026-06-30"),
    _rec("gone", "2026-05-01", "2026-06-20"),
]


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    return results


def test_chunk_new_batches_only_the_delta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = _setup(tmp_path, monkeypatch)
    (results / "corpus.json").write_text(json.dumps(CORPUS))
    raw = results / "jobs-raw.json"
    raw.write_text(json.dumps([{"id": "should-not-be-read"}]))  # --new must ignore jobs-raw.json

    chunk.main(batch=40, new=True)

    manifest = json.loads((results / "batches" / "manifest.json").read_text())
    assert manifest["total_jobs"] == 2  # only first_seen == max(last_seen)
    assert manifest["batch_count"] == 1
    batch = json.loads((results / "batches" / "batch-000.json").read_text())
    assert sorted(j["id"] for j in batch) == ["new1", "new2"]  # old + gone excluded
    assert json.loads(raw.read_text()) == [{"id": "should-not-be-read"}]  # jobs-raw.json untouched


def test_chunk_new_fails_loud_without_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(tmp_path, monkeypatch)  # no corpus.json written
    with pytest.raises(FileNotFoundError, match="corpus"):
        chunk.main(batch=40, new=True)


def test_chunk_caps_description_leaving_the_stored_text_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``DESC_CAP`` is a relevance-pass budget, so ``chunk`` applies it — not ingest (#347).

    The batches feed the relevance screen, which is what the cap exists to bound. Ingest keeps the
    whole posting so the tailor pass, which reads ``jobs-raw.json`` directly, is grounded in the
    complete JD. Both halves are asserted here: batch text is capped, stored text is untouched.
    """
    results = _setup(tmp_path, monkeypatch)
    long_desc = "y" * (DESC_CAP + 1000)
    raw = results / "jobs-raw.json"
    raw.write_text(json.dumps([{"id": "a", "title": "role", "description": long_desc}]))

    chunk.main(batch=40)

    batched = json.loads((results / "batches" / "batch-000.json").read_text())
    assert len(batched[0]["description"]) == DESC_CAP  # relevance pass sees the capped slice
    assert batched[0]["description"] == long_desc[:DESC_CAP]  # a prefix, not a re-derived string
    assert json.loads(raw.read_text())[0]["description"] == long_desc  # source stays whole


def test_chunk_new_includes_changed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # #235: --new batches first-seen-new AND content-changed records (both carry last_changed ==
    # the latest pull date); an unchanged record (older last_changed) is skipped.
    results = _setup(tmp_path, monkeypatch)

    def _lc(jid: str, first: str, changed: str) -> dict:
        return {**_rec(jid, first, "2026-06-30"), "last_changed": changed}

    corpus_json = [
        _lc("new1", "2026-06-30", "2026-06-30"),
        _lc("changed1", "2026-06-01", "2026-06-30"),
        _lc("unchanged1", "2026-06-01", "2026-06-01"),
    ]
    (results / "corpus.json").write_text(json.dumps(corpus_json))
    chunk.main(batch=40, new=True)
    batch = json.loads((results / "batches" / "batch-000.json").read_text())
    assert sorted(j["id"] for j in batch) == ["changed1", "new1"]  # unchanged1 skipped


def test_chunk_scopes_description_to_the_substantive_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The relevance screen should see the role, not the employer-branding wrapper (arc-010 item 7).

    87% of the corpus opens with an "About us" blurb (median 809 chars before the first substantive
    marker) and many close with EEO/benefits boilerplate. Neither carries lane signal and both crowd
    the body out from under ``DESC_CAP``. Scoping runs regardless of length: this description sits
    well under the cap, so a cap-gated implementation would leave the preamble in.
    """
    results = _setup(tmp_path, monkeypatch)
    desc = (
        "About us\n\nWe are a category-defining unicorn. " + ("culture " * 40) + "\n\n"
        "Requirements\n\n- 5 years of Python building distributed systems.\n" * 20 + "\n"
        "Benefits\n\nFree snacks, a gym membership and unlimited PTO.\n"
    )
    raw = results / "jobs-raw.json"
    raw.write_text(json.dumps([{"id": "a", "title": "role", "description": desc}]))

    chunk.main(batch=40)

    batched = json.loads((results / "batches" / "batch-000.json").read_text())[0]["description"]
    assert len(desc) < DESC_CAP  # guards the premise: the cap drops nothing here
    assert "5 years of Python" in batched  # the body survives
    assert "About us" not in batched  # employer-branding preamble dropped
    assert "Free snacks" not in batched  # trailing benefits boilerplate dropped
    assert json.loads(raw.read_text())[0]["description"] == desc  # source stays whole


def test_chunk_caps_the_scoped_slice_at_desc_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``DESC_CAP`` stays a hard backstop *after* scoping — never something scoping can overrun."""
    results = _setup(tmp_path, monkeypatch)
    desc = "About us\n\nbranding\n\nResponsibilities\n\n" + ("z" * (DESC_CAP + 500))
    (results / "jobs-raw.json").write_text(
        json.dumps([{"id": "a", "title": "role", "description": desc}]),
    )

    chunk.main(batch=40)

    batched = json.loads((results / "batches" / "batch-000.json").read_text())[0]["description"]
    assert len(batched) == DESC_CAP  # bounded
    assert batched.startswith("Responsibilities")  # scoped first, then bounded


def test_chunk_keeps_the_jd_whole_when_a_marker_lands_in_prose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A marker word in running prose must not gut the posting.

    99.9% of the corpus is one unbroken line, so markers are matched mid-string and a sentence like
    "...who care about requirements gathering..." can look like a heading. Measured on the real
    corpus this cut JDs to as little as 1.5% of their length. The retention floor is what makes
    mid-string matching safe: a slice that keeps too little is treated as a spurious hit.
    """
    results = _setup(tmp_path, monkeypatch)
    desc = "Our team builds tools for scientists. " * 60 + (
        "we value people who care about requirements gathering and delivery."
    )
    (results / "jobs-raw.json").write_text(
        json.dumps([{"id": "a", "title": "role", "description": desc}]),
    )

    chunk.main(batch=40)

    batched = json.loads((results / "batches" / "batch-000.json").read_text())[0]["description"]
    assert len(desc) < DESC_CAP  # the cap is not what is under test here
    assert batched == desc  # the spurious match is rejected, the posting survives intact
