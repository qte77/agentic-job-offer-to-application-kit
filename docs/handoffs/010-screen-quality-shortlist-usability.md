# Handoff 010 — screen quality + shortlist usability

**State (2026-08-07): arc 009 closed, arc 010 opened with 10 items, none started.**
Plan: [docs/plans/010-screen-quality-shortlist-usability.md](../plans/010-screen-quality-shortlist-usability.md).
Arc 009 is closed — [its plan](../plans/009-renew-search-cv-letters.md) is history now; two items
migrated here (Phase C, second tailor round) and nothing else is stranded there.

## Read this first

The plan has **exactly one remaining-work table** (10 rows). Everything else in it — source map,
design notes, watch-outs — describes *how*, never *what is open*. If you find yourself building a
second list of open work, stop: that is the failure mode the arc rules exist to prevent.

**The plan's source map is complete.** Every file, function and line ref you need is in it, verified
on `main` after #354/#355/#358/#359/#360 merged. You should not have to re-map the codebase. If a
line number has drifted, grep the symbol — the symbol names are stable.

## What shipped in 009 (context, not work)

- **#354** `refresh` — only 404/410 expire a shortlist entry. Any `stale` flag written before this
  is suspect: a 3xx or 403 used to count as death, which buried 56 live offers in one sweep.
- **#358** `DESC_CAP` relocated off ingest to `chunk`. It was truncating **80%** of JDs (4 632 of
  5 773; median length exactly 4 000). Also `content_hash` now digests the capped slice so the
  relocation did not reclassify 6k records — **verified 0 of 7 997 changed**. Also adds the #348
  lane-grounding guard, and the `>=`→`==` fix after the truncation check false-positived on every
  long JD.
- **#359** two dead Greenhouse boards dropped (`fireworksai`, `dbtlabsinc`); 142 → 140 sources.
- **#360** advisory location/work-authorization flagging + `lychee.toml` accepting 429.
- **Phase B** evidence library rebuilt (24 projects) after 7 attempts; **Phase D** 12 packs + the
  HumanLayer pack regenerated; 8 corpus-delisted packs archived by `mv` to `results/offers-archive/`.

Current data state: corpus **8 459**, jobs-raw **5 807** (full text, max 25 392 chars), shortlists
**614 rows / 467 live**, packs **22 live / 8 archived**, batches **21 / 825 JDs** staged.

## How to run this arc

**Order matters in exactly one place: item 1 before item 3.** The 558 RSS records were screened
with no employer name; fixing that after Phase C means paying for Phase C twice.

Suggested sequence:

1. **Item 1** (RSS company extraction) — highest leverage, purely deterministic, TDD-shaped. Three
   feeds, three known patterns, plus the two tests that actually matter: an unmatched title must
   yield `""` rather than a mangled name, and weworkremotely's `Company: Title` split must not
   invent a company from a role name containing a colon.
2. **Items 5, 6** (dashboard) — independent of everything else, small, and they make the rest of the
   arc easier to inspect. Needs `patchright install` first for e2e.
3. **Item 4** (manual-JD durability) — do it before any `ingest` run or the 5 `manual:` records die.
4. **Ask the owner for item 2** (`config/location.json`). It gates item 3's value, not its
   execution — Phase C runs fine without it, just without location flags.
5. **Item 3** (Phase C, ~2.1M tokens) once 1 and 2 are settled.
6. **Items 7, 8, 9** as capacity allows; **item 10** after 3.

## Decide-by-default

Every open decision has a default; proceed with it unattended and let the owner override:

- **Location policy absent** → run Phase C anyway; the advisory is inert and the screen behaves
  exactly as before. Do not block.
- **Phase C cross-library score noise** → accept it. Re-screening 614 back-catalogue rows costs
  ~1.6M tokens to change a decision about 12 packs.
- **workatastartup ToS unread** → tier it CAUTION and do not add it to `feeds`/`ats`. Robots being
  permissive is only half of ADR-0002.
- **Scoped extraction ambiguity** → keep `DESC_CAP` as a hard backstop after extraction. Never let
  the batch exceed it.

## Watch-outs that cost real time last session

- **`--merge` on persist, always.** A bare `persist` overwrites 614 accrued shortlist rows.
- **`env -u GH_TOKEN -u GITHUB_TOKEN`** on every `gh` and `git push` — a stale env token 401s.
  Commit with `--no-gpg-sign`.
- **`gh pr merge --squash --admin`** works for PRs you authored; bot-authored PRs (dependabot,
  github-actions) need `gh pr review --approve` first because the ruleset sets
  `require_code_owner_review: true`.
- **polyfetch's Chromium is gone** — a `uv run` in that checkout rebuilt the venv. `patchright
  install` before any UI e2e.
- **Disk at 96%.** Delete the ~94 MB of `*.pre-*` backups in `results/` listed in the plan before
  installing anything.
- **Background workflows die.** The evidence library needed 7 attempts; 5 of 12 tailor runs failed
  on session limits. Resume is cheap — cached agents replay at ~0 tokens in ~300 ms — but **persist
  each result as it lands**, because the task output files are wiped when the scratchpad is cleared.
- **Judge pack liveness on the corpus join, never a URL probe or a slug join.** `meta.json` → `id`
  matched 29/29; `last_seen != max(last_seen)` is the reliable death signal and needs no network.

## Open questions for the owner

1. `config/location.json` values — the advisory is inert until this exists (item 2).
2. Whether to restore polyfetch's Chromium now (~150–300 MB on a 96% disk) or defer UI e2e.
3. Whether `workatastartup` is wanted as a source at all, given it yields one company per fetch
   rather than a feed.

## Not this arc

HumanLayer / Lobby AI / Nomadic applications are owner work — outreach and submission are human by
policy (AGENTS.md: no automated submission).

**The research is persisted, not stranded in a transcript** — `results/company-research/`
(git-ignored, alongside the packs):

- `humanlayer.md` — RPI pipeline, the schema-level proof that no eval/goal/criterion table exists,
  unpinned skills + `permissions-mode bypass`, the agent-races pitch strategy, and the honesty
  guardrail on `skills-lock.json` (TRMNLY's prior art, not this candidate's build)
- `lobby-ai.md` — Zurich HQ, two founding roles, **highest expected value of the three** because it
  is the only one with no location or authorization blocker. Carries one OPEN ITEM: the JDs are
  JS-rendered and still uncaptured, blocked on `patchright install`
- `nomadic-ai.md` — Understanding Layer for Physical AI, 6 SF on-site roles, 3 screened at score 3,
  all scored on company context only because the role bodies were never fetched

The HumanLayer pack itself is at `results/offers/humanlayer-founding-product-engineer/`.
