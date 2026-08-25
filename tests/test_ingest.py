"""Value-add tests for ingest source loading.

Cover the seed.json -> default-seed.json fallback contract and the integrity of the shipped
default-seed.json (so a malformed committed default can't silently break out-of-box ingest).
Adapter parsing / pre-filter is covered elsewhere.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from ajoa_kit import __main__ as cli
from ajoa_kit import defaults, ingest, normalize
from ajoa_kit.models import Lane


def _write(path: Path, slug: str) -> None:
    entry = {"ats": "lever", "slug": slug, "company": "X", "lane": "engineering"}
    path.write_text(json.dumps({"feeds": [], "ats": [entry]}))


def test_load_sources_prefers_seed_over_default(tmp_path: Path) -> None:
    _write(tmp_path / "seed.json", "from-seed")
    _write(tmp_path / "default-seed.json", "from-default")
    _, ats, _ = ingest.load_sources(tmp_path)
    assert [a["slug"] for a in ats] == ["from-seed"]  # the run config wins


def test_load_sources_falls_back_to_default(tmp_path: Path) -> None:
    _write(tmp_path / "default-seed.json", "from-default")  # no seed.json present
    _, ats, _ = ingest.load_sources(tmp_path)
    assert [a["slug"] for a in ats] == ["from-default"]


def test_load_sources_fails_loud_when_neither_present(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"seed\.json"):
        ingest.load_sources(tmp_path)


def test_shipped_default_seed_is_valid() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "default-seed.json"
    cfg = json.loads(path.read_text())  # raises on malformed JSON
    assert cfg["ats"], "default-seed.json must list ats sources"
    assert all({"ats", "slug", "company", "lane"} <= e.keys() for e in cfg["ats"])
    assert all({"source", "url"} <= f.keys() for f in cfg["feeds"])


def test_load_lanes_reads_override(tmp_path: Path) -> None:
    (tmp_path / "lanes.json").write_text(
        json.dumps([{"key": "ml", "label": "ML", "focus": "models", "gapHint": "research depth"}])
    )
    lanes = ingest.load_lanes(tmp_path)
    assert [lane.key for lane in lanes] == ["ml"]
    assert lanes[0].gap_hint == "research depth"  # the camelCase JSON alias maps to the field


def test_load_lanes_falls_back_to_defaults_when_absent(tmp_path: Path) -> None:
    assert ingest.load_lanes(tmp_path) is defaults.DEFAULT_LANES  # no lanes.json present


def test_load_location_is_inert_without_a_policy_file(tmp_path: Path) -> None:
    """A fresh clone has no config/location.json, and that must never fail or filter.

    The file is untracked by design (it describes a person; the repo's no-PII rule keeps it out),
    so absence is the normal case. An empty policy must report ``is_active`` False so the relevance
    screen is told to skip location filtering rather than guess.
    """
    policy = ingest.load_location(tmp_path)
    assert policy.is_active is False
    assert policy.authorized_in == []
    assert policy.remote_ok is True  # permissive default — never silently drops a remote role


def test_load_location_reads_policy_and_round_trips_the_workflow_aliases(tmp_path: Path) -> None:
    """The camelCase aliases must survive both directions — one file feeds Python and the JS arg."""
    written = {
        "basedIn": "Zurich, Switzerland",
        "authorizedIn": ["Switzerland", "EU"],
        "remoteOk": True,
        "relocateTo": ["Germany"],
        "notes": "no visa sponsorship available",
    }
    (tmp_path / "location.json").write_text(json.dumps(written))
    policy = ingest.load_location(tmp_path)
    assert policy.is_active is True  # authorized_in present -> the screen can now exclude
    assert policy.authorized_in == ["Switzerland", "EU"]
    assert policy.based_in == "Zurich, Switzerland"
    assert policy.model_dump(by_alias=True) == written  # emitted shape == args.location shape


def test_load_tenure_is_inert_without_a_policy_file(tmp_path: Path) -> None:
    """Mirrors location (arc-010 item 8): absence must never fail or filter.

    Phase D found 5 of 12 packs had no employment tenure to cite against a JD's stated
    requirement. Same shape as location: the file is untracked (describes a person), so a fresh
    clone has none, and ``is_active`` False tells the screen to skip tenure flagging entirely.
    """
    policy = ingest.load_tenure(tmp_path)
    assert policy.is_active is False
    assert policy.longest_tenure_years == 0


def test_load_tenure_reads_policy_and_round_trips_the_workflow_aliases(tmp_path: Path) -> None:
    """The camelCase alias must survive both directions — one file feeds Python and the JS arg."""
    written = {"longestTenureYears": 2.5, "notes": "two roles cut short by acquisitions"}
    (tmp_path / "tenure.json").write_text(json.dumps(written))
    policy = ingest.load_tenure(tmp_path)
    assert (
        policy.is_active is True
    )  # a real figure -> the screen can now flag a JD's ask against it
    assert policy.longest_tenure_years == 2.5
    assert policy.model_dump(by_alias=True) == written  # emitted shape == args.tenure shape


def test_shipped_lanes_json_matches_in_code_defaults() -> None:
    # The shipped config/lanes.json is the SSOT; DEFAULT_LANES is the in-code fallback that must
    # mirror it (equality guards the two from silently drifting apart).
    path = Path(__file__).resolve().parents[1] / "config" / "lanes.json"
    shipped = [Lane.model_validate(e) for e in json.loads(path.read_text())]
    assert shipped == defaults.DEFAULT_LANES


def test_shipped_keywords_json_matches_in_code_defaults() -> None:
    # The shipped config/keywords.json is the SSOT (published as trend keys — keep it generic);
    # defaults.INTEREST/TITLE_ROLES are the in-code no-config mirror, guarded against drift the
    # same way as lanes (#249 slice B).
    from ajoa_kit import defaults

    path = Path(__file__).resolve().parents[1] / "config" / "keywords.json"
    shipped = json.loads(path.read_text())
    assert shipped["interest"] == defaults.INTEREST
    assert shipped["title_roles"] == defaults.TITLE_ROLES


def test_collect_warn_and_continues_on_failing_source() -> None:
    # A raising source (e.g. a non-200 -> FetchError, or a bad slug) is recorded in `failures`
    # and never aborts the run — the other sources still collect (run-level resilience).
    def boom() -> list[dict]:
        raise RuntimeError("boom")

    def ok() -> list[dict]:
        return [normalize.record(id="x", ats="rss", source="s", title="Engineer")]

    state = ingest.collect([("bad", boom), ("good", ok)])
    assert any("bad" in f and "RuntimeError" in f for f in state["failures"])
    assert state["counts"]["good"] == 1  # the healthy source still collected
    assert "bad" not in state["counts"]  # the failing source contributes no counts entry
    assert len(state["jobs"]) == 1


def test_update_corpus_first_run_seeds_with_first_seen(tmp_path: Path) -> None:
    jobs = [normalize.record(id="a", ats="rss", source="s", title="Engineer", description="build")]
    ingest._update_corpus(jobs, tmp_path, "2026-06-01")
    corpus = json.loads((tmp_path / "corpus.json").read_text())
    assert len(corpus) == 1
    assert corpus[0]["first_seen"] == "2026-06-01"
    assert corpus[0]["last_seen"] == "2026-06-01"
    assert "content_hash" in corpus[0]


def test_update_corpus_second_run_keeps_delisted_and_updates_changed(tmp_path: Path) -> None:
    # First pull: a + b. Second pull: a's description changed, b is gone (delisted).
    a0 = normalize.record(id="a", ats="rss", source="s", title="Engineer", description="v1")
    b0 = normalize.record(id="b", ats="rss", source="s", title="SRE", description="ops")
    ingest._update_corpus([a0, b0], tmp_path, "2026-06-01")
    a1 = normalize.record(id="a", ats="rss", source="s", title="Engineer", description="v2")
    ingest._update_corpus([a1], tmp_path, "2026-06-27")

    corpus = {r["id"]: r for r in json.loads((tmp_path / "corpus.json").read_text())}
    assert set(corpus) == {"a", "b"}  # delisted record retained
    assert corpus["a"]["description"] == "v2"  # changed record adopted fresh content
    assert corpus["a"]["first_seen"] == "2026-06-01"  # preserved across the change
    assert corpus["a"]["last_seen"] == "2026-06-27"  # advanced
    assert corpus["b"]["last_seen"] == "2026-06-01"  # delisted -> last_seen frozen

    # Local-only digest (#175): emitted with corpus.json on --merge (a changed, b delisted).
    digest = (tmp_path / "daily-summary.md").read_text()
    assert "**Changed:** 1" in digest
    assert "**Delisted:** 1" in digest
    assert "No new offers" in digest  # nothing new this run


def _capture_ingest(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> dict:
    """Run the CLI with argv and return the kwargs the ingest step was dispatched with."""
    called: dict[str, object] = {}
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr("ajoa_kit.ingest.main", lambda **kw: called.update(kw))
    cli.main()
    return called


def test_cli_ingest_merge_flag_dispatches_merge_true(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: --merge must be REGISTERED on the ingest subparser, not just read in the
    # dispatcher — otherwise argparse rejects it ("unrecognized arguments").
    assert _capture_ingest(monkeypatch, ["ajoa-kit", "ingest", "--merge"]) == {"merge": True}


def test_cli_ingest_without_flag_defaults_merge_false(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _capture_ingest(monkeypatch, ["ajoa-kit", "ingest"]) == {"merge": False}
