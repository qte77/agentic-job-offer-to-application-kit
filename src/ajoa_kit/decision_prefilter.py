"""Decision-model pre-filter for the relevance screen, in shadow mode.

A decision model returns a probability for a typed yes/no question instead of generating text, at
a fraction of an LLM's cost. Two backends share one request shape (a ``state`` plus named
``questions``): TypeSafe's Jev and Cloudflare Workers AI's Clef-flash. Each JD gets ONE question:
is it a plausible fit for the candidate in any target lane?

Shadow mode only: ``ajoa-kit decision-prefilter`` scores a stratified sample of JDs the LLM
screen already judged, then prints, per threshold, how many kept offers a gate would lose and
how many JDs it would save the LLM. Nothing is gated yet. Any backend failure (a 403, a
timeout, junk) returns ``None``: the JD goes on to the LLM screen, never "drop".

Keys come from the git-ignored ``.env``: ``TYPESAFE_API_KEY``, ``CLOUDFLARE_API_TOKEN``,
``CLOUDFLARE_ACCOUNT_ID``. The JD text and a short candidate summary are sent to the chosen API.
"""

from __future__ import annotations

import json
import random
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from pydantic import SecretStr  # noqa: TC002 -- pydantic resolves field types at runtime
from pydantic_settings import BaseSettings, SettingsConfigDict

from ajoa_kit.defaults import DESC_CAP
from ajoa_kit.ingest import load_lanes
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.13.0"
CLEF_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/cloudflare/clef-flash"
)
CLEF_MODEL = "clef-flash"
TIMEOUT = 20.0
THRESHOLDS = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5)


class DecisionKeys(BaseSettings):
    """API keys for the decision-model backends, from the environment or ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    typesafe_api_key: SecretStr | None = None
    cloudflare_api_token: SecretStr | None = None
    cloudflare_account_id: str | None = None


def _endpoint(backend: str, keys: DecisionKeys) -> tuple[str, str, SecretStr | None]:
    """Return (url, model, token) for ``backend``; url is "" when it can't be built."""
    if backend == "jev":
        return JEV_URL, JEV_MODEL, keys.typesafe_api_key
    account = keys.cloudflare_account_id
    return (
        (CLEF_URL.format(account=account) if account else ""),
        CLEF_MODEL,
        keys.cloudflare_api_token,
    )


def _post(url: str, body: dict, headers: dict[str, str]) -> dict:
    if not url.startswith("https://"):  # never file:/ or other schemes
        raise ValueError(f"refusing non-https URL: {url!r}")
    req = urllib.request.Request(  # noqa: S310 -- https enforced above
        url, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310  # nosec B310
        return json.loads(resp.read())


def parse_fit(payload: object) -> float | None:
    """Read the ``fit`` probability from a Jev or Clef reply; ``None`` when absent or malformed."""
    if not isinstance(payload, dict):
        return None
    inner = payload.get("result", payload)
    try:
        p = inner["answers"]["fit"]["noul"]
    except (KeyError, TypeError):
        return None
    return float(p) if isinstance(p, int | float) and not isinstance(p, bool) else None


def fit(
    state: str,
    backend: str,
    keys: DecisionKeys,
    *,
    post: Callable[[str, dict, dict[str, str]], dict] = _post,
    lanes: str = "",
) -> float | None:
    """Probability the JD in ``state`` fits the candidate; ``None`` = send it on to the LLM."""
    url, model, token = _endpoint(backend, keys)
    if not url or token is None:
        return None
    question = (
        "Is this job a plausible fit for this candidate in at least one of these roles: "
        f"{lanes or 'the roles named in the candidate summary'}? "
        "Judge only from the job text and the candidate summary."
    )
    body = {
        "model": model,
        "state": state,
        "questions": {"fit": {"type": "noul", "instructions": question}},
    }
    headers = {
        "Authorization": f"Bearer {token.get_secret_value()}",
        "Content-Type": "application/json",
    }
    try:
        return parse_fit(post(url, body, headers))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError, ValueError):
        return None


def build_state(jd: dict, brief: str) -> str:
    """The ``state`` sent per JD: candidate summary, then the posting (description capped)."""
    head = f"{jd.get('title', '')} at {jd.get('company', '')} ({jd.get('location', '')})"
    return f"Candidate:\n{brief}\n\nJob: {head}\n{str(jd.get('description', ''))[:DESC_CAP]}"


def _drop_rate(rows: list[dict], threshold: float) -> float:
    """Share of ``rows`` a gate at ``threshold`` would drop (``p is None`` is never dropped)."""
    if not rows:
        return 0.0
    return sum(r["p"] is not None and r["p"] < threshold for r in rows) / len(rows)


