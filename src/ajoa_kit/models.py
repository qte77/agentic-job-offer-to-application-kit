"""Typed L1 data contracts (ADR-0003) — every pydantic data model lives here.

Two seam families today: parse-on-read at the JS→Python boundary (the relevance workflow result —
JSON-Schema-validated JS-side but read back from a human-supplied path: :class:`ScoredItem`,
:class:`Lane`), and the publishable trend-series contracts (:class:`WeekCounts` /
:class:`DayCounts` / :class:`MonthCounts`, written as NDJSON to ``public-data/``). The Stage-3
tailor pass's resolved writing-style inputs (:class:`StyleBrief`) live here too. A ``JobRecord``
for the JD record stays a follow-up — Python-produced and Python-consumed, so always well-formed.
``AppSettings`` is config, not a data contract, and stays in :mod:`ajoa_kit.settings`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Lane(BaseModel):
    """One position lane — the canonical lane definition (ADR-0003 lane SSOT).

    The authoritative set lives in ``config/lanes.json`` and is loaded by
    :func:`ajoa_kit.ingest.load_lanes`; the two JS workflow scripts carry an in-code copy only as a
    no-config fallback. ``gap_hint`` uses the ``gapHint`` alias so a lane round-trips to the exact
    ``{key,label,focus,gapHint}`` shape the workflows expect as ``args.lanes``.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    focus: str
    gap_hint: str = Field(alias="gapHint")


class LocationPolicy(BaseModel):
    """Where the candidate can actually take a job — **advisory** input to the relevance screen.

    The screen already asks for a ``deal_breaker`` phrase but had no idea what the candidate's
    constraint was, so authorization requirements surfaced only during the tailor pass, after
    ~400k tokens per pack: a Webflow pack scored 5/5 and called it the closest skill match in the
    shortlist, then flagged Argentina-only residency as "disqualifying regardless of skill fit".

    This makes the constraint visible at screen time. It deliberately does **not** drop or rescore
    anything — sponsorship, remote exceptions and relocation are all negotiable in ways a screen
    cannot judge, so the policy annotates and the human decides.

    Mirrors :class:`Lane` as a cross-runtime SSOT: ``config/location.json`` feeds the Python side
    and ``ajoa-kit location --json`` emits the same shape for the relevance workflow's
    ``args.location``. Field aliases are camelCase so the policy round-trips unchanged.

    **Not committed.** Unlike ``config/lanes.json`` this describes a person, so it stays untracked
    under the ``config/`` ignore (same precedent as ``config/seed-candidates.json``).

    An empty policy is inert: :attr:`is_active` is False and the screen behaves exactly as before,
    so the feature ships dormant until the candidate fills it in.
    """

    model_config = ConfigDict(populate_by_name=True)

    based_in: str = Field(default="", alias="basedIn")
    """Where the candidate lives, free text (e.g. ``"Zurich, Switzerland"``)."""
    authorized_in: list[str] = Field(default_factory=list, alias="authorizedIn")
    """Regions the candidate may work in without sponsorship (e.g. ``["EU", "Switzerland"]``)."""
    remote_ok: bool = Field(default=True, alias="remoteOk")
    """Whether a remote role outside :attr:`authorized_in` is acceptable."""
    relocate_to: list[str] = Field(default_factory=list, alias="relocateTo")
    """Regions worth relocating for — friction, not a blocker."""
    notes: str = ""
    """Free text passed verbatim to the screen (visa status, notice period, hard limits)."""

    @property
    def is_active(self) -> bool:
        """True when the policy can actually exclude something.

        Without ``authorized_in`` there is no ground truth to test a JD against, so the screen is
        told to skip location filtering entirely rather than guess from ``based_in``.
        """
        return bool(self.authorized_in)


class SeniorityPolicy(BaseModel):
    """The candidate's longest single-employer tenure — **advisory** input to the relevance screen.

    Phase D of arc 009 found 5 of 12 tailored packs had no employment tenure to cite against a
    JD's stated "minimum N years in a single role" requirement — the same blind spot
    :class:`LocationPolicy` closed for authorization. Mirrors it exactly: a ``deal_breaker`` phrase
    already existed on the screen result, but nothing told the model what the candidate's own
    tenure actually was.

    This deliberately does **not** drop or rescore anything — a short tenure is often explained
    (acquisition, layoff, fixed-term contract) in ways a screen cannot judge, so the policy
    annotates and the human decides.

    **Not committed.** Describes a person, so it stays untracked under the ``config/`` ignore, same
    as ``config/location.json``.

    An empty policy is inert: :attr:`is_active` is False and the screen behaves exactly as before.
    """

    model_config = ConfigDict(populate_by_name=True)

    longest_tenure_years: float = Field(default=0.0, alias="longestTenureYears")
    """The candidate's longest continuous tenure at a single employer, in years."""
    notes: str = ""
    """Free text passed verbatim to the screen (a gap explanation, a career change, etc.)."""

    @property
    def is_active(self) -> bool:
        """True when there is a real figure to test a JD's stated tenure ask against.

        Zero (the default) means no ground truth was configured, so the screen is told to skip
        tenure flagging entirely rather than treat "unset" as "no tenure".
        """
        return self.longest_tenure_years > 0


