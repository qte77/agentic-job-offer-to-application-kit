# Plan 009 — renew the local job search, CV and letters

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
`a2ui-agui-kit`, `fo-scraper-miwi`, `agenthud-agui-a2ui`, `ai-agents-research`, `polyfetch-scrape`,
`claude-code-plugins`. **Not covered — `agentic-cax-gauge`, `__SABI`, `protocols`**: all three exist
and are recent but small (11 / 19 / 2 commits), and `maxProjects: 24` selected 24 of 84 workspace
repos, so they lost the cut.

**Side effect of the same cap:** ~10 repos that *were* in the 06-29 library dropped out, notably the
`gha-*` Actions family (`gha-issue-triage`, `gha-sbom-action`, `gha-llms-txt-action`,
`gha-rxiv-feed-action`, `gha-rxiv-paper-eval`, `gha-arbitrary-repo-timeline`) plus
`polyforge-orchestrator`, `vlm-toolkit`, `diagramforge`. That thins the cloud/DevOps lane's evidence
(only `gha-sec-feed` survives from that family). The tailor workflow reads the *new* library only.

**Owner decision (2026-08-03): re-resume at `maxProjects: 34`.** In flight on the same run id, so
the 24 mined projects replay from cache and only the new repos plus a fresh assemble cost tokens.
Note the inventory agent's prompt embeds the cap, so that one agent always re-runs; if it renames or
re-paths a project, that project's miner re-runs too.

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

### Phase C — re-screen the delta

`Workflow({ scriptPath: '.claude/workflows/cc-workflow-relevance.js', args: { rootDir: '.',
batchCount: 21 }})` → `make persist FILE=<out.json>` **with `--merge`** (union by id; a bare
`persist` overwrites the accrued shortlists). ~100k tokens/batch → ~2.1M.

**Done when** `results/<lane>/shortlist.json` gains the delta's keepers and `jobs-scored.json`
reflects them.

### Phase D — re-tailor, capped at 12

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
