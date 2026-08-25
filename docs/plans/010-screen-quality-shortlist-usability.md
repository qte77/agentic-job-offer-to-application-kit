# Plan 010 — screen quality + shortlist usability

> **CLOSED 2026-08-25.** All 13 items shipped. Nothing migrates — every open thread this arc raised
> is resolved (including item 9's finding, which reversed the arc's own earlier assumption; see
> that item's source-map entry). This file is history — do not add work to it.
> [Arc 011](011-pack-coverage-and-output-eval.md) is the active plan for anyone picking up work
> next; it was scoped independently, not as a continuation of this arc's backlog.

**Opened 2026-08-07**, migrating the one unfinished item from
[arc 009](009-renew-search-cv-letters.md) (Phase C) plus the defects and deferred work that arc
surfaced. Handoff: [docs/handoffs/010-screen-quality-shortlist-usability.md](../handoffs/010-screen-quality-shortlist-usability.md).

## Why this arc exists

Arc 009 renewed the CVs and letters — 12 packs regenerated plus HumanLayer, 8 stale packs archived.
Running it exposed four problems that are all about *the screen and the shortlist*, not about
tailoring:

1. **558 corpus records have no company name.** Every one is `ats: rss`. They were screened without
   the employer being known, and they collapse into a single "Unknown / 244" row in the
   Companies-hiring tab.
2. **Manually captured JDs do not survive an ingest.** `ingest` rewrites `results/jobs-raw.json`
   wholesale, so the five `manual:` records (HumanLayer, Nomadic ×4) vanish on the next pull and
   their packs lose the JD they are grounded in.
3. **The dashboard cannot distinguish a tailored row from an untailored one.** 22 of 467 rows carry
   a pack; the other 445 correctly show nothing, but nothing marks which is which, and the tailored
   rows sit scattered from position 2 to 460.
4. **Newly added offers are born at the bottom.** `aggregate()` orders by lane-file glob then score,
   and `engineering` holds 369 of 467 rows — so HumanLayer landed at row 417 and Nomadic ML at 467.

Plus the screen improvements arc 009 deferred: scoped extraction, and a tenure advisory mirroring
the location one that shipped in [#360](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/360).

## Owner decisions carried in

| Decision | Choice | Source |
|---|---|---|
| Location handling | **Advisory, never a filter** — flag in `deal_breaker`, never drop or rescore | 009, shipped #360 |
| Tenure handling | Same shape as location — advisory | 009 review |
| Phase D cap | 12 packs | 009 |
| Non-survivor packs | Archive by `mv`, never delete | 009 |
| `workatastartup` | ~~Wanted, but opt-in~~ — item 9's ADR-0002 evaluation (2026-08-25) found BLOCKED, not opt-in-able: no listings feed without auth, YC's own ToU bars scraping/data-mining. **Superseded**: paste-only hand capture only (already the case for HumanLayer) | 010, 2026-08-11; corrected 2026-08-25 |

## Shipped

- **Item 1** — RSS company extraction, [#363](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/363).
  557 of 558 records recovered (258 distinct employers); the one miss carries no separator, so `""`
  is correct. Salary bands captured too (363). `title` left verbatim, so the corpus backfills for
  free on the next pull. **The item-3 ordering constraint is now satisfied.**
- **Item 4** — manual-JD durability, [#364](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/364).
  `config/manual-jds.json` + `ingest.with_manual`; injection on every pull is what also stops
  `merge_corpus` delisting them. **The 5 in-flight records were migrated into the config and 2
  Lobby AI roles added — 7 entries, verified byte-identical to the live `jobs-raw.json` rows apart
  from the new `salary` key.** The next `ingest --merge` is now safe to run.
- **Item 11** — ADR-0002 scope + the manual-JD freshness caveat,
  [#368](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/368). Hand capture is
  now bounded by **conduct, not destination**, and the ADR records that `refresh` can only expire a
  manual entry through its `url` — so capture the posting's URL, not a careers page.
- **Item 2** — `config/location.json` written 2026-08-11 (owner: authorized in EU / Switzerland / US,
  `remoteOk`). The advisory is active. Its `notes` ask the screen to surface a citizenship-or-visa-only
  requirement verbatim in `deal_breaker` while never dropping or downscoring the role — the owner
  wants the pack built anyway, with the blocker named in it.
- **Item 3** — Phase C, run 2026-08-11 over the delta (not the full back-catalogue). `ingest --merge`
  first: corpus 8 459 → 9 161, **0 blank companies among live records** (the #363 backfill landed) and
  all 7 manual entries survived. `refresh` then flagged 146 of 614 rows stale. `chunk --new` cut the
  delta to 366 (214 first seen that day, 152 content-changed) → 10 batches; the screen kept **84**,
  dropped 282, and `persist --merge` folded them in with 0 malformed / 0 un-laned / 0 invalid-lane.
  Shortlists 614 → 687 rows, 541 live. **Screened with the advisory inert** — `args.location` was
  omitted, see the item-3 note below.
- **Item 10** — Phase D, 2026-08-11. **12 packs, all persisted** (`results/tailor-slate-20260811.json` is
  the slate; per-offer JSON kept as `results/tailor-<company>-20260811.json`). Must-have coverage ran
  86% (DeepJudge) down to 33% (Stripe); **screen score barely predicted pack quality** — the best pack
  was a score-4 picked only for being the sole Swiss row, the two worst were a 5 and a 4. Recurring
  non-technical blockers across the twelve: no production traffic/SLO/on-call (8), no employment
  tenure to cite (5), no peer review (5), no customer-facing ownership (4). Three packs correctly
  refused to guess at facts the repo cannot know (degree, C1 German, years employed).

## Remaining work

**None — this arc is closed.** Item 14 shipped 2026-08-25. Source map and design notes below
describe HOW each item was built; the "Shipped" section above and the source map's `· SHIPPED`
markers are the record of WHAT.

## Source map

Exact anchors, verified 2026-08-07 on `main` after #354/#355/#358/#359/#360 merged. Line numbers
drift — grep the symbol if it has moved.

### Item 1 — RSS company extraction · SHIPPED #363

As built: `normalize.rss_company_salary(source, title)` holds one regex per feed
(`Title @ Company [CHF band]` · `Company: Title` · `Title // Company`) and `from_rss` calls it.
Unregistered feed or non-conforming title → `("", "")`, never a guess. weworkremotely splits on the
first colon **followed by a space** — that is what keeps `https://shiperp.com/: PHP Web Developer`
whole and stops a role name's own colon from inventing an employer.

`title` is left verbatim because it is a `corpus._CONTENT_FIELDS` member (`title`, `location`,
`description`); `company`/`salary` are unhashed, so the `merge_corpus` unchanged-branch adoption
added in #358 backfills them on the next pull with no re-screen. **The corpus still holds the old
blank values until an `ingest --merge` runs** — that pull is a precondition for item 3.

### Item 3 — Phase C · SHIPPED 2026-08-11

| Path | Role |
|---|---|
| `.claude/workflows/cc-workflow-relevance.js` | the screen; `LOCATION`/`LOCATION_ACTIVE` near the config block, prompt assembled in `gatePrompt()` |
| `results/batches/manifest.json` | read `batch_count` before every invocation — `chunk --new` rewrites it (2026-08-11: `{total_jobs: 366, batch_size: 40, batch_count: 10}`) |
| `src/ajoa_kit/persist_scored.py:110` `write_shortlists` · `:122` `_union_by_id` · `:130` `_evict_ids` | the merge path |
| `src/ajoa_kit/chunk.py:39` `_new_offers` · `:55` `main` | re-chunk if the delta must be rebuilt |

```text
uv run ajoa-kit location --json                 # -> paste as args.location (see below)
Workflow({ scriptPath: '.claude/workflows/cc-workflow-relevance.js',
           args: { rootDir: '.', batchCount: <manifest.batch_count>,
                   location: { ...ajoa-kit location --json... } } })
uv run ajoa-kit persist <out.json> --merge      # --merge is MANDATORY, see watch-outs
```

**`args.location` is not read from disk.** `LOCATION = cfg.location || null` — the workflow never
opens `config/location.json`, so omitting the arg silently screens with the advisory inert even when
the file exists and `ajoa-kit location` reports it active. Same for `args.lanes` (the hardcoded
fallback happens to match `config/lanes.json` today; do not rely on it).

### Item 4 — manual-JD durability · SHIPPED #364

As built: `ingest.load_manual_jds` (mirrors `load_lanes`/`load_location`) + `ingest.with_manual`,
which appends manual records to the pull and reuses `dedupe`, so a pulled record with the same id
wins on order alone. **`merge_corpus` needed no change** — injecting on every run means a manual
record is never "absent from today's pull", so the delisting branch never sees it.

### Items 5–6 — dashboard · SHIPPED #384 #385

As built (#384 — score ordering): `build_ui_shortlist._score_key` sorts `aggregate()`'s output by
`score` descending, stably, after the source-path collection — equal scores keep their prior
(lane-path, then in-file) order, so the snapshot stays deterministic. `bool` is excluded explicitly
(it subclasses `int`; a stray `true` would otherwise rank as score 1); missing/`None`/non-numeric
`score` sorts to `-inf` (bottom), never raises, never displaces a real row.

As built (#385 — has-pack badge + filter): `renderShortlist(items, laneLabel, filter, packOnly)`
gained a fourth param — `it.cv` is the marker field (the first artifact `attach_tailor_docs` joins
onto a row), so `packOnly` narrows to rows that actually went through tailoring. A `pack` badge
renders next to any row carrying `cv`. The text filter and the pack toggle **compose**: `app.js`
repaints from both control values together on every keystroke/click, rather than each listener
reading only its own event target (which would drop the other control's state).

| Path | Role |
|---|---|
| `scripts/build_ui_shortlist.py` `_score_key` / `aggregate` | the score-desc sort (#384) |
| `src/ajoa_kit/persist_offer.py:298` `attach_tailor_docs` | joins packs by JD id via `meta.json`; unchanged — already correct |
| `ui/src/shortlist.js` `renderShortlist` | `packOnly` filter + `pack` badge render (#385) |
| `ui/src/app.js` | wires `#filter` + `#filter-pack` to a shared repaint (#385) |
| `Makefile` → `preview` | copies `ui/` to a temp dir and injects real data there; source `ui/` stays data-free |

### Item 7 — scoped extraction · SHIPPED #395

As built: `chunk._scoped()` trims to the substantive body, then `_capped()` applies `DESC_CAP` as
the backstop. Over the 9 159-record corpus: 86.6% of postings scope (median 34.4% of chars dropped,
p90 55.8%, max 75.0%) and **2 636 JDs that the cap previously truncated now fit under it whole**.

**The plan's premise was wrong and the corpus corrected it.** This section originally assumed
section headings. In fact **99.9% of descriptions contain no newline at all** (5 of 9 159 — HTML is
stripped at ingest), so a line-anchored pattern matched **0.0%** of the corpus; the first
implementation was a silent no-op that only the corpus measurement caught. Markers must be matched
mid-string, which makes a prose hit the live risk. Three guards bound it: `PREAMBLE_WINDOW` (2 500)
for the opening marker, `TAIL_FRACTION` (0.6) for the closing one, and `MIN_KEEP_RATIO` (0.25),
which rejects any slice retaining too little. The floor is load-bearing — without it a stray
"...your role, keeping our systems running..." cut a 3 165-char JD to 64 chars; bare `the role` /
`your role` / `your mission` were dropped from the pattern for the same reason.

The earlier pre-#358 measurement quoted here (median 809 chars of preamble, 87% "About us") used a
loose marker regex and a line-anchored reading; treat the figures above as the current ground truth.

### Item 8 — tenure advisory · SHIPPED

As built: `models.SeniorityPolicy` (`longest_tenure_years: float`, `notes: str`, `is_active` =
`longest_tenure_years > 0`) — a near-literal copy of `LocationPolicy`, deliberately smaller (tenure
needed one figure, not four fields, so the mirror is in shape and pattern, not field-for-field).
`ingest.load_tenure` / `__main__._tenure` / the `tenure` subparser copy `load_location` /
`_location` exactly. The relevance workflow gained `TENURE`/`TENURE_ACTIVE` beside
`LOCATION`/`LOCATION_ACTIVE`, a `tenure` prompt block mirroring the `location` one verbatim in
structure ("NEVER drops a JD and NEVER changes a score" / flags `deal_breaker` + counts in
`tenure_flagged_count`), and the trailing prompt sentence extended the same way
`LOCATION_ACTIVE` was.

The AHA extraction question this section originally raised (`CandidateConstraints` shared model) is
now moot in its original form: two constraints exist (`LocationPolicy`, `SeniorityPolicy`) but they
were duplicated, not extracted, per the repo rule (extract at the *third* use) — still correctly
duplicated, only if a third constraint (comp floor, clearance) appears.

| Path | Role |
|---|---|
| `src/ajoa_kit/models.py` `SeniorityPolicy` | the model, next to `LocationPolicy` |
| `src/ajoa_kit/ingest.py` `load_tenure` | the loader, next to `load_location` |
| `src/ajoa_kit/__main__.py` `_tenure` | the CLI, next to `_location` |
| `.claude/workflows/cc-workflow-relevance.js` | `TENURE`/`TENURE_ACTIVE` + the `tenure` prompt block + `tenure_flagged_count` |
| `config/tenure.json` | untracked, mirrors `config/location.json`; absent file is inert |

### Item 9 — workatastartup under ADR-0002 · SHIPPED #404

**Tiered BLOCKED, not opt-in-able — the plan's own "wanted, but opt-in" framing above is
superseded.** Two independent grounds, either alone sufficient:

- **Structural.** Unauthenticated access serves one company at a time behind "Sign up to see more"
  — no listings feed exists to poll. ADR-0002's own BLOCKED definition includes "there is no public
  listings API"; this is that case regardless of the ToS question below.
- **Legal.** `robots.txt` stayed permissive on re-verification (2026-08-25, unchanged from
  2026-08-07). But Y Combinator's own Terms of Use (`ycombinator.com/legal#tou`, fetched this
  session) states verbatim: *"You agree not to...engage in or use any data mining, robots, scraping
  or similar data gathering or extraction methods."* `workatastartup.com/terms` self-titles as "Y
  Combinator's Work at a Startup" terms, and YC's own legal hub lists no separate WaS terms document.

**One gap, disclosed rather than glossed over:** `workatastartup.com/terms`'s own page body could
not be directly read — it is client-rendered with no server-side text (confirmed: the raw HTML
payload contains zero occurrences of "scraping"/"robots"/"automated"/"data mining" — the terms text
loads via JS after load), and the local headless-Chromium reinstall needed to render it failed on
`ENOSPC` (disk space in this session's container, not a site block or a ToS restriction). The
structural ground doesn't depend on resolving this gap.

**What this actually changes:** nothing operational — `config/default-seed.json` never carried this
source and still doesn't. What changes is the plan's own owner-decision row above, which pre-dated
this evaluation and assumed an eventual opt-in path; BLOCKED forecloses that. The correct path for
a wanted workatastartup posting is unchanged from what already happened for HumanLayer: paste-only
hand capture into `config/manual-jds.json`, governed by "conduct, not destination" (ADR-0002),
never a recurring adapter.

| Path | Role |
|---|---|
| `docs/decisions/0002-source-tos-tiers.md` | the tiering rationale, now extended with this finding |
| `config/default-seed.json` → `discovery` | holds `yc-oss` today — **discovery only, inert to the ingest loader**; unaffected by this finding (a different YC surface, ADR-0004 governs it) |
| `src/ajoa_kit/verify_sources.py` `_reachable` | treats 3xx as live; the reachability convention — not applicable here, this source never enters `feeds`/`ats` |

### Item 12 — geo blind spot · SHIPPED #403

As built: `companies.parse_geo(location, remote, source)` gained a `source` parameter — when the
text carries no region qualifier, it falls back to `_SOURCE_REGION.get(source, "")` (one entry:
`{"swissdevjobs": "Switzerland"}`), a fallback for a gap, never an override of a stated qualifier.
`city` is never touched by the fallback — it stays honestly `"Unknown"` when the text gives no city,
satisfying "no fabricated `location` written into records" precisely: the record itself is never
mutated, and even the derived `city` bucket is never invented, only `region`, and only from a feed
whose every listing is verifiably one country. Both call sites (`aggregate_companies`,
`companies_trend.geo_field_key`) now pass `rec.get("source", "")` through.

Measured on the live corpus: 391 of 391 `swissdevjobs` records carry a blank `location` (confirmed,
not assumed — the premise holds, unlike item 7's). Post-fix, `aggregate_companies` output: 187
active-record rows moved from `(Unknown, "")` to `(Unknown, "Switzerland")`; 64 rows remain
genuinely unresolved (other blank-location sources with no known feed-geo mapping) — expected
residual, not a regression.

| Path | Role |
|---|---|
| `src/ajoa_kit/companies.py` `parse_geo` / `_SOURCE_REGION` | the fallback and its one-entry map |
| `src/ajoa_kit/companies.py` `aggregate_companies` | passes `rec.get("source", "")` through |
| `src/ajoa_kit/companies_trend.py` `geo_field_key` | passes `job.get("source", "")` through — this is the publishable geo-by-field path, so the fix also corrects `public-data/hiring-*.ndjson`, not just the local Companies tab |

### Item 13 — manual JDs scored · SHIPPED

As run: `ingest --merge` (corpus 9 161 → 10 148, all 9 manual ids present, 143/143 sources ok) →
`chunk --new` (49 batches from the delta — only Cardinal ×2 landed there; Nomadic Chief of Staff
and Lobby AI ×2 had unchanged content, so their `last_changed` predated this pull and they never
entered the `--new` delta). Re-screening all 49 batches to reach 3 records would have cost
~4.9M tokens for a goal only about these ids, so instead: a standalone one-off batch
(`results/batches-manual/batch-000.json`, built with the same `chunk._capped` transform every other
batch gets) held exactly the 5 unscored ids, screened via one relevance-workflow call
(`batchDir` override, `batchCount: 1`, ~94k tokens) and persisted with `--merge`.

**Result — 8 of 9 in a shortlist, 1 provably dropped:** HumanLayer (4, pre-existing), Nomadic ML/BE/FE
(3 each, pre-existing), Lobby AI Founding Senior Engineer (4/founding), Lobby AI Founding AI Engineer
(4/ml), Cardinal Founding Engineer (4/founding), Cardinal Founding Product Engineer (3/founding,
maybe). **Nomadic Chief of Staff scored below 3** in the same screen — a real LLM judgement, not a
silent gap — closing the item.

### Item 11 — ADR-0002 and hand-captured JDs · SHIPPED

As built: ADR-0002 gained a Context paragraph scoping `config/manual-jds.json` out of the tiering, a
"Hand capture is bounded by conduct, not by destination" subsection under Decision, and a
Consequences bullet on the freshness asymmetry. The ADR is the single source — do not restate it
here.

Verified against `refresh.py` rather than assumed: `is_delisted:40` can never fire for a manual
entry (injection pins `last_seen` to the newest pull), while `mark:79` does re-probe `probe(it.url)`
and `classify:53` still flags on `GONE_STATUSES = {404, 410}`. All 7 entries carried careers-page
URLs at the time, so none could expire — hence the "capture the posting's URL" advice.

### Item 14 — partial manual captures completed · SHIPPED #405

As run, 2026-08-25: 5 of 9 manual JDs (arc 009's own captures) carried only a summary, with the
full role body sitting behind an unfetched link. Resolved differently per source:

- **Nomadic AI ×4** (ML, Backend, Frontend, Chief of Staff) — the marketing site's "Apply" buttons
  turned out to link straight to **public, no-auth Ashby postings**
  (`jobs.ashbyhq.com/Pear-VC/...`) — an OK-tier ATS this project already fetches, not a login wall.
  Fetched all 4 directly (`polyfetch fetch <url> --tier patchright --show-body`, no click-automation
  needed), confirmed each title matched before trusting the link order, and replaced the partial
  `description` in `config/manual-jds.json` with the full body. Re-ran `ingest --merge` afterward so
  `results/jobs-raw.json` carries the fuller text too (corpus 10 148 → 10 154, all 9 manual ids
  still present). No existing pack referenced any of the 4 (`results/offers/` has no `nomadic*`
  dir), so nothing needed regenerating.
- **HumanLayer** — genuinely blocked, not just unattempted. `workatastartup.com`'s "View job" click
  was tried (`render_session` + `click_text("View job")`): same URL, same body text before and
  after — a no-op, meaning the full JD requires a login this ADR (item 9, same session) already
  found the site's own Terms of Use bars automating around. Stayed on the done-when's other branch:
  its pack (`results/offers/humanlayer-founding-product-engineer/`) already discloses the partial
  capture across `match.md`, `gap-report.md`, `prefill-pack.md` and `coverage-report.md` — verified
  present, not assumed.

**Watch-out for whoever hits a `.pre-*`/browser-blocked task next:** the local headless-Chromium
reinstall this required (`polyfetch doctor --fix`, unsandboxed) failed once on `ENOSPC` before
succeeding on retry — disk fluctuated between 362 MB and 714 MB free over the session with no
action from this session freeing it (other, unrelated projects' `/tmp` data). Re-check `df` before
concluding a browser-install failure means the target site is blocking you.

`config/manual-jds.json` is git-ignored (describes a person) — this change has no commit of its
own; the record of it lives here and in the corpus/jobs-raw.json regen.

## Watch-outs

- **`--merge` is mandatory on persist.** A bare `persist` overwrites the accrued shortlists — 614
  rows across 7 lanes as of 2026-08-07. `_evict_ids` also moves an id out of other lanes when its
  `best_lane` changes; expect lane counts to shift on merge.
- **Cross-library score comparability.** The 614 existing rows were scored against the *pre-rebuild*
  evidence library (before 2026-07-29). Phase C scores under the current one. A "5" from June and a
  "5" from Phase C are not the same judgement. Re-screening the back catalogue is ~16 batches
  (~1.6M tokens) if that ever matters enough.
- **`--admin` merges PRs authored by the sole code owner (qte77), not any other author.** The
  `default` ruleset sets `require_code_owner_review: true`; this blocks bots (dependabot,
  github-actions) **and other human accounts** (e.g. dntywntme) identically — all need an explicit
  `gh pr review --approve` from qte77 first. A comment saying "approved" does not count; verify with
  `gh pr view <n> --json reviews` before trusting a claim that one landed.
- **`env -u GH_TOKEN -u GITHUB_TOKEN` on every `gh` and `git push` — both, always.** Unsetting only
  `GH_TOKEN` falls through to the devcontainer's `GITHUB_TOKEN`, an installation token whose writes
  fail `403 Resource not accessible by integration` while reads succeed. It reads as a revoked
  account, not a shadowed token, and `repos/…/permissions` reports `admin: true` throughout (that is
  the user's role, not the token's grant). `gh auth status` is the tell: the stored `gho_` token
  shows `Active account: false` while a shadowing token is set. Commit with `--no-gpg-sign`.
- **polyfetch's patchright Chromium is restored** (2026-08-09) — but `patchright install` must run
  **unsandboxed**; a sandboxed run reports success, downloads 177 MB, then discards the writes to
  `~/.cache/ms-playwright`. `make ui_e2e` / `make ui_shots` work again (items 5–6 verification).
- **Disk.** The ~94 MB of `*.pre-*` session backups are deleted; 1.7 GB free after the browser
  install. `evidence-library.2026-06-29.json` was kept — the plan wants bullet drift diffable.
- **Do not follow redirects to decide liveness.** Greenhouse's job-removed page returns HTTP 200.
- **Never archive on a slug join.** Join packs to corpus on `meta.json` → `id` (29/29 matched);
  slug-keyed joins report everything absent.

## Verification

- `make check` — ruff lint + format, pyright, complexipy, offline pytest at CI parity
- `make docs_lint` — markdownlint + lychee (429 now accepted; see #360)
- Items 5–6, as shipped: #384's `_score_key` sort got unit tests (`tests/test_build_ui_shortlist.py`)
  since it's pure Python; #385's badge/filter is rendering/wiring, covered by `make ui_check` /
  `make ui_e2e`, not unit tests
- Item 8, as shipped: `load_tenure` got the same two-test pattern as `load_location`
  (`tests/test_ingest.py`) — inert-without-a-file, and alias round-trip. The prompt-block change in
  `cc-workflow-relevance.js` has no unit coverage (same as `location`'s — it is exercised live, not
  in CI, since the relevance pass needs an LLM)
- Item 9, as shipped: no test (governance research, not code) — verified `robots.txt` fresh via
  WebFetch, YC's Terms of Use fetched and quoted verbatim, the WaS-specific terms-page gap disclosed
  in the ADR rather than assumed away
- Item 12, as shipped: `tests/test_companies.py` (`parse_geo`'s fallback, non-override, inert-for-
  unmapped-sources, and one `aggregate_companies` integration case) + `test_companies_trend.py`
  (`geo_field_key`'s publishable-key format). Also verified against the live corpus — 391/391
  swissdevjobs blank, 187 rows fixed
- Item 13, as shipped: no unit test (it's a live pipeline run, not code) — verified by re-checking
  all 9 manual ids against `results/<lane>/shortlist.json` post-persist; `persist --merge` reported
  0 malformed / 0 un-laned / 0 invalid-lane
- Item 14, as shipped: no unit test (config data, not code) — verified via `ingest.load_manual_jds`
  loading all 9 through the real `ManualJd` pydantic model post-edit, a byte-diff confirming only
  the 4 Nomadic `description` fields changed (every other field and every other entry untouched),
  and `results/jobs-raw.json` re-checked post-`ingest --merge` to confirm the fuller text actually
  propagated, not just the config source
- Item 3's precondition (the item-1 backfill): re-run `ingest --merge` and confirm the
  Companies-hiring "Unknown" row drops from 244
- Item 3: `results/<lane>/shortlist.json` row counts grow; spot-check that `deal_breaker` carries
  location constraints once item 2 is done

## Not in this arc

The **HumanLayer / Lobby AI / Nomadic applications** are owner work, not agent work — outreach and
submission are human by policy (AGENTS.md: no automated submission). Research for those lives in
this session's transcript and in `results/offers/humanlayer-founding-product-engineer/`.
