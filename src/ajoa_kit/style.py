"""Resolve the user's writing-style inputs for the Stage-3 tailor pass (#16).

The candidate drops their own CV / cover-letter samples and/or a tone preference into a
git-ignored ``config/style.json``; the tailor workflow then writes in that voice while the
evidence library supplies the facts (US5). Precedence, per artifact: a writing SAMPLE wins
over a TONE string, which wins over a neutral default (the agent's own professional voice).

Preview the resolved directives before a run (also validates ``config/style.json``)::

    ajoa-kit style          # human-readable
    ajoa-kit style --json   # the {cv, coverLetter} object to pass as the workflow `style` arg

``config/style.json`` — all keys optional::

    {
      "tone": "Direct, technical, understated; short sentences; no buzzwords.",
      "cv_sample": "style/my-cv.md",
      "cover_letter_sample": "style/my-cover-letter.md"
    }
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

from ajoa_kit.models import StyleBrief
from ajoa_kit.settings import AppSettings

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_CAP = 6000  # chars of a writing sample passed to the agent (bounds prompt size)
STYLE_FILE = "style.json"


def _read_sample(config_dir: Path, rel: str) -> str:
    """Read a writing sample under config_dir, capped; fail loud if it is missing."""
    path = config_dir / rel
    if not path.is_file():
        raise FileNotFoundError(f"style sample not found: {path} (referenced in {STYLE_FILE})")
    return path.read_text()[:SAMPLE_CAP]


def load_style(config_dir: Path) -> StyleBrief:
    """Load ``config/style.json`` and resolve its sample files into a :class:`StyleBrief`.

    A missing ``style.json`` yields a neutral (empty) brief; a referenced-but-missing
    sample file raises (the user pointed at something that is not there).

    Args:
        config_dir: The config root (from ``AppSettings``).

    Returns:
        The resolved style brief.
    """
    path = config_dir / STYLE_FILE
    if not path.is_file():
        return StyleBrief()
    cfg = json.loads(path.read_text())
    return StyleBrief(
        tone=cfg.get("tone", "") or "",
        cv_sample=_read_sample(config_dir, cfg["cv_sample"]) if cfg.get("cv_sample") else "",
        cover_letter_sample=(
            _read_sample(config_dir, cfg["cover_letter_sample"])
            if cfg.get("cover_letter_sample")
            else ""
        ),
    )


def directive(brief: StyleBrief, kind: str) -> str:
    """Build the style instruction for an agent (``kind`` is ``cv`` or ``cover_letter``).

    Precedence: a writing sample for this artifact wins over the tone string, which wins
    over a neutral default (empty string — the agent uses its own professional voice).

    Args:
        brief: The resolved style brief.
        kind: ``"cv"`` or ``"cover_letter"``.

    Returns:
        The instruction text, or ``""`` when nothing is configured.
    """
    sample = brief.cv_sample if kind == "cv" else brief.cover_letter_sample
    if sample:
        return (
            f"Match the candidate's own writing style, shown verbatim in this sample:\n\n{sample}"
        )
    if brief.tone:
        return f"Write in this tone: {brief.tone}"
    return ""


def as_directives(brief: StyleBrief) -> dict[str, str]:
    """Return the ``{cv, coverLetter}`` directive object the workflow takes as its ``style`` arg."""
    return {"cv": directive(brief, "cv"), "coverLetter": directive(brief, "cover_letter")}


def main(config_dir: Path | None = None, as_json: bool = False) -> None:
    """Preview the resolved style directives; reads ``--json`` from argv when called directly.

    Args:
        config_dir: The config root (defaults to ``AppSettings().config_dir``).
        as_json: Emit the workflow ``style`` arg object instead of a human-readable summary.
    """
    if config_dir is None:
        parser = argparse.ArgumentParser(prog="ajoa-kit style")
        parser.add_argument("--json", action="store_true", help="Emit the workflow `style` arg.")
        as_json = parser.parse_args().json
        config_dir = AppSettings().config_dir
    directives = as_directives(load_style(config_dir))
    if as_json:
        print(json.dumps(directives, indent=2, ensure_ascii=False))
        return
    for kind, text in directives.items():
        print(f"[{kind}] {text or '(neutral — no style configured)'}")


if __name__ == "__main__":
    main()
