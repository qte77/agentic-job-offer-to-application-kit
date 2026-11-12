# Plan 009 — renew the local job search, CV and letters

> **CLOSED 2026-08-07.** Every item below is shipped, except two that migrated to
> [plan 010](010-screen-quality-shortlist-usability.md): **Phase C** (re-screen the delta) and the
> **second tailor round** that follows it. Nothing is stranded here. This file is history — do not
> add work to it.
>
> **Shipped:** Phase A (hygiene) · Phase B (evidence library, 24 projects) ·
> Phase B2 [#358](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/358) ·
> Phase D (12 packs + HumanLayer regenerated, 8 archived) ·
> PRs [#354](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/354)
> [#355](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/355)
> [#358](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/358)
> [#359](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/359)
> [#360](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/360).

**Goal.** Refresh the whole local pipeline end to end: live-only shortlists, a portfolio-current
evidence library, a re-screened corpus delta, and up to 12 re-tailored application packs.

**Trigger.** The evidence library was built 2026-06-29 and misses ~10 July-active repos — including
this kit at v0.8.0. Every CV and cover letter downstream inherits that gap, so re-tailoring against
the old library would only restate the same claims.

## Owner decisions (settled 2026-07-28)

| Decision | Choice |
|---|---|
| Evidence library | **Full rebuild**, `maxProjects: 24` |
| Phase D scope | Top fresh + surviving old packs, **capped at 12** |
| Non-survivors | **Archive, never delete** |
| Execution | Phase A first, check in, then B→D |

## Phases

### Phase A — hygiene, no LLM · DONE

1. `refresh` — reconcile shortlists vs corpus + read-only re-probe.
2. `verify-sources` — re-stamp `_date_verified`.
3. `scripts/ingest.sh --merge` → `ajoa-kit chunk --new`.

Result: corpus 7 563 → **7 997** (434 new / 396 changed / 2 224 delisted); delta batched to
**21 batches / 830 JDs** (`results/batches/manifest.json`); sources **140/142** live.

**Defect found and fixed mid-phase** — see `refresh.classify` below. PR
[#354](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/354).

### Phase B — evidence-library rebuild · DONE (2026-07-29), one gap open

```text
Workflow({ scriptPath: '.claude/workflows/cc-workflow-evidence-library.js', args: {
  workspaceRoot: '/workspaces/qte77', account: 'qte77',
  profileRepo: '/workspaces/qte77/qte77', leanAwayFrom: '', maxProjects: 24 }})
```

Run id `wf_bc321d71-472` — landed on the **4th** resume (51 agents, 0 errors). The three earlier
attempts died mid-run, twice on session limits and once on a process exit; each resume replayed the
cached miners and got further (26 → 36 → 55 → complete). Written to `results/evidence-library.json`
(117 KB, 24 `perProject`, 16 master bullets, 14 skill clusters). The 06-29 library is kept as
`results/evidence-library.2026-06-29.json` so bullet drift is diffable.

**Done-when: 9 of 12.** Covered — this kit, `claude-azure-workflows-gui`, `web-recon-kit`,
`a2ui-agui-kit`, a private scraper sibling repo, `agenthud-agui-a2ui`, `ai-agents-research`,
`polyfetch-scrape`, `claude-code-plugins`. **Not covered — `agentic-cax-gauge`, a private sibling repo, `protocols`**: all three exist
and are recent but small (11 / 19 / 2 commits), and `maxProjects: 24` selected 24 of 84 workspace
repos, so they lost the cut.

**Side effect of the same cap:** ~10 repos that *were* in the 06-29 library dropped out, notably the
`gha-*` Actions family (`gha-issue-triage`, `gha-sbom-action`, `gha-llms-txt-action`,
`gha-rxiv-feed-action`, `gha-rxiv-paper-eval`, `gha-arbitrary-repo-timeline`) plus
`polyforge-orchestrator`, `vlm-toolkit`, `diagramforge`. That thins the cloud/DevOps lane's evidence
(only `gha-sec-feed` survives from that family). The tailor workflow reads the *new* library only.

**Resolved 2026-08-07: shipped at 24.** The `maxProjects: 34` re-resume was attempted and its
assemble step was **rejected by the schema** (`must have required property 'toneApplied'`) before it
could return; the run was interrupted mid-retry. The recovered draft held 31 projects — it gained
a private repo (2 060 commits, never mined before), `gha-rxiv-feed-action` and `gha-sec-feed-eval`, but
**lost `qte77`, the profile repo** — so the owner chose the schema-valid 24-project library already
on disk. `agentic-cax-gauge`, a private sibling repo, and `protocols` remain uncovered, and 5 of the 7 original
`gha-*` repos are still absent. Not carried into arc 010: the 24-project library grounds every
current pack and no downstream work is blocked by it.

### Phase B2 — JD grounding fixes · SHIPPED [#358](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/358)

`DESC_CAP` was a relevance-pass budget applied at the ingest layer, and the tailor pass reads the
same stored record — so packs were grounded in a partial JD. Measured: **4632 of 5773 JDs (80.2%)**
sat at the cap, median description length exactly 4000. 87% of capped JDs carry a front-loaded
company blurb while EEO/benefits/comp appear in only 10–16%, because those live at the end and were
already truncated — the cap kept marketing and discarded requirements.

`normalize.html_to_text` now stores the whole posting; `chunk._capped` applies the cap when writing
batches. Two changes make that safe: `content_hash` digests `description[:DESC_CAP]` (**verified: 0
of 7997 corpus records change**, avoiding a one-off ~150-batch re-screen), and `merge_corpus` adopts
fresh content on the *unchanged* branch, which is where every backfill lands — the old
`{**old, ...}` would have frozen all 6063 truncated rows permanently.

Also ships `persist_offer.lane_angle_warning` → `lane-grounding-check.md` (#348), the deterministic
half of that issue; the immediate half was resolved by the rebuild (all 7 `{lane}Angle` present).

### Phase C — re-screen the delta · MIGRATED to [plan 010](010-screen-quality-shortlist-usability.md) item 3

Staged but never run: 21 batches / 825 JDs at `results/batches/manifest.json`. Moved because the
558 RSS records it would screen carry no company name — plan 010 item 1 fixes that first.

<details><summary>original section</summary>

`Workflow({ scriptPath: '.claude/workflows/cc-workflow-relevance.js', args: { rootDir: '.',
batchCount: 21 }})` → `make persist FILE=<out.json>` **with `--merge`** (union by id; a bare
`persist` overwrites the accrued shortlists). ~100k tokens/batch → ~2.1M.

**Done when** `results/<lane>/shortlist.json` gains the delta's keepers and `jobs-scored.json`
reflects them.

</details>

### Phase D — re-tailor, capped at 12 · DONE (2026-08-07)

**Shipped.** All 12 slate packs regenerated against the rebuilt library, plus a 13th for
HumanLayer. Zero `jd-truncation-check.md` and zero `lane-grounding-check.md` across them — the
practical proof that #358's two fixes hold. 8 corpus-delisted packs archived by `mv` to
`results/offers-archive/` (moved, never deleted). The **second tailor round** for Phase C keepers
migrated to [plan 010](010-screen-quality-shortlist-usability.md) item 10.

<details><summary>original section</summary>

**Owner decision (2026-08-03): run D before C** — re-tailor the surviving packs now, then screen the
delta and tailor any fresh winner in a second round. Costs more in total (some offers get tailored
twice) but puts current CVs in hand sooner.

```text
Workflow({ scriptPath: '.claude/workflows/cc-workflow-tailor-offer.js',
           args: { rootDir: '.', lane: '<lane>', offerId: '<id>', critique: true } })
uv run ajoa-kit persist-offer <out.json>
uv run ajoa-kit ats-check results/offers/<slug>/cv.md
uv run ajoa-kit render-pdf results/offers/<slug>/cv.md   # needs: uv sync --extra pdf
```

~300–600k tokens each → ~4–7M for 12. **Done when** each pack has all 8 artifacts and `ats-check`
passes. Archive non-survivors to `results/offers-archive/<slug>/` — **move, never delete**.

**The slate is already computable, offline.** Every pack's `meta.json` carries its corpus id, so the
liveness join needs no network — `last_seen != max(last_seen)` is the same signal `refresh.is_delisted`
uses, and it was never the buggy branch. As of the 2026-07-28 pull: **29/29 packs join**, **6 are
corpus-delisted** (`anthropic-applied-ai-beneficial-deployments`, `cadaico-ai-engineer-chat-to-cad`,
`rimini-street-…-forward-deployed-engineer`, `rockstar-technical-ai-solution-architect`,
`stellar-ai-senior-software-engineer`, `stripe-backend-engineer-ai-security`) and **23 are alive**,
of which **12 score 5** — exactly filling the cap. Ties at 5 need a tiebreak (confidence, then
recency).

</details>

## Source map

| Path | Role |
|---|---|
| `src/ajoa_kit/refresh.py:49` `GONE_STATUSES` · `:53` `classify` | liveness rule — **fixed this arc**, only 404/410 expire |
| `src/ajoa_kit/refresh.py:40` `is_delisted` | `last_seen != latest_pull`; the reliable death signal |
| `src/ajoa_kit/slug_probe.py:21` `fetch_status` | read-only probe; does **not** follow redirects (deliberate — see below) |
| `src/ajoa_kit/verify_sources.py:40` `_reachable` | already treats 3xx as live; the convention `refresh` now matches |
| `src/ajoa_kit/persist_offer.py` | `ARTIFACTS`, `strip_frontmatter` — writes the 8-file pack |
| `.claude/workflows/cc-workflow-{evidence-library,relevance,tailor-offer}.js` | the three LLM phases; each header documents its `args` |
| `config/default-seed.json` | 142 sources; `greenhouse/dbtlabsinc` is a hard 404 — drop it |
| `results/batches/manifest.json` | `batch_count: 21` — Phase C's `batchCount` |

## Watch-outs

- **Do not "fix" the probe by following redirects.** Greenhouse serves its job-removed page as
  `?error=true` with HTTP **200**, so a follow-based rule marks dead offers live. Corpus-delisting
  is the reliable signal; the probe only catches sources we stopped tracking.
- **Pack ↔ corpus id join is unverified.** Joining `results/offers/<slug>/meta.json` `offer_id`
  against corpus ids returns "absent" for all 29 packs, while the same ids join fine against
  shortlist entries. Do not archive on the corpus join — use the `refresh` sweep's `stale` flag.
- `persist` without `--merge` overwrites accrued shortlists.
- Network subcommands need the [venv-borrow](../../CONTRIBUTING.md#polyfetch-venv-borrow); plain
  `uv run ajoa-kit ingest` fails.
- `env -u GH_TOKEN -u GITHUB_TOKEN` on every `gh` / `git push`.

## Handoff

The session handoff for this arc, merged in from the former `docs/handoffs/` folder (one file per arc). Historical: this arc is closed.

> **CLOSED 2026-08-07.** Arc complete. Two items migrated to
> [handoff 010](010-screen-quality-shortlist-usability.md) / [plan 010](010-screen-quality-shortlist-usability.md):
> Phase C and the second tailor round. **Start there, not here.**
>
> Final state: PRs #354 #355 #358 #359 #360 merged · evidence library rebuilt (24 projects) ·
> 12 slate packs + HumanLayer regenerated with zero truncation and zero lane-grounding warnings ·
> 8 corpus-delisted packs archived by `mv` · corpus 8 459 · jobs-raw 5 807 with full JD text ·
> shortlists 614 rows / 467 live · 21 batches / 825 JDs staged for Phase C.
>
> The blockers this handoff listed are resolved: #354 merged, and the `refresh` re-sweep was
> superseded — pack liveness is judged on the corpus join (`meta.json` → `id`, 29/29 matched),
> which needs no network.

**Historical record below — superseded by the banner above.** Plan:
[docs/plans/009-renew-search-cv-letters.md](009-renew-search-cv-letters.md). Arc 008
(`render-pdf`) is closed and shipped — nothing migrated from it.

### What shipped

- [x] **Phase A hygiene.** `refresh` + `verify-sources` + `ingest --merge` + `chunk --new`.
      Corpus 7 563 → **7 997**; delta = **21 batches / 830 JDs**; sources **140/142** live.
- [x] **PR [#354](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/354)** —
      `fix(refresh): only 404/410 expire a shortlist entry`. CI green, **merged 2026-08-07**.
- [x] **PR [#358](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/358)** —
      `fix(chunk): relocate DESC_CAP off ingest; add lane-grounding check`. Fixes the grounding half
      of #347 (the cap truncated **80%** of ingested JDs) and ships #348's deterministic guard.
      Hash stability verified against the live corpus: **0 of 7997** records reclassify.
- [x] **Phase B evidence library.** `wf_bc321d71-472` landed on the 4th resume (51 agents, 0
      errors); `results/evidence-library.json` = 117 KB / 24 projects / 16 master bullets / 14 skill
      clusters. Old library kept at `results/evidence-library.2026-06-29.json`. **Coverage is 9 of
      the 12 repos the done-when named** — see the plan's Phase B for the gap and the open cap
      decision.

### The defect, because it changes how you read old sweeps

`refresh.classify` treated any non-2xx probe as proof of death. Board URLs 301 to the canonical
posting (Stripe/Databricks `gh_jid` links) and WeWorkRemotely answers an unattended probe with 403 —
so the 2026-07-28 sweep buried **56 live offers**. Verified: `direct=301 follow=200 ->
stripe.com/jobs/listing/staff-engineer-agentic-commerce/8047789`.

Fix narrows the kill rule to `GONE_STATUSES = {404, 410}`. **Any `stale` flag written before this
fix is suspect** — the shortlists currently on disk were flagged by the old rule and must be
re-swept before Phase D picks packs.

### Blocked / resume order — RESOLVED, kept for history

Both blockers cleared on 2026-08-07: #354 merged (along with #355/#358/#359/#360), and the
owner-gated `refresh` re-sweep was superseded rather than run — pack liveness is judged on the
corpus join, which needs no network. The resume order that lived here is finished except for
Phase C and the second tailor round, both now
[plan 010](010-screen-quality-shortlist-usability.md) items 3 and 10.

### Watch-outs

- **Never resolve liveness by following redirects** — Greenhouse's job-removed page is HTTP 200.
- **The corpus-id join is sound — an earlier version of this file said otherwise and was wrong.**
  Join on `results/offers/<slug>/meta.json` → `id`, not on the slug: **29/29 match**. That gives a
  network-free liveness signal (`last_seen != max(last_seen)`, the same one `refresh.is_delisted`
  uses and never the buggy branch), so archiving and the Phase D ranking do **not** wait on the
  owner-gated sweep.
- **The new library is not a superset of the old one.** `maxProjects: 24` over 84 repos dropped ~10
  projects the 06-29 library had, incl. six `gha-*` Actions repos — the cloud/DevOps lane keeps only
  `gha-sec-feed` from that family. The cap decision was settled on 2026-08-07: **ship at 24** (the
  34-cap assemble was schema-rejected and its draft lost the `qte77` profile repo). Tailoring reads
  the 24-project library; lane evidence for cloud/DevOps stays thin by choice.
- `persist` without `--merge` overwrites the accrued shortlists.
- Phase D at 12 packs ≈ 4–7M tokens; Phase C ≈ 2.1M.
- `env -u GH_TOKEN -u GITHUB_TOKEN` on every `gh` / `git push`; commit with `--no-gpg-sign`.