def report_row(rows: list[dict], *, threshold: float, kept_share: float) -> dict:
    """Shadow metrics at ``threshold``: a JD is dropped when ``p < threshold`` (``None`` never)."""
    kept = [r for r in rows if r["kept"]]
    strong = [r for r in kept if (r["score"] or 0) >= 4]
    recall = 1 - _drop_rate(kept, threshold) if kept else 0.0
    caught = _drop_rate([r for r in rows if not r["kept"]], threshold)
    return {
        "threshold": threshold,
        "recall_kept": recall,
        "recall_score4": 1 - _drop_rate(strong, threshold) if strong else None,
        "dropped_caught": caught,
        "escalated": sum(r["p"] is None for r in rows),
        "est_drop_share": (1 - kept_share) * caught + kept_share * (1 - recall),
    }


def _screened(results: Path) -> tuple[list[dict], dict[str, float | None]]:
    """The JDs in the current batches, and the LLM screen's kept ids -> score."""
    jds = [
        jd
        for f in sorted((results / "batches").glob("batch-*.json"))
        for jd in json.loads(f.read_text())
    ]
    ids = {jd["id"] for jd in jds}
    relevant = json.loads((results / "jobs-scored.json").read_text()).get("relevant", [])
    return jds, {r["id"]: r.get("score") for r in relevant if r.get("id") in ids}


def make_scorer(backend: str, results: Path, config_dir: Path) -> Callable[[dict], float | None]:
    """Build ``jd -> fit probability``, loading the brief, lane labels and keys once."""
    library = json.loads((results / "evidence-library.json").read_text())
    brief = f"{library.get('headline', '')}\n{library.get('positioningSummary', '')}"
    lanes = "; ".join(lane.label for lane in load_lanes(config_dir))
    keys = DecisionKeys()
    return lambda jd: fit(build_state(jd, brief), backend, keys, lanes=lanes)


# Shadow 2026-10-21: no score-4+ offer scored below 0.26 on Jev (118 checked); ~30% of JDs fall
# below 0.25.
GATE_BACKEND = "jev"
GATE_THRESHOLD = 0.25


def gate(
    jds: list[dict],
    results_dir: Path,
    *,
    score: Callable[[dict], float | None],
    threshold: float = GATE_THRESHOLD,
) -> list[dict]:
    """Return the JDs worth an LLM screen; record each skipped one in ``skipped.jsonl``.

    Only a confident low score skips a JD. A failed call (``None``) keeps it.
    """
    out_dir = results_dir / "decision-prefilter"
    out_dir.mkdir(parents=True, exist_ok=True)
    kept: list[dict] = []
    failed = 0
    with (out_dir / "skipped.jsonl").open("w") as fh:
        for jd in jds:
            p = score(jd)
            if p is not None and p < threshold:
                fh.write(json.dumps({"id": jd["id"], "title": jd.get("title", ""), "p": p}) + "\n")
                continue
            failed += p is None
            kept.append(jd)
    print(
        f"decision gate ({GATE_BACKEND} < {threshold}): skipped {len(jds) - len(kept)} of "
        f"{len(jds)}; {failed} kept after a failed call -> {out_dir / 'skipped.jsonl'}"
    )
    return kept


def main(backend: str = "jev", sample: int = 500, seed: int = 0) -> None:
    """Score a stratified sample with ``backend``, save it, and print the shadow report."""
    settings = AppSettings()
    results = settings.results_dir
    jds, kept = _screened(results)
    # Reproducible sampling, not cryptography.
    rng = random.Random(seed)  # noqa: S311  # nosec B311
    pos = [jd for jd in jds if jd["id"] in kept]
    neg = [jd for jd in jds if jd["id"] not in kept]
    picked = rng.sample(pos, min(sample // 2, len(pos))) + rng.sample(
        neg, min(sample // 2, len(neg))
    )
    score = make_scorer(backend, results, settings.config_dir)
    out_dir = results / "decision-prefilter"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with (out_dir / f"{backend}.jsonl").open("w") as fh:
        for jd in picked:
            p = score(jd)
            row = {"id": jd["id"], "kept": jd["id"] in kept, "score": kept.get(jd["id"]), "p": p}
            fh.write(json.dumps(row) + "\n")
            rows.append(row)
    kept_share = len(pos) / len(jds) if jds else 0.0
    print(
        f"{backend}: scored {len(rows)} ({len(pos)} kept / {len(neg)} dropped in the full screen)"
    )
    print("threshold  recall_kept  recall_score4  dropped_caught  escalated  est_drop_share")
    for t in THRESHOLDS:
        r = report_row(rows, threshold=t, kept_share=kept_share)
        s4 = "n/a" if r["recall_score4"] is None else f"{r['recall_score4']:.1%}"
        print(
            f"{t:>9.2f}  {r['recall_kept']:>11.1%}  {s4:>13}  "
            f"{r['dropped_caught']:>14.1%}  {r['escalated']:>9}  {r['est_drop_share']:>14.1%}"
        )
