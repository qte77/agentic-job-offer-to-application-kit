"""Deterministic keyword-stuffing check for a tailored CV (issue #272).

Keyword stuffing — cramming a résumé with a repeated keyword, a copy-pasted phrase, or a
dense skill-dump line to game ATS keyword-matching — is dishonest and detectable
(research.md §ATS). The tailor CV prompt already forbids it and the optional critique loop
trims it; this is the deterministic backstop, a sibling of
``ats_check.parse_safety_warnings`` that ``persist_offer`` surfaces as ``cv-stuffing-check.md``
whenever it flags anything. Heuristic and non-blocking: warnings are review aids, not errors,
and the thresholds are deliberately conservative so an honest CV never trips them.

Pure, no I/O — mirrors ``ats_check`` so it stays importable without the network layer.
"""

from __future__ import annotations

import re
from collections import Counter

# Content-word tokenizer: a token starts with a letter and may carry tech punctuation so
# ``c++`` / ``c#`` / ``node.js`` stay whole. The caller case-folds first.
_WORD = re.compile(r"[a-z][a-z0-9+#.\-]*")
# High-frequency words carrying no keyword signal — excluded so they neither count as the
# "stuffed keyword" nor pad the density denominator. Kept as a plain string (split at import,
# not a list literal) so the set stays readable on a few lines.
_STOPWORDS = (
    "the a an and or but of to in on at for with by from as is are was were be been being "
    "it its this that these those i my me we our you your they their he she his her not no so "
    "than then over into out up down more most also can will would"
)
_STOP = frozenset(_STOPWORDS.split())
_MIN_LEN = 3  # shorter tokens are too noisy to weigh for density

# Thresholds — conservative so an honest, keyword-rich CV stays clean.
_MIN_TOKENS = 40  # below this there are too few content words to judge density
_DENSITY = 0.06  # one keyword owning > 6% of content words reads as stuffing
_MIN_REPEAT = 6  # ...and it must recur enough times to be deliberate
_NGRAM_N = 3
_NGRAM_REPEAT = 4  # the same three-word phrase 4x+ is copy-paste stuffing
_LIST_SEP = re.compile(r"[,/|·;]")
_LIST_MIN_ITEMS = 25  # a single line dumping 25+ short items is a keyword wall
_LIST_MAX_WORDS = 3  # ...where each "item" is a keyword, not prose


def _content_tokens(cv_md: str) -> list[str]:
    """Lowercase content words (len >= _MIN_LEN, non-stopword) in document order."""
    return [t for t in _WORD.findall(cv_md.lower()) if len(t) >= _MIN_LEN and t not in _STOP]


def _density_warning(tokens: list[str]) -> str | None:
    """Flag a single keyword that owns an implausible share of the content words."""
    if len(tokens) < _MIN_TOKENS:
        return None
    word, count = Counter(tokens).most_common(1)[0]
    if count >= _MIN_REPEAT and count / len(tokens) >= _DENSITY:
        pct = round(100 * count / len(tokens))
        return f"keyword '{word}' is {pct}% of content words ({count}x) — keyword stuffing"
    return None


def _ngram_warning(tokens: list[str]) -> str | None:
    """Flag a three-word phrase copy-pasted well past honest repetition."""
    if len(tokens) < _NGRAM_N:
        return None
    grams = Counter(tuple(tokens[i : i + _NGRAM_N]) for i in range(len(tokens) - _NGRAM_N + 1))
    gram, count = grams.most_common(1)[0]
    if count >= _NGRAM_REPEAT:
        return f"phrase '{' '.join(gram)}' repeated {count}x — copy-paste stuffing"
    return None


def _list_warning(cv_md: str) -> str | None:
    """Flag one line that dumps a wall of short, keyword-only items."""
    for line in cv_md.splitlines():
        parts = [p.strip() for p in _LIST_SEP.split(line) if p.strip()]
        if len(parts) >= _LIST_MIN_ITEMS and max(len(p.split()) for p in parts) <= _LIST_MAX_WORDS:
            return f"one line lists {len(parts)} short items — dense skills-list stuffing"
    return None


def stuffing_warnings(cv_md: str) -> list[str]:
    """Return keyword-stuffing warnings for a markdown CV (empty list = clean).

    Args:
        cv_md: The tailored CV as markdown.

    Returns:
        Human-readable warnings, one per detected stuffing pattern.
    """
    text = cv_md or ""
    tokens = _content_tokens(text)
    checks = (_density_warning(tokens), _ngram_warning(tokens), _list_warning(text))
    return [w for w in checks if w]
