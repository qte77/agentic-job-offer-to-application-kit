"""Offline end-to-end smoke test for the deterministic pipeline chain (#165).

The relevance and tailor steps are non-deterministic LLM Workflow scripts that cannot run in
CI, so this pins the deterministic CLI stages they bracket — ``chunk`` → ``persist_scored`` →
``persist_offer`` → ``ats_check`` — feeding canned, synthetic Workflow outputs where the LLM
would otherwise produce them. The value is the cross-stage seams the per-module unit tests do
*not* cover: one shared ``AJOA_RESULTS_DIR`` carried through every entrypoint, the manifest
``batch_count`` the relevance workflow fans out on, and the real on-disk ``cv.md`` that
``persist_offer`` writes being consumed by ``ats_check`` from that same path.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit import ats_check, chunk, persist_offer, persist_scored

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# A tiny synthetic ingest corpus standing in for results/jobs-raw.json (no PII; fictional
# companies). chunk treats it as an opaque list, so minimal JD-shaped records suffice.
JOBS_RAW = [
    {
        "id": "ashby:acme-ai:101",
        "title": "AI Engineer, Agentic Systems",
        "company": "Acme AI",
        "url": "https://example.com/acme-ai/jobs/101",
    },
    {
        "id": "greenhouse:globex:7",
        "title": "Senior Platform Engineer",
        "company": "Globex",
        "url": "https://example.com/globex/jobs/7?utm_source=feed",
    },
]

# Canned cc-workflow-relevance.js result (the LLM gap between chunk and persist_scored).
RELEVANCE_RESULT = {
    "relevant": [
        {
            "id": "ashby:acme-ai:101",
            "best_lane": "engineering",
            "score": 4,
            "verdict": "shortlist",
            "company": "Acme AI",
            "title": "AI Engineer, Agentic Systems",
            "url": "https://example.com/acme-ai/jobs/101",
            "rationale": "Direct fit on agentic LLM workflows.",
            "deadline": "2026-07-31",
            "deal_breaker": "",
        },
    ],
}

# Canned cc-workflow-tailor-offer.js pack (the LLM gap between persist_scored and persist_offer).
# The CV is deliberately ATS-clean (section headings, no tables/HTML) so ats_check passes.
TAILOR_PACK = {
    "slug": "acme-ai-101",
    "match": "Strong overlap on agentic LLM workflows, retrieval, and Python.",
    "cv": "## Summary\nInfrastructure-first AI engineer.\n\n## Experience\n"
    "- Built an agentic pipeline.\n\n## Skills\n- Python, LLMs\n",
    "cover_letter": "Dear hiring team, I am excited to apply for this role.",
    "gap_report": "Gap: production-at-scale ops and on-call rotations.",
    "prefill_pack": "First name: Alexis\nEmail: alexis@example.com\n(Human reviews + submits.)",
}


def test_offline_pipeline_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """chunk → persist_scored → persist_offer → ats_check over one shared results dir."""
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setenv("AJOA_RESULTS_DIR", str(results))
    (results / "jobs-raw.json").write_text(json.dumps(JOBS_RAW))

    # chunk: the manifest batch_count is the contract the relevance workflow fans out on.
    chunk.main(batch=40)
    manifest = json.loads((results / "batches" / "manifest.json").read_text())
    assert manifest == {"total_jobs": 2, "batch_size": 40, "batch_count": 1}
    batch = json.loads((results / "batches" / "batch-000.json").read_text())
    assert [j["id"] for j in batch] == ["ashby:acme-ai:101", "greenhouse:globex:7"]

    # persist_scored: canned relevance result → per-lane shortlist.{json,md}.
    rel_src = tmp_path / "relevance.json"
    rel_src.write_text(json.dumps(RELEVANCE_RESULT))
    persist_scored.main(src=rel_src)
    shortlist = json.loads((results / "engineering" / "shortlist.json").read_text())
    assert [j["id"] for j in shortlist] == ["ashby:acme-ai:101"]
    md = (results / "engineering" / "shortlist.md").read_text()
    assert "AI Engineer, Agentic Systems" in md
    assert "due 2026-07-31" in md  # #271 deadline flag rides through the deterministic chain

    # persist_offer: canned tailor pack → the 5 human-review artifacts.
    pack_src = tmp_path / "tailor.json"
    pack_src.write_text(json.dumps(TAILOR_PACK))
    persist_offer.main(src=pack_src)
    offer_dir = results / "offers" / "acme-ai-101"
    assert sorted(p.name for p in offer_dir.glob("*.md")) == [
        "cover-letter.md",
        "cv.md",
        "gap-report.md",
        "match.md",
        "prefill-pack.md",
    ]

    # ats_check: the cv.md persist_offer just wrote is parse-safe → returns (no SystemExit) and
    # leaves no cv-ats-check.md warning file behind.
    ats_check.main(src=offer_dir / "cv.md")
    assert not (offer_dir / "cv-ats-check.md").exists()
