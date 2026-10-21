"""Value-add tests for the decision-model pre-filter (shadow mode).

Covers the sharp edges: reading the fit probability from both backends' replies, sending a JD on
to the LLM screen (``None``) on ANY failure instead of guessing, and the shadow-report arithmetic
the go/no-go decision rests on. Network calls are injected, so these run offline.
"""

from __future__ import annotations

import json
import urllib.error
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

from ajoa_kit import decision_prefilter as prefilter

if TYPE_CHECKING:
    from collections.abc import Callable

KEYS = prefilter.DecisionKeys(
    typesafe_api_key=SecretStr("ts-secret"),
    cloudflare_api_token=SecretStr("cf-secret"),
    cloudflare_account_id="acct123",
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"answers": {"fit": {"type": "noul", "noul": 0.82}}}, 0.82),
        # Workers AI REST wraps model output in {"result": ..., "success": true}.
        ({"result": {"answers": {"fit": {"noul": 0.1}}}, "success": True}, 0.1),
        ({"answers": {}}, None),
        ({"answers": {"fit": {"noul": "high"}}}, None),
        ({"error": "rate limited"}, None),
    ],
)
def test_fit_probability_is_read_from_either_reply_shape(payload: dict, expected: object) -> None:
    assert prefilter.parse_fit(payload) == expected


def _post_raising(exc: Exception) -> Callable[..., dict]:
    def post(url: str, body: dict, headers: dict[str, str]) -> dict:
        raise exc

    return post


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.HTTPError("https://x", 403, "Forbidden", None, None),  # type: ignore[arg-type]
        urllib.error.URLError("timed out"),
        json.JSONDecodeError("bad", "", 0),
    ],
)
def test_any_backend_failure_sends_the_jd_on_instead_of_guessing(exc: Exception) -> None:
    # A 403 (TypeSafe's WAF blocks some content), a timeout or junk must never count as "drop".
    assert prefilter.fit("state", "jev", KEYS, post=_post_raising(exc)) is None


def test_requests_carry_one_fit_question_and_the_right_endpoint() -> None:
    seen: dict[str, object] = {}

    def post(url: str, body: dict, headers: dict[str, str]) -> dict:
        seen.update(url=url, body=body, auth=headers["Authorization"])
        return {"answers": {"fit": {"noul": 0.5}}}

    prefilter.fit("JD text", "clef", KEYS, post=post)
    assert "accounts/acct123/ai/run/@cf/cloudflare/clef-flash" in str(seen["url"])
    assert seen["auth"] == "Bearer cf-secret"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["state"] == "JD text"
    assert list(body["questions"]) == ["fit"]
    assert body["questions"]["fit"]["type"] == "noul"


def test_missing_key_sends_the_jd_on_without_calling_out() -> None:
    called = []
    no_keys = prefilter.DecisionKeys(
        typesafe_api_key=None, cloudflare_api_token=None, cloudflare_account_id=None
    )
    out = prefilter.fit("s", "jev", no_keys, post=lambda *a: called.append(a) or {})
    assert out is None
    assert called == []


def test_shadow_report_counts_recall_drops_and_escalations() -> None:
    rows = [
        {"kept": True, "score": 5, "p": 0.9},
        {"kept": True, "score": 4, "p": 0.2},  # a score-4 offer lost at threshold 0.3
        {"kept": True, "score": 3, "p": None},  # escalated -> still goes to the LLM, never lost
        {"kept": False, "score": None, "p": 0.1},
        {"kept": False, "score": None, "p": 0.6},
        {"kept": False, "score": None, "p": None},
    ]
    line = prefilter.report_row(rows, threshold=0.3, kept_share=0.25)
    assert line["recall_kept"] == pytest.approx(2 / 3)
    assert line["recall_score4"] == pytest.approx(1 / 2)
    assert line["dropped_caught"] == pytest.approx(1 / 3)
    assert line["escalated"] == 2
    # Estimated share of ALL screened JDs the pre-filter would drop, reweighted to the real mix.
    assert line["est_drop_share"] == pytest.approx(0.75 * (1 / 3) + 0.25 * (1 / 3))
