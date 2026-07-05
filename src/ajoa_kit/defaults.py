"""In-code defaults mirroring the tracked ``config/`` SSOT files (#249 slice B).

Pure data, no I/O: the pre-filter keyword vocabulary, the canonical position lanes, and the ingest
tuning constants. The tracked ``config/keywords.json`` / ``config/lanes.json`` are the canonical
sources — the lists here are the no-config fallbacks the loaders in :mod:`ajoa_kit.ingest` use when
the file is absent, and drift-guard tests assert file == mirror. Keep both generic: the keyword
terms become the published trend keys (never personal/identifying vocabulary — point
``AJOA_CONFIG_DIR`` at a private dir for your own set).
"""

from __future__ import annotations

from ajoa_kit.models import Lane

DESC_CAP = 4000  # chars of description kept per JD (bounds the later relevance-pass tokens)

# --- Structured pre-filter ------------------------------------------------------------
# Coarse, cheap cut BEFORE the LLM relevance pass: keep only JDs whose ATS department
# (or, for RSS, title) matches an interest term. Matched on WORD BOUNDARIES so "ai" does
# not match "maintenance". A deliberately generous cut on a clean taxonomy field — the
# LLM gate does the lane-level nuance.
FILTER_ATS_BY_DEPARTMENT = True  # Greenhouse/Ashby/Recruitee expose a clean `department`
FILTER_RSS_BY_TITLE = True  # RSS has no department; match the role title instead
# Keyword sets are English-only; locale/i18n keyword support is tracked in #31.
INTEREST = [
    "engineer",
    "engineering",
    "software",
    "developer",
    "development",
    "infrastructure",
    "platform",
    "devops",
    "sre",
    "site reliability",
    "architect",
    "architecture",
    "system",
    "systems",
    "backend",
    "fullstack",
    "full stack",
    "full-stack",
    "ai",
    "ml",
    "machine learning",
    "mlops",
    "data",
    "security",
    "cloud",
    "technical",
    "founding",
    "applied",
]
# Stricter set for the ATS *title* fallback (when department is empty/non-matching):
# core eng role nouns, so broad dept words do not pull in non-eng titles via the title.
TITLE_ROLES = [
    "engineer",
    "engineering",
    "developer",
    "software",
    "architect",
    "architecture",
    "devops",
    "sre",
    "site reliability",
    "platform",
    "infrastructure",
    "backend",
    "fullstack",
    "full stack",
    "full-stack",
    "mlops",
    "founding",
]

# Canonical position lanes — the in-code fallback when ``config/lanes.json`` is absent; the tracked
# file is the cross-runtime lane SSOT, loaded by :func:`ajoa_kit.ingest.load_lanes` (the JS workflow
# fallbacks mirror it too). Built from plain dicts (``gapHint`` alias) so the literals mirror
# config/lanes.json exactly.
_DEFAULT_LANE_DEFS = [
    {
        "key": "cxo",
        "label": "(fractional) CxO — fractional CTO / Chief AI Officer / technical advisor",
        "focus": "early-stage leadership; reframe breadth as a product/systems-level asset",
        "gapHint": "no evidence of leading people / teams",
    },
    {
        "key": "founding",
        "label": "founding engineer / first technical hire",
        "focus": "0->1 startup; breadth, autonomy, ship end-to-end solo, set up practice from zero",
        "gapHint": "scaling / team-leadership experience",
    },
    {
        "key": "engineering",
        "label": "software engineer (senior IC)",
        "focus": (
            "backend / platform / systems; production-grade engineering "
            "(typing, testing, systems design)"
        ),
        "gapHint": "solo / no-team, no production-at-scale ops",
    },
    {
        "key": "ml",
        "label": "AI / ML engineer — applied AI, LLM apps, agentic systems",
        "focus": (
            "building WITH models: agent orchestration, RAG, evals / observability, model "
            "integration and AI product features; the agentic / applied-AI work as the "
            "throughline, not generic backend"
        ),
        "gapHint": (
            "applied / integration depth rather than foundational ML research or large-scale "
            "model training"
        ),
    },
    {
        "key": "fde",
        "label": "forward-deployed / solutions engineer",
        "focus": (
            "customer-facing applied engineering: integrate and deploy the product into "
            "enterprise environments, build bespoke solutions, bridge engineering and customer; "
            "the solo end-to-end shipping breadth is the asset"
        ),
        "gapHint": "less direct enterprise customer-facing / pre-sales / large-account experience",
    },
    {
        "key": "cloud",
        "label": "cloud / DevOps / platform engineer",
        "focus": "CI/CD, supply-chain security, reusable CI actions, containerization",
        "gapHint": "thin on cloud-provider infra at scale, IaC, production ops / observability",
    },
    {
        "key": "architect",
        "label": "software / systems architect",
        "focus": (
            "ADR/MADR culture, system design, multi-repo governance, doc hierarchies, "
            "contract-driven design"
        ),
        "gapHint": "architecture is solo / greenfield, not enterprise-scale or cross-team",
    },
]
DEFAULT_LANES = [Lane.model_validate(d) for d in _DEFAULT_LANE_DEFS]
