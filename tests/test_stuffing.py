"""Value-add tests for the deterministic keyword-stuffing checker (``stuffing``).

Each case pins one stuffing pattern the checker must flag (or, for the honest CV, must
not) — the sharp edges, not trivial getters. Sibling of ``test_ats_check``.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit import stuffing

# An honest, varied CV: > 40 content words so the density path actually runs, but no
# keyword dominates and no phrase or line is a stuffed wall.
CLEAN_CV = (
    "# Jane Doe\n\n"
    "## Summary\n"
    "Infrastructure engineer focused on reliable distributed systems and developer "
    "tooling. I turn ambiguous problems into simple, well-tested services.\n\n"
    "## Experience\n"
    "- Built a streaming ingestion pipeline that halved processing latency.\n"
    "- Led migration of legacy batch jobs to an event-driven architecture.\n"
    "- Mentored two junior developers and sped up code-review turnaround.\n\n"
    "## Skills\n"
    "- Languages: Python, Go, TypeScript\n"
    "- Platforms: Kubernetes, AWS, Terraform\n\n"
    "## Education\n"
    "- BSc Computer Science, University of Somewhere\n"
)

# One keyword owning a fifth of the content words, spaced out so it is a density signal
# (not an adjacent repeated phrase). 60 tokens total, "kubernetes" every 5th.
DENSITY_STUFFED = " ".join("kubernetes" if i % 5 == 0 else f"skill{i}" for i in range(60))

# The same three-word phrase copy-pasted five times.
NGRAM_STUFFED = "## Summary\nsenior platform engineer " * 5 + "with broad delivery experience.\n"

# One line dumping 30 short skills — a classic ATS keyword wall.
LIST_STUFFED = (
    "## Skills\n"
    + ", ".join(f"tool{i}" for i in range(30))
    + "\n\n## Experience\n- Shipped things.\n"
)


def test_clean_cv_has_no_warnings() -> None:
    assert stuffing.stuffing_warnings(CLEAN_CV) == []


def test_keyword_density_is_flagged() -> None:
    warnings = stuffing.stuffing_warnings(DENSITY_STUFFED)
    assert any("content words" in w for w in warnings)


def test_repeated_phrase_is_flagged() -> None:
    warnings = stuffing.stuffing_warnings(NGRAM_STUFFED)
    assert any("repeated" in w for w in warnings)


def test_dense_skills_line_is_flagged() -> None:
    warnings = stuffing.stuffing_warnings(LIST_STUFFED)
    assert any("items" in w for w in warnings)


def test_a_normal_short_skills_line_is_not_list_stuffing() -> None:
    # A handful of comma-separated skills is honest, not a keyword wall.
    cv = CLEAN_CV.replace(
        "- Platforms: Kubernetes, AWS, Terraform\n",
        "- Platforms: Kubernetes, AWS, Terraform, Docker, Postgres\n",
    )
    assert stuffing.stuffing_warnings(cv) == []


def test_empty_and_whitespace_are_safe() -> None:
    assert stuffing.stuffing_warnings("") == []
    assert stuffing.stuffing_warnings("   \n\t  \n") == []


class TestStuffingProperties:
    # Reason: pure detector over arbitrary text; deadline off.
    @given(text=st.text())
    @settings(deadline=None)
    def test_never_raises_on_arbitrary_input(self, text: str) -> None:
        assert isinstance(stuffing.stuffing_warnings(text), list)
