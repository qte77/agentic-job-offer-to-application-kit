"""Value-add tests for prefill field-schema handling (``prefill``, #50).

Cover the real parsing/rendering logic only: normalizing a Greenhouse ``?questions=true``
payload (incl. select options and the required flag) and rendering the required marker +
options. No getter/constant trivia. The network fetch is a thin wrapper, untested here.
"""

from __future__ import annotations

from ajoa_kit import prefill

GH_JOB = {
    "questions": [
        {
            "label": "First Name",
            "required": True,
            "fields": [{"name": "first_name", "type": "input_text", "values": []}],
        },
        {
            "label": "Are you authorized to work?",
            "required": True,
            "fields": [
                {
                    "name": "q_auth",
                    "type": "multi_value_single_select",
                    "values": [{"label": "Yes", "value": 1}, {"label": "No", "value": 0}],
                }
            ],
        },
        {
            "label": "LinkedIn",
            "required": False,
            "fields": [{"name": "linkedin", "type": "input_text"}],
        },
    ]
}


def test_parse_extracts_name_label_required_type() -> None:
    fields = prefill.parse_greenhouse_questions(GH_JOB)
    assert len(fields) == 3
    first = fields[0]
    assert (first["name"], first["label"], first["required"], first["type"]) == (
        "first_name",
        "First Name",
        True,
        "input_text",
    )
    assert fields[2]["required"] is False  # optional field flagged correctly


def test_parse_captures_select_options() -> None:
    auth = next(f for f in prefill.parse_greenhouse_questions(GH_JOB) if f["name"] == "q_auth")
    assert auth["values"] == ["Yes", "No"]


def test_parse_no_questions_is_empty() -> None:
    assert prefill.parse_greenhouse_questions({}) == []


def test_render_marks_required_and_lists_options_only_where_present() -> None:
    md = prefill.render_fields(prefill.parse_greenhouse_questions(GH_JOB))
    lines = {line.split("**")[1]: line for line in md.splitlines() if "**" in line}
    assert "(required)" in lines["First Name"]
    assert "Yes" in lines["Are you authorized to work?"]  # select options surfaced
    assert "(required)" not in lines["LinkedIn"]  # optional field not marked required
