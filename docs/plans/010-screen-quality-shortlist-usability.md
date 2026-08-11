# Plan 010 — screen quality + shortlist usability

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
| `workatastartup` | **Wanted, but opt-in** — never in `config/default-seed.json` defaults | 010, 2026-08-11 |

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

## Remaining work

One table. Source map and design notes below describe HOW; they never re-list WHAT is open.

| # | Item | Gate | Done when |
|---|---|---|---|
| 3 | Phase C — relevance over the delta *(migrated from 009)* | agent | `results/<lane>/shortlist.json` gains the delta's keepers; `jobs-scored.json` reflects them |
| 5 | UI: has-pack badge + filter | agent | a tailored row is visually distinct; filter shows only rows with `cv` |
| 6 | UI: score-desc ordering across lanes | agent | `aggregate()` output is score-ordered; a new score-4 row is not below 400 |
| 7 | Scoped extraction at chunk time | agent | batch text drops preamble/EEO/benefits; `_capped` still bounds at `DESC_CAP` |
| 8 | Tenure advisory (`SeniorityPolicy`) | agent | inert without config; flags in `deal_breaker` + `tenure_flagged_count`; never drops or rescores |
| 9 | `workatastartup` ADR-0002 evaluation | agent, **ToS read required** | tiered OK/CAUTION/BLOCKED with rationale recorded in ADR-0002; documented as an opt-in a user adds to their own `config/seed.json` — **never** added to the shipped `default-seed.json` |
| 10 | Second tailor round for Phase C keepers *(migrated from 009)* | agent, after 3 | any fresh keeper outranking a survivor has a pack; slate still capped at 12 |

**Ordering constraint — satisfied.** Item 1 had to land before item 3, and did (#363). Those 558
JDs were screened with no employer name; re-screening them after the fix is free only if it happens
in the same Phase C run, so Phase C must not run until an `ingest --merge` has backfilled the
company field into the corpus.

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

### Item 3 — Phase C

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

### Items 5–6 — dashboard

| Path | Role |
|---|---|
| `scripts/build_ui_shortlist.py:20` `aggregate` | orders by `sorted(glob(...))` then in-file score — the burial cause |
| `src/ajoa_kit/persist_offer.py:298` `attach_tailor_docs` | joins packs by JD id via `meta.json`; already correct, needs no change |
| `ui/src/shortlist.js` `tailorDoc()` | renders CV/cover-letter panes when `it.cv` is present |
| `ui/src/dom-utils.js` | the sanitiser allowlist for pack markdown |
| `Makefile` → `preview` | copies `ui/` to a temp dir and injects real data there; source `ui/` stays data-free |

### Item 7 — scoped extraction

| Path | Role |
|---|---|
| `src/ajoa_kit/chunk.py:26` `_capped` | applies `DESC_CAP` when writing batches — extend here, keep the cap as backstop |

Measured on the 4 632 capped JDs of the pre-#358 corpus: median **809 chars** before the first
substantive marker (`responsibilities|requirements|qualifications|what you'll do|who you are`), mean
978, p75 1 360, **p90 2 010**. 87% carry an "About us" blurb. EEO (10%), benefits (11%) and comp
(16%) are rare *because they sat past the old cap*. Marker regex was loose, biasing the offset low.

### Item 8 — tenure advisory

Mirror the location implementation exactly, all shipped in #360:

| Path | Role |
|---|---|
| `src/ajoa_kit/models.py:34` `LocationPolicy` | the model to copy (aliases, `is_active`) |
| `src/ajoa_kit/ingest.py:73` `load_location` | the loader to copy |
| `src/ajoa_kit/__main__.py:106` `_location` | the CLI to copy |
| `.claude/workflows/cc-workflow-relevance.js` | the prompt block + `location_flagged_count` to copy |

**AHA caution:** two constraint models will tempt an extraction into a shared `CandidateConstraints`.
The repo rule is extract at the *third* use. Duplicate for tenure; extract only if a third
constraint (comp floor, clearance) appears.

### Item 9 — workatastartup under ADR-0002

| Path | Role |
|---|---|
| `docs/decisions/0002-source-tos-tiers.md` | the tiering rationale to extend |
| `config/default-seed.json` → `discovery` | holds `yc-oss` today — **discovery only, inert to the ingest loader** |
| `src/ajoa_kit/verify_sources.py` `_reachable` | treats 3xx as live; the reachability convention |

Verified 2026-08-07: `workatastartup.com/robots.txt` is `User-Agent: * / Disallow:` — nothing
disallowed. `ycombinator.com/robots.txt` disallows `/companies?*`. The page is structurally
consistent (one page per company; roles with title, location, comp, equity) so it would parse with
no LLM tier. **Two blockers:** the YC Terms have not been read (robots is only half of ADR-0002),
and the page says "Sign up to see more" — unauthenticated access yields one company at a time, not
a feed.

### Item 11 — ADR-0002 and hand-captured JDs · SHIPPED

As built: ADR-0002 gained a Context paragraph scoping `config/manual-jds.json` out of the tiering, a
"Hand capture is bounded by conduct, not by destination" subsection under Decision, and a
Consequences bullet on the freshness asymmetry. The ADR is the single source — do not restate it
here.

Verified against `refresh.py` rather than assumed: `is_delisted:40` can never fire for a manual
entry (injection pins `last_seen` to the newest pull), while `mark:79` does re-probe `probe(it.url)`
and `classify:53` still flags on `GONE_STATUSES = {404, 410}`. All 7 entries carried careers-page
URLs at the time, so none could expire — hence the "capture the posting's URL" advice.

## Watch-outs

- **`--merge` is mandatory on persist.** A bare `persist` overwrites the accrued shortlists — 614
  rows across 7 lanes as of 2026-08-07. `_evict_ids` also moves an id out of other lanes when its
  `best_lane` changes; expect lane counts to shift on merge.
- **Cross-library score comparability.** The 614 existing rows were scored against the *pre-rebuild*
  evidence library (before 2026-07-29). Phase C scores under the current one. A "5" from June and a
  "5" from Phase C are not the same judgement. Re-screening the back catalogue is ~16 batches
  (~1.6M tokens) if that ever matters enough.
- **`--admin` merges your own PRs, not bot-authored ones.** The `default` ruleset sets
  `require_code_owner_review: true`; admin override clears it for PRs you authored but not for
  dependabot/github-actions PRs, which need an explicit `gh pr review --approve`.
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
- Items 5–6 are rendering/wiring: `make ui_check` / `make ui_e2e`, not unit tests
- Item 3's precondition (the item-1 backfill): re-run `ingest --merge` and confirm the
  Companies-hiring "Unknown" row drops from 244
- Item 3: `results/<lane>/shortlist.json` row counts grow; spot-check that `deal_breaker` carries
  location constraints once item 2 is done

## Not in this arc

The **HumanLayer / Lobby AI / Nomadic applications** are owner work, not agent work — outreach and
submission are human by policy (AGENTS.md: no automated submission). Research for those lives in
this session's transcript and in `results/offers/humanlayer-founding-product-engineer/`.
