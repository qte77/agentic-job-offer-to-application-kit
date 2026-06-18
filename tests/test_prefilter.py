"""Value-add tests for the deterministic pre-filter (word-boundary matching).

The sharp edge: interest terms must match on WORD BOUNDARIES so short tokens like "ai"
do not match inside unrelated words ("maintenance"). This is the cheap recall cut that
runs before the expensive LLM relevance pass.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ajoa_kit import ingest
from ajoa_kit.ingest import is_interesting, is_role_title, keep

if TYPE_CHECKING:
    from pathlib import Path


def test_interest_requires_word_boundary() -> None:
    assert is_interesting("Senior AI Engineer")
    # 'ai' is a substring of "maintenance"/"retail" but not a whole word -> must NOT match
    assert not is_interesting("Maintenance Coordinator")
    assert not is_interesting("Retail Sales Associate")


def test_role_title_is_core_role_nouns_only() -> None:
    assert is_role_title("Backend Engineer")
    # "data" is an INTEREST term but not a core role noun -> title fallback should not fire
    assert not is_role_title("Data Analyst")


def test_keep_ats_on_department_or_title() -> None:
    sales = {"ats": "greenhouse", "department": "Sales", "title": "Account Executive"}
    assert not keep(sales)  # both department and title miss
    by_dept = {"ats": "greenhouse", "department": "Engineering", "title": "Account Manager"}
    assert keep(by_dept)  # department matches
    by_title = {"ats": "lever", "department": "", "title": "Backend Engineer"}
    assert keep(by_title)  # empty department, title fallback fires


def test_keep_rss_uses_title() -> None:
    assert keep({"ats": "rss", "title": "Software Developer"})
    assert not keep({"ats": "rss", "title": "Marketing Lead"})


def test_load_keywords_reads_config_override(tmp_path: Path) -> None:
    (tmp_path / "keywords.json").write_text(
        json.dumps({"interest": ["rust", "wasm"], "title_roles": ["rust"]})
    )
    interest, title_roles = ingest.load_keywords(tmp_path)
    assert interest == ["rust", "wasm"]
    assert title_roles == ["rust"]


def test_load_keywords_falls_back_to_defaults(tmp_path: Path) -> None:
    # no keywords.json in tmp_path -> the hardcoded defaults apply
    interest, title_roles = ingest.load_keywords(tmp_path)
    assert interest == ingest.INTEREST
    assert title_roles == ingest.TITLE_ROLES


def test_custom_keyword_set_matches_on_word_boundary() -> None:
    pat_interest, pat_title = ingest.build_patterns(["rust"], ["rust"])
    assert is_interesting("Senior Rust Engineer", pat_interest)
    # 'rust' inside 'Trust' is not a whole word -> must NOT match
    assert not is_interesting("Trust & Safety Lead", pat_interest)
    assert is_role_title("Rust Developer", pat_title)
