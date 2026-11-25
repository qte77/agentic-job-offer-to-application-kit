"""Value-add tests for the prefill pack's "Apply via" check (#526).

The tailor agent writes the pack from third-party JD text, so the code scans every line, keeps only
links and addresses the job record, its JD or the candidate's own library allow, and writes the
route line itself.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ajoa_kit.apply_via import NEEDS_HUMAN, OFF_HOST, REMOVED, WARNING, check_apply_via

RECORD = {
    "id": "greenhouse:acme:42",
    "ats": "greenhouse",
    "url": "https://jobs.example.com/careers/42?gh_jid=42&utm_source=feed",
    "description": (
        "Apply at https://careers.example.org/jobs/42-engineer?ref=jd or email jobs@example.org."
    ),
}
CANON = "https://jobs.example.com/careers/42?gh_jid=42"
JD_ROUTE = "https://careers.example.org/jobs/42-engineer"
EVIL = "evil.example.net"


def pack_with(line: str) -> str:
    return f"{line}\n\nFirst name: [NEEDS HUMAN INPUT]\n"


def first_line(text: str) -> str:
    return text.splitlines()[0]


# --- what passes ---


def test_record_url_with_gh_jid_is_kept_without_warnings() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}"), RECORD)
    assert text == pack_with(f"**Apply via:** {CANON}")
    assert warnings == []


def test_raw_record_url_is_accepted_as_stored() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {RECORD['url']}"), RECORD)
    assert first_line(text) == f"**Apply via:** {RECORD['url']}"
    assert warnings == []


def test_jd_route_cut_to_host_and_path_is_kept_and_flagged_as_off_host() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {JD_ROUTE}"), RECORD)
    assert first_line(text) == f"**Apply via:** {JD_ROUTE}"
    assert warnings == [OFF_HOST]


def test_closing_punctuation_after_an_allowed_link_is_fine() -> None:
    for tail in (".", ",", ";", ")", "!", "?"):
        body = pack_with(f"**Apply via:** the portal ({CANON}){tail} or email the team")
        text, warnings = check_apply_via(body, RECORD)
        assert first_line(text) == f"**Apply via:** {CANON}", tail
        assert warnings == [], tail


def test_scheme_less_jd_route_and_jd_email_are_kept() -> None:
    for route in ("careers.example.org/jobs/42-engineer", "jobs@example.org"):
        text, warnings = check_apply_via(pack_with(f"**Apply via:** {route}"), RECORD)
        assert first_line(text) == f"**Apply via:** {route}", route
        assert warnings == [OFF_HOST], route


def test_code_writes_the_route_line_from_plain_words_or_a_missing_line() -> None:
    for body in (
        pack_with("**Apply via:** the careers portal"),
        "First name: [NEEDS HUMAN INPUT]\n",
    ):
        text, warnings = check_apply_via(body, RECORD)
        assert first_line(text) == f"**Apply via:** {CANON}"
        assert warnings == []


def test_own_links_from_the_library_stay() -> None:
    body = pack_with(f"**Apply via:** {CANON}") + "Website: https://alexis.example.dev/work\n"
    text, warnings = check_apply_via(body, RECORD, ("https://alexis.example.dev/work",))
    assert "https://alexis.example.dev/work" in text
    assert warnings == []


def test_a_disguised_route_label_still_yields_exactly_one_route_line() -> None:
    text, _ = check_apply_via(pack_with(f"**Apply\u200b via\uff1a** {CANON}"), RECORD)
    assert text.count("Apply") == 1
    assert first_line(text) == f"**Apply via:** {CANON}"


def test_check_is_idempotent_on_its_own_output() -> None:
    body = pack_with(f"**Apply via**: https://{EVIL}/x") + f"note https://{EVIL}/y\n"
    once, _ = check_apply_via(body, RECORD)
    twice, warnings = check_apply_via(once, RECORD)
    assert twice == once
    assert warnings == []


# --- what fails: every string must lose the attacker host and warn (#526 review F1-F3) ---

BYPASSES = [
    # F1: the label is not the gate
    f"**Apply via**: https://{EVIL}/x",
    f"**Apply via** https://{EVIL}/x",
    f"Apply via - https://{EVIL}/x",
    f"**Apply\u200b via:** https://{EVIL}/x",
    f"**Apply via\u200b:** https://{EVIL}/x",
    f"**\u0410pply via:** https://{EVIL}/x",
    f"**Apply via\uff1a** https://{EVIL}/x",
    f"**Apply via&#58;** https://{EVIL}/x",
    f"**Apply _via_:** https://{EVIL}/x",
    f"**Apply here:** https://{EVIL}/x",
    f"| Application link | https://{EVIL}/x |",
    f"**Apply via:**\nhttps://{EVIL}/x",
    f"**Apply via:** [the portal][1]\n\n[1]: https://{EVIL}/x",
    f"https://{EVIL}/x",
    # F2: a link that does not start the token
    f'**Apply via:** <a href="https://{EVIL}/x">portal</a>',
    f"**Apply via:** <a href='https://{EVIL}/x?d=1'>portal</a>",
    f"**Apply via:** [the [official] portal](https://{EVIL}/x?d=1)",
    f"**Apply via:** [portal\\]x](https://{EVIL}/x)",
    f"**Apply via:** portal(https://{EVIL}/x)",
    f"**Apply via:** url=https://{EVIL}/x?d=1",
    f"**Apply via:** |https://{EVIL}/x",
    f"**Apply via:** \u200bhttps://{EVIL}/x",
    f"**Apply via:** \ufeffhttps://{EVIL}/x",
    f"**Apply via:** www.{EVIL}?d=secret",
    f"**Apply via:** www.{EVIL}#secret",
    f"**Apply via:** {EVIL}?d=secret",
    f"**Apply via:** {EVIL}\\x",
    "**Apply via:** www.\u0435vil.example.net/x",
    f"**Apply via:** \uff48\uff54\uff54\uff50\uff53://{EVIL}/x",
    "**Apply via:** \uff48\uff54\uff54\uff50\uff53\uff1a\uff0f\uff0fevil.example.net\uff0fx",
    f"**Apply via:** javascript:alert(1) {EVIL}",
    f"**Apply via:** mailto:jobs@example.org?subject={EVIL}",
    # glued onto an allowed item
    f"**Apply via:** {CANON}&x={EVIL}",
    f"**Apply via:** {CANON}#{EVIL}",
    f"**Apply via:** {JD_ROUTE}.{EVIL}/x",
    f"**Apply via:** {JD_ROUTE}?d={EVIL}",
    # glued after an allowed item with characters an autolink keeps
    *(f"**Apply via:** {JD_ROUTE}{c}d=1.{EVIL}" for c in ";!$'*,~("),
    f"**Apply via:** {CANON};x=1.{EVIL}",
    f"**Apply via:** https://careers.example.org@{EVIL}/jobs/42-engineer",
    # F3: an email that is not alone in its token
    f"**Apply via:** email hr@{EVIL}: quote ref 42",
    f"**Apply via:** hr@{EVIL}?subject=x",
    f"**Apply via:** hr@{EVIL}/",
    f"**Apply via:** HR<hr@{EVIL}>",
    f"**Apply via:** o'x@{EVIL}",
    f"**Apply via:** \u200bhr@{EVIL}",
    "**Apply via:** hr@evil_x.example.net",
    "**Apply via:** hr@evil_.example.net",
    "**Apply via:** hr@\u00e9vil.example.net",
]


@pytest.mark.parametrize("body", BYPASSES)
def test_bypass_strings_lose_the_attacker_host_and_warn(body: str) -> None:
    text, warnings = check_apply_via(pack_with(body), RECORD)
    assert "example.net" not in text  # the emitted bytes, not a normalised view of them
    assert WARNING in warnings
    assert first_line(text) == f"**Apply via:** {CANON}"


def test_a_failing_line_becomes_the_fixed_note_and_the_warning_never_repeats_it() -> None:
    body = pack_with(f"**Apply via:** {CANON}") + f"LinkedIn: https://{EVIL}/in/planted\n"
    text, warnings = check_apply_via(body, RECORD)
    assert REMOVED in text.splitlines()
    assert "planted" not in "".join(warnings)


def test_no_record_fails_closed() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}"), None)
    assert first_line(text) == f"**Apply via:** {NEEDS_HUMAN}"
    assert warnings == [WARNING]


def test_a_record_without_an_http_url_falls_back_to_needs_human_input() -> None:
    rec = {**RECORD, "url": "javascript:alert(1)"}
    text, _ = check_apply_via(pack_with(f"**Apply via:** https://{EVIL}/x"), rec)
    assert first_line(text) == f"**Apply via:** {NEEDS_HUMAN}"


# --- round 2 (#527 review N1-N6): data hidden in characters normalisation removes, and noise ---

ATTACKER_ROUTE = "https://attacker.example.net/apply"
ATTACKER_JD = {**RECORD, "description": f"Apply at {ATTACKER_ROUTE} today."}
_TAGS = "".join(chr(0xE0000 + ord(c)) for c in "secret")

HIDDEN = [
    f"Portal: {ATTACKER_ROUTE}{_TAGS}",
    f"Portal: {ATTACKER_ROUTE}\u200b\u200c\u200b\u200c",
    f"Portal: https://attacker.example.net/{_TAGS}apply",
    "Portal: https://attacker.example.net/ap\u00adply",
    f"Portal: {ATTACKER_ROUTE}\x1fsecret",
    f"Portal: {ATTACKER_ROUTE}\x1csecret",
    f"Portal: {ATTACKER_ROUTE}\x85secret",
    "Portal: https://attacker.example.net/\uff41pply",
    "Portal: https://attacker.example.net/ApPlY",
]


@pytest.mark.parametrize("line", HIDDEN)
def test_nothing_the_check_did_not_see_is_emitted(line: str) -> None:
    text, _ = check_apply_via(pack_with(f"**Apply via:** {CANON}") + line, ATTACKER_JD)
    assert all(c == "\n" or " " <= c <= "~" for c in text), "only printable ASCII is emitted"
    assert "secret" not in text
    assert "ApPlY" not in text


@pytest.mark.parametrize(
    "line",
    [f"Portal: {ATTACKER_ROUTE}?.,;:!]", f"Portal: {ATTACKER_ROUTE}.]", f"[see {ATTACKER_ROUTE}]"],
)
def test_a_trailing_bracket_after_a_route_replaces_the_line(line: str) -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}") + line, ATTACKER_JD)
    assert REMOVED in text.splitlines()
    assert WARNING in warnings


@pytest.mark.parametrize(
    "body",
    [
        f"Open [a\nb] here.\n\n[a\nb]: https:/{EVIL}",
        "[x]: vscode:secret",
        "Link: https:/2130706433/x?d=secret",
        f"[NEEDS HUMAN INPUT]: irc:{EVIL}/x?d=secret",
        f"[x]:\thttps:/{EVIL}",
    ],
)
def test_reference_definitions_and_single_slash_schemes_are_removed(body: str) -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}") + body, RECORD)
    assert EVIL not in text
    assert "secret" not in text
    assert WARNING in warnings


ORDINARY = [
    "Node.js/Express experience: 5 years",
    "GPA: 3.85/4.0",
    "Python 3.12: yes",
    "ASP.NET/C# : intermediate",
    "README.md: section 2",
    "Salary expectation: > 80k",
    "Notice period: < 3 months",
    "Relocation: yes -> Berlin",
    "GitHub handle: @alexis-doe",
    "Work authorization: [NEEDS HUMAN INPUT]",
    "Email: [email]",
    "Phone: [phone]",
    "Tel: [phone]",
    "Data: 4 years of pipelines",
    "Apply viable skills: Python, SQL",
    "Timezone: UTC+1:00",
    "Runtime: node:20",
    "Level:Senior",
    "C++: std::vector",
    "Availability: 5 @ 80%",
    "Ping me via @mention or hr@evilhost",
]


def test_ordinary_field_lines_are_never_replaced() -> None:
    body = f"**Apply via:** {CANON}\n" + "\n".join(ORDINARY)
    text, warnings = check_apply_via(body, RECORD)
    assert text == body
    assert warnings == []


def test_a_unicode_lookalike_host_never_matches_and_never_raises() -> None:
    rec = {**RECORD, "description": "Apply at https://hiring.example.org/x today."}
    lookalike = "Portal: https://h\u0131ring.example.org/x"  # dotless i
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}") + lookalike, rec)
    assert REMOVED in text.splitlines()
    assert WARNING in warnings


def test_a_second_route_line_is_dropped_with_a_warning() -> None:
    body = (
        f"**Apply via:** {CANON}\nApply via LinkedIn Easy Apply: yes\nApply viable skills: Python"
    )
    text, warnings = check_apply_via(body, RECORD)
    assert text == f"**Apply via:** {CANON}\nApply viable skills: Python"
    assert warnings == [WARNING]


def test_a_jd_route_without_a_record_url_is_flagged() -> None:
    rec = {**RECORD, "url": ""}
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {JD_ROUTE}"), rec)
    assert first_line(text) == f"**Apply via:** {JD_ROUTE}"
    assert warnings == [OFF_HOST]


def test_scheme_and_host_match_in_any_case_but_the_path_exactly() -> None:
    upper = "HTTPS://Careers.Example.org/jobs/42-engineer"
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {upper}"), RECORD)
    assert first_line(text) == f"**Apply via:** {JD_ROUTE}"  # the code writes the allowed string
    assert warnings == [OFF_HOST]
    _, w_path = check_apply_via(
        pack_with(f"**Apply via:** {JD_ROUTE.upper()[:8]}{JD_ROUTE[8:].upper()}"), RECORD
    )
    assert WARNING in w_path


class TestNoAttackerLinkSurvives:
    @given(pre=st.text(), post=st.text())
    @settings(deadline=None)
    def test_an_attacker_url_anywhere_in_a_line_is_removed(self, pre: str, post: str) -> None:
        text, _ = check_apply_via(f"{pre}https://{EVIL}/x?d=1{post}", RECORD)
        assert f"{EVIL}/x" not in text

    @given(post=st.text())
    @settings(deadline=None)
    def test_only_trimmable_text_follows_an_allowed_route(self, post: str) -> None:
        text, _ = check_apply_via(f"Portal: {ATTACKER_ROUTE}{post}", ATTACKER_JD)
        for line in text.split("\n"):
            at = line.find(ATTACKER_ROUTE)
            if at == -1 or line.startswith("**Apply via:**"):
                continue
            tail = re.split(r"[ \t]", line[at + len(ATTACKER_ROUTE) :], maxsplit=1)[0]
            # Reason: an autolink ends at ASCII space or tab and trims only this closing punctuation
            assert re.fullmatch(r"[.,;:!?)]*", tail), repr(tail)