class ManualJd(BaseModel):
    """One hand-captured JD from ``config/manual-jds.json`` — a posting no adapter can reach.

    Some employers publish roles only behind a JS accordion, a login, or a page with no feed at
    all, so the JD is captured by hand. Before this existed those records lived *only* in
    ``results/jobs-raw.json``, which :func:`ajoa_kit.ingest.main` rewrites wholesale from the pull —
    so they vanished on the next ingest and the packs grounded in them lost their JD.

    Making them config turns the loss into a reload: :func:`ajoa_kit.ingest.load_manual_jds` injects
    them into every pull, which also stops :func:`ajoa_kit.corpus.merge_corpus` from delisting them
    (a record present in ``fresh`` is never "absent from today's pull"). Removing an entry is
    therefore the deliberate way to retire one.

    Only the author-supplied fields live here; ``source``/``ats``/``fetched_backend`` are stamped by
    the loader. Aliases are camelCase to match ``config/lanes.json`` and ``config/location.json``.

    **Not committed** — ``config/`` is git-ignored wholesale, so captured JD text never enters the
    repo.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    """Stable id, conventionally ``manual:<company-slug>:<role-slug>``."""
    title: str
    company: str = ""
    company_slug: str = Field(default="", alias="companySlug")
    location: str = ""
    url: str = ""
    description: str = ""
    lane_hint: str = Field(default="", alias="laneHint")
    posted_at: str = Field(default="", alias="postedAt")
    remote: bool | None = None


class ScoredItem(BaseModel):
    """One scored JD from the relevance workflow.

    Lenient by design (``extra="allow"``, all fields optional) so a new field never drops a row;
    only a wrong-typed item (a non-numeric ``score`` or non-object entry) is dropped at the read
    boundary.
    """

    # extra="allow" keeps unknown workflow fields through model_dump(), so persist's re-write of
    # jobs-scored.json round-trips any field the relevance schema grows beyond the 12 below (#197).
    # The first 10 are the relevance RESULT schema; `stale`/`last_checked` come from refresh (#214).
    model_config = ConfigDict(extra="allow")

    id: str = ""
    title: str = ""
    company: str = ""
    best_lane: str = ""
    score: int | float | None = None
    verdict: str = ""
    rationale: str = ""
    url: str = ""
    # Human-actionable GATE-2 flags (#271): the JD's stated application deadline and a one-phrase
    # hard concern; "" = none. Optional in the JS RESULT schema, typed here (not left as extras) so
    # they survive the model pipeline (persist -> merge -> refresh) and surface in shortlist.md.
    deadline: str = ""
    deal_breaker: str = ""
    # Liveness (#214): the refresh sweep flags an offer that is filled/closed (corpus-delisted or a
    # dead URL re-probe) and stamps when last checked. Typed (not a dropped extra) so the flag
    # survives a persist round-trip and the dashboard can hide stale rows.
    stale: bool = False
    last_checked: str = ""


class WeekCounts(BaseModel):
    """One ISO week's aggregate keyword frequencies — the publishable trends contract.

    The single typed shape written to ``public-data/trends.ndjson``, read by the dashboard's pivot
    layer: ``{week, counts}`` where ``counts`` is ``{keyword: document-frequency}``. No JD content,
    company, title, or per-posting row ever appears here (ADR-0001 PII gate).
    """

    week: str
    counts: dict[str, int]


class DayCounts(BaseModel):
    """One ISO calendar day's aggregate keyword frequencies — the daily-granularity trends contract.

    Written to ``public-data/trends-daily.ndjson`` as ``{date, counts}`` (``YYYY-MM-DD``).
    Same keyword-only, no-PII guarantee as :class:`WeekCounts`; weeks are summed from these days.
    """

    date: str
    counts: dict[str, int]


class MonthCounts(BaseModel):
    """One calendar month's aggregate keyword frequencies — the monthly-granularity contract (#188).

    Written to ``public-data/trends-monthly.ndjson`` as ``{month, counts}`` (``YYYY-MM``).
    Same keyword-only, no-PII guarantee as :class:`WeekCounts`; months are summed from the days.
    """

    month: str
    counts: dict[str, int]


class CompanyRow(BaseModel):
    """One aggregated company-hiring row for the LOCAL market-intel tracker (#284).

    ``{city, region, field, company, count, momentum}`` — who's hiring, by geo x field, with a
    per-company active-role ``count`` and an optional ``heating``/``cooling``/``steady`` tag
    (``None`` until history is deep enough). ``city`` is the canonical group key (duplicate
    spellings merged); ``region`` keeps the source's state/country qualifier for display (``""``
    when absent) — nothing is dropped from the corpus.

    LOCAL-ONLY: built by ``scripts/build_ui_companies.py`` for ``make preview``, NEVER published.
    Company + geo + counts are business data the ``data``-branch boundary guard forbids (a published
    version needs an ADR-0002 ToU review first). No recruiter names/emails here.
    """

    city: str
    region: str = ""
    field: str
    company: str
    count: int
    momentum: str | None = None


class StyleBrief(BaseModel):
    """Resolved writing-style inputs for the Stage-3 tailor pass (#16).

    Empty strings mean nothing was configured. Loaded from ``config/style.json`` by
    :func:`ajoa_kit.style.load_style` and rendered to the workflow ``style`` arg by
    :func:`ajoa_kit.style.as_directives`.
    """

    tone: str = ""
    cv_sample: str = ""
    cover_letter_sample: str = ""


class PackPolicy(BaseModel):
    """Config-driven pack-selection policy — which shortlist rows earn a full tailored pack.

    ``config/pack-policy.json`` overrides the defaults (mirrors :class:`Lane`'s config
    precedent, loaded by :func:`ajoa_kit.pack_plan.load_policy`); an absent file is inert
    (``PackPolicy()``, every field default). ``ajoa-kit pack-plan``'s CLI flags override the
    loaded policy in turn (ADR-0005).
    """

    min_score: int = 5
    """Only shortlist rows scoring at or above this earn a pack."""
    max_packs: int = 0
    """Cap on the number of selected targets; ``0`` = unlimited."""
    lanes: list[str] = Field(default_factory=list)
    """Restrict selection to these lane keys; empty = every lane."""
    per_company_cap: int = 0
    """Cap on selected targets per company (after scoring); ``0`` = unlimited."""
    dedup: str = "role_x_company"
    """Dedup strategy; ``"role_x_company"`` drops a later row with the same (title, company) as
    an earlier one (case-insensitive). Any other value disables deduping."""


class OfferStatus(BaseModel):
    """One offer's local application-outcome status (#273) — set by hand via ``ajoa-kit status``.

    ``stage`` advances applied -> responded -> interview -> offer/rejected; ``date`` is the last
    update, ``notes`` a free-text memo. LOCAL-ONLY: written to ``results/offers/<slug>/status.json``
    (git-ignored PII), never published — like the offer pack it sits beside.
    """

    stage: str = ""
    date: str = ""
    notes: str = ""


# --- discovery adapters (ADR-0004): CAUTION-tier read boundaries ---------------------------------


class YcCompany(BaseModel):
    """One YC company parsed from the yc-oss hiring feed at the network read boundary (ADR-0003).

    yc-oss is a third-party daily mirror of YC's public Algolia directory -- company signal only, no
    JDs. Parsed so the ``hiring`` flag + ``slug`` can be followed to the company's public
    ``/companies/<slug>/jobs`` page. ``slug`` is required (the job-page URL cannot be built without
    it); ``tags`` feeds the relevance pre-filter.
    """

    name: str
    slug: str
    batch: str = ""
    hiring: bool = False
    tags: list[str] = Field(default_factory=list)


class AtsRef(BaseModel):
    """A first-party ATS reference (``ats`` + board ``slug``) recovered from an apply URL.

    The payoff of the startups.gallery discovery pass: an aggregator card links straight to the
    company's own ATS, so the ``(ats, slug)`` goes to the first-party ingest (clean JDs, natural
    dedup) instead of scraping the aggregator's coarse card as a terminal JD.
    """

    ats: str
    slug: str
    url: str = ""


class SgFilters(BaseModel):
    """Query filters for a startups.gallery ``/jobs`` request -- all optional, blank means unset."""

    location: str = ""
    job_title: str = ""
    company_name: str = ""


class SgJob(BaseModel):
    """One parsed startups.gallery card: apply URL + derived ATS ref + best-effort display fields.

    The title is a separate node that flattens in front of the ``Company · Location`` meta line, so
    title/company cannot be split reliably: ``heading`` is the flattened role+company text; only
    ``location`` and ``posted_at`` are cleanly delimited. The load-bearing field is ``ats_ref``.
    """

    apply_url: str = ""
    ats_ref: AtsRef | None = None
    heading: str = ""
    location: str = ""
    posted_at: str = ""
