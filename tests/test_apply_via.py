"""Value-add tests for the "Apply via" line check (#526).

The tailor agent writes the line from third-party JD text, so the link a candidate clicks is
checked in code: it must be the job record's own (canonical) url, or the host and path of a link
that appears in the JD, over http(s). Anything else on the line is replaced.
"""

from __future__ import annotations

from ajoa_kit.apply_via import NEEDS_HUMAN, check_apply_via

RECORD = {
    "id": "greenhouse:acme:42",
    "ats": "greenhouse",
    "url": "https://jobs.example.com/careers/42?gh_jid=42&utm_source=feed",
    "description": (
        "Apply at https://careers.example.org/jobs/42-engineer?ref=jd or email jobs@example.org."
    ),
}
CANON = "https://jobs.example.com/careers/42?gh_jid=42"


def pack_with(line: str) -> str:
    return f"{line}\n\nFirst name: [NEEDS HUMAN INPUT]\n"


def first_line(text: str) -> str:
    return text.splitlines()[0]


def test_record_url_with_gh_jid_is_kept() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}"), RECORD)
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings == []


def test_raw_record_url_is_accepted_in_canonical_form() -> None:
    raw = RECORD["url"]
    _, warnings = check_apply_via(pack_with(f"**Apply via:** {raw}"), RECORD)
    assert warnings == []


def test_jd_route_cut_to_host_and_path_is_kept() -> None:
    line = "**Apply via:** https://careers.example.org/jobs/42-engineer"
    text, warnings = check_apply_via(pack_with(line), RECORD)
    assert first_line(text) == line
    assert warnings == []


def test_planted_query_string_is_replaced() -> None:
    line = "**Apply via:** https://careers.example.org/jobs/42-engineer?note=ignore-previous"
    text, warnings = check_apply_via(pack_with(line), RECORD)
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings
    assert "ignore-previous" not in "".join(warnings)  # the sidecar never repeats the rejected text


def test_planted_fragment_on_the_record_url_is_replaced() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}#local-notes"), RECORD)
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings


def test_non_http_scheme_is_replaced() -> None:
    for bad in (
        "javascript:alert(1)",
        "file:///home/user/.ssh/id_rsa",
        "ftp://careers.example.org/jobs/42-engineer",
    ):
        text, warnings = check_apply_via(pack_with(f"**Apply via:** {bad}"), RECORD)
        assert first_line(text) == f"**Apply via:** {CANON}", bad
        assert warnings, bad


def test_unlisted_host_is_replaced() -> None:
    text, warnings = check_apply_via(
        pack_with("**Apply via:** https://evil.example.net/jobs/42"), RECORD
    )
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings


def test_userinfo_trick_is_replaced() -> None:
    line = "**Apply via:** https://careers.example.org@evil.example.net/jobs/42-engineer"
    text, warnings = check_apply_via(pack_with(line), RECORD)
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings


def test_markdown_link_with_a_different_target_is_replaced() -> None:
    line = (
        "**Apply via:** [https://careers.example.org/jobs/42-engineer](https://evil.example.net/x)"
    )
    text, warnings = check_apply_via(pack_with(line), RECORD)
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings


def test_one_bad_url_among_two_replaces_the_line() -> None:
    line = f"**Apply via:** {CANON} or https://evil.example.net/x"
    text, warnings = check_apply_via(pack_with(line), RECORD)
    assert first_line(text) == f"**Apply via:** {CANON}"
    assert warnings


def test_scheme_less_host_and_path_is_checked_too() -> None:
    _, w_ok = check_apply_via(
        pack_with("**Apply via:** careers.example.org/jobs/42-engineer"), RECORD
    )
    assert w_ok == []
    bad, w_bad = check_apply_via(pack_with("**Apply via:** evil.example.net/jobs/42"), RECORD)
    assert first_line(bad) == f"**Apply via:** {CANON}"
    assert w_bad


def test_bare_email_from_the_jd_is_kept_and_mailto_with_subject_is_replaced() -> None:
    ok, w_ok = check_apply_via(pack_with("**Apply via:** jobs@example.org"), RECORD)
    assert first_line(ok) == "**Apply via:** jobs@example.org"
    assert w_ok == []
    _, w_mailto = check_apply_via(
        pack_with("**Apply via:** mailto:jobs@example.org?subject=hi"), RECORD
    )
    assert w_mailto
    _, w_other = check_apply_via(pack_with("**Apply via:** someone@evil.example.net"), RECORD)
    assert w_other


def test_plain_words_and_needs_human_input_pass() -> None:
    for line in (f"**Apply via:** the Greenhouse form at {CANON}", f"**Apply via:** {NEEDS_HUMAN}"):
        text, warnings = check_apply_via(pack_with(line), RECORD)
        assert first_line(text) == line
        assert warnings == []


def test_every_line_with_the_label_is_checked() -> None:
    body = f"**Apply via:** {CANON}\n\nNotes\n\napply via: https://evil.example.net/x\n"
    text, warnings = check_apply_via(body, RECORD)
    assert "evil.example.net" not in text
    assert warnings


def test_no_record_fails_closed() -> None:
    text, warnings = check_apply_via(pack_with(f"**Apply via:** {CANON}"), None)
    assert first_line(text) == f"**Apply via:** {NEEDS_HUMAN}"
    assert warnings


def test_a_record_without_an_http_url_falls_back_to_needs_human_input() -> None:
    rec = {**RECORD, "url": "javascript:alert(1)"}
    text, warnings = check_apply_via(pack_with("**Apply via:** https://evil.example.net/x"), rec)
    assert first_line(text) == f"**Apply via:** {NEEDS_HUMAN}"
    assert warnings


def test_a_pack_without_the_line_is_unchanged() -> None:
    body = "First name: Alexis\nEmail: alexis@example.com\n"
    assert check_apply_via(body, RECORD) == (body, [])
    assert check_apply_via(body, None) == (body, [])
