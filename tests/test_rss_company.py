"""RSS item-title -> (company, salary) extraction (arc 010 item 1).

The RSS adapter has no employer field — each feed folds it into the item title with its own
separator convention, so the title is the only source. Cases below are drawn from the 558
blank-company records in the live corpus.
"""

from __future__ import annotations

import pytest

from ajoa_kit.normalize import rss_company_salary


@pytest.mark.parametrize(
    ("source", "title", "company", "salary"),
    [
        # swissdevjobs: "Title @ Company [CHF band]" — all 363 blank records carry both.
        (
            "swissdevjobs",
            "Java Software Engineer (w/m/d) @ 08EINS Softwarehaus [CHF 90'000 - 110'000]",
            "08EINS Softwarehaus",
            "CHF 90'000 - 110'000",
        ),
        # ...and the band is optional: a title without one still yields the company.
        ("swissdevjobs", "Big Data & Platform Engineer 80-100% @ 3ap", "3ap", ""),
        # weworkremotely: "Company: Title".
        ("weworkremotely", "1Password: Senior Web Developer", "1Password", ""),
        # berlinstartupjobs: "Title // Company".
        ("berlinstartupjobs", "Senior iOS Engineer // Tandem", "Tandem", ""),
    ],
)
def test_extracts_company_per_feed_convention(
    source: str, title: str, company: str, salary: str
) -> None:
    assert rss_company_salary(source, title) == (company, salary)


def test_wwr_splits_on_the_first_colon_space_not_the_last() -> None:
    """A role name carrying its own colon must not be folded into the employer.

    Live corpus case: a last-colon split invents the employer
    "Indigenous Climate Action: Request for Proposals".
    """
    assert rss_company_salary(
        "weworkremotely", "Indigenous Climate Action: Request for Proposals: Website Developer"
    ) == ("Indigenous Climate Action", "")


def test_wwr_tolerates_a_url_shaped_company() -> None:
    """Live corpus case: the scheme's colon has no space after it, so it is not the separator."""
    assert rss_company_salary("weworkremotely", "https://shiperp.com/: PHP Web Developer") == (
        "https://shiperp.com/",
        "",
    )


@pytest.mark.parametrize(
    ("source", "title"),
    [
        # Live corpus case: one berlinstartupjobs title carries no separator at all.
        ("berlinstartupjobs", "Senior Product Manager, Data and API"),
        ("swissdevjobs", "Software Engineer"),
        ("weworkremotely", "Senior Web Developer"),
        # A feed with no known convention must never be guessed at.
        ("some-new-feed", "Senior Engineer @ Acme"),
    ],
)
def test_unmatched_title_yields_empty_not_a_mangled_name(source: str, title: str) -> None:
    assert rss_company_salary(source, title) == ("", "")
