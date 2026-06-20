"""Application-field schema for the Stage-3 prefill pack (#50).

Greenhouse is the one ATS that exposes its application question schema with no auth
(``GET boards-api.greenhouse.io/v1/boards/<slug>/jobs/<id>?questions=true`` — see
``research.md`` §Delivery); this normalizes that payload into a flat field list and
renders it as a checklist. For any other ATS, fall back to :data:`GENERIC_FIELDS` — Ashby's public
job-board GET carries no question schema (verified, #56), and Lever/Workable are submit-key-gated.

Preview the fields for an offer (Greenhouse fetch needs the polyfetch env)::

    ajoa-kit prefill-fields --ats greenhouse --slug acme --job-id 123
    ajoa-kit prefill-fields                 # generic fallback field set

READ-ONLY: this fetches the public question schema only. It never submits — the prefill
pack is assembled for a human to review and submit manually (no auto-apply).
"""

from __future__ import annotations

import argparse

# Standard application fields, used when an ATS does not expose its schema publicly.
GENERIC_FIELDS: list[dict] = [
    {
        "name": "first_name",
        "label": "First name",
        "required": True,
        "type": "input_text",
        "values": [],
    },
    {
        "name": "last_name",
        "label": "Last name",
        "required": True,
        "type": "input_text",
        "values": [],
    },
    {"name": "email", "label": "Email", "required": True, "type": "input_text", "values": []},
    {"name": "phone", "label": "Phone", "required": False, "type": "input_text", "values": []},
    {
        "name": "resume",
        "label": "Resume / CV",
        "required": True,
        "type": "input_file",
        "values": [],
    },
    {
        "name": "cover_letter",
        "label": "Cover letter",
        "required": False,
        "type": "input_file",
        "values": [],
    },
    {
        "name": "linkedin",
        "label": "LinkedIn URL",
        "required": False,
        "type": "input_text",
        "values": [],
    },
    {
        "name": "website",
        "label": "Website / portfolio",
        "required": False,
        "type": "input_text",
        "values": [],
    },
]


def parse_greenhouse_questions(job: dict) -> list[dict]:
    """Normalize a Greenhouse ``?questions=true`` job payload into a flat field list.

    Args:
        job: The job object returned with ``questions=true``.

    Returns:
        One ``{name, label, required, type, values}`` dict per form field; ``values`` holds
        the option labels for selects (empty otherwise).
    """
    fields: list[dict] = []
    for q in job.get("questions", []):
        label = q.get("label", "")
        required = bool(q.get("required", False))
        for f in q.get("fields", []):
            fields.append(
                {
                    "name": f.get("name", ""),
                    "label": label,
                    "required": required,
                    "type": f.get("type", ""),
                    "values": [v.get("label", "") for v in f.get("values") or []],
                }
            )
    return fields


def render_fields(fields: list[dict]) -> str:
    """Render a field list as a markdown checklist (one bullet per field).

    Args:
        fields: Normalized fields (from :func:`parse_greenhouse_questions` or
            :data:`GENERIC_FIELDS`).

    Returns:
        Markdown, one ``- **Label** (required) — `name` [type] — options: ...`` line per field.
    """
    lines: list[str] = []
    for f in fields:
        req = " (required)" if f.get("required") else ""
        options = f.get("values") or []
        opts = f" — options: {', '.join(options)}" if options else ""
        lines.append(
            f"- **{f.get('label', '')}**{req} — `{f.get('name', '')}` [{f.get('type', '')}]{opts}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def fetch_greenhouse_questions(slug: str, job_id: str) -> list[dict]:
    """Fetch + normalize a Greenhouse board's public application question schema (no auth)."""
    # lazy: keep pure logic importable w/o polyfetch
    from polyfetch_scrape import FetchError, fetch  # pyright: ignore[reportMissingImports]

    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}?questions=true"
    r = fetch(url, headers={"Accept": "application/json"})
    if r.status != 200:
        raise FetchError(f"HTTP {r.status} ({r.backend})")
    import json

    return parse_greenhouse_questions(json.loads(r.body))


def main(ats: str | None = None, slug: str | None = None, job_id: str | None = None) -> None:
    """Print the application-field checklist for an offer (Greenhouse schema or generic).

    Args:
        ats: ``"greenhouse"`` to fetch the live schema; anything else uses the generic set.
        slug: Greenhouse board slug (required when ``ats == "greenhouse"``).
        job_id: Greenhouse job id (required when ``ats == "greenhouse"``).
    """
    if ats is None:
        parser = argparse.ArgumentParser(prog="ajoa-kit prefill-fields")
        parser.add_argument(
            "--ats", default="", help="ATS name; 'greenhouse' fetches the live schema."
        )
        parser.add_argument("--slug", default="", help="Greenhouse board slug.")
        parser.add_argument("--job-id", default="", help="Greenhouse job id.")
        ns = parser.parse_args()
        ats, slug, job_id = ns.ats, ns.slug, ns.job_id
    if ats == "greenhouse":
        if not slug or not job_id:
            raise ValueError("greenhouse needs --slug and --job-id")
        fields = fetch_greenhouse_questions(slug, job_id)
    else:
        fields = GENERIC_FIELDS
    print(render_fields(fields), end="")


if __name__ == "__main__":
    main()
