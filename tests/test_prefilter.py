"""Value-add tests for the deterministic pre-filter (word-boundary matching).

The sharp edge: interest terms must match on WORD BOUNDARIES so short tokens like "ai"
do not match inside unrelated words ("maintenance"). This is the cheap recall cut that
runs before the expensive LLM relevance pass.
"""

from __future__ import annotations

from ajoa_kit.ingest import is_interesting, is_role_title, keep


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
