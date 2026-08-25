# Handoff 010 — screen quality + shortlist usability

**State (2026-08-25): items 1, 2, 3, 4, 5, 6, 7, 10 and 11 shipped** ([#363](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/363), [#364](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/364), [#368](https://github.com/qte77/agentic-job-offer-to-application-kit/issues/368), [#384](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/384), [#385](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/385), [#395](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/395)); **5 items open, none owner-gated.**
Also merged: [#362](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/362) — the
python-deps bump. It carried ruff **0.16**, which formats Python code blocks inside Markdown by
default, so `ruff format --check .` now covers `docs/`. One plan snippet needed reformatting; expect
`make check` to police code blocks in every doc you write from here on.
Plan: [docs/plans/010-screen-quality-shortlist-usability.md](../plans/010-screen-quality-shortlist-usability.md).
Arc 009 is closed — [its plan](../plans/009-renew-search-cv-letters.md) is history now; two items
migrated here (Phase C, second tailor round) and nothing else is stranded there.

## Read this first

The plan has **exactly one remaining-work table** (5 rows: items 8, 9, 12, 13, 14 — the last three opened by an earlier session's audits). Everything else in it — source map,
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

Phases B/C/D are done. Items 5, 6, 7 (dashboard usability + scoped extraction) are also done —
[#384](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/384),
[#385](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/385),
[#395](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/395). What remains is the
arc's own backlog plus three findings an earlier session's audits opened.

1. **Item 13 first among the remaining rows** — one `ingest --merge` + `chunk --new` + relevance pass
   puts the 5 unscored manual JDs (Cardinal ×2, Lobby AI ×2, Nomadic Chief of Staff) into a shortlist,
   and the same pass sweeps whatever else the pull brings. Cheapest way to stop flying blind on them.
2. **Item 12** (geo blind spot) before any further Swiss selection — six score-4 Swiss roles were
   missed by a `location`-based filter because RSS records carry none. The six are captured in
   `results/swiss-candidates-20260811.json` with language / EU-EEA blockers already flagged.
3. **Items 8, 9, 14** as capacity allows.

**Owner decisions carried in 2026-08-11:** location policy is EU / Switzerland / US with `remoteOk`,
and a citizenship-or-visa-only requirement is surfaced in `deal_breaker` but never drops a role — the
pack still gets built with the blocker named. `workatastartup` is wanted but opt-in only.

## Decide-by-default

Every open decision has a default; proceed with it unattended and let the owner override:

- **Location policy absent** → run Phase C anyway; the advisory is inert and the screen behaves
  exactly as before. Do not block.
- **Phase C cross-library score noise** → accept it. Re-screening 614 back-catalogue rows costs
  ~1.6M tokens to change a decision about 12 packs.
- **workatastartup ToS unread** → tier it CAUTION and do not add it to `feeds`/`ats`. Robots being
  permissive is only half of ADR-0002.
- **Scoped extraction ambiguity** → settled in #395: `DESC_CAP` is applied after extraction as the
  hard backstop, and the batch never exceeds it. Note for anything else that parses JD text —
  descriptions are flat single-line prose (99.9% carry no newline, HTML is stripped at ingest), so
  line-anchored patterns match nothing. Measure against `results/corpus.json`, not just unit tests.

## Watch-outs that cost real time last session

- **`--merge` on persist, always.** A bare `persist` overwrites 614 accrued shortlist rows.
- **`env -u GH_TOKEN -u GITHUB_TOKEN`** on every `gh` and `git push` — **both**, not just
  `GH_TOKEN`. Unsetting one falls through to the other, and the devcontainer's `GITHUB_TOKEN` is an
  installation token: reads succeed, writes fail `403 Resource not accessible by integration`. It
  looks exactly like a revoked account (2026-08-10 cost two failed writes and a wrong diagnosis).
  `gh auth status` is the tell — the stored `gho_` token shows `Active account: false` while a
  shadowing token is set. Commit with `--no-gpg-sign`.
- **`gh pr merge --squash --admin`** works for PRs authored by the sole code owner (qte77); every
  other author — bots (dependabot, github-actions) **and other human accounts** (e.g. dntywntme) —
  hits `Waiting on code owner review from qte77` and needs a real `gh pr review --approve` from
  qte77 first (a comment saying "approved" does not count — check `gh pr view <n> --json reviews`
  before trusting it). The `require_code_owner_review: true` ruleset rule drives this; `reviewDecision`
  does not reliably reflect it (it reflects classic branch protection) — the merge attempt itself, or
  the `reviews` array, is the authoritative check.
- **polyfetch's Chromium keeps vanishing** — gone twice (2026-08-09, 2026-08-11), each time
  surfacing only as "Executable doesn't exist" mid-fetch. `patchright install` must run
  **unsandboxed** (`dangerouslyDisableSandbox`): a sandboxed run reports success, downloads 177 MB,
  then discards the writes to `~/.cache/ms-playwright`. **Verify the binary path on disk afterwards**
  — the installer's exit code lies.
- **Disk.** The ~94 MB of `*.pre-*` backups listed in the plan are deleted. 1.7 GB free after the
  browser install; `results/` is down to 91 MB.
- **Rendering is not interacting.** A rendered-but-still-thin page may be click-gated — drive it,
  don't re-fetch it. Escalation has three tiers (static → rendered → driven) and a tier can be
  necessary without being sufficient; on Lobby AI both were true, which is why four attempts failed.
  See [AGENT_LEARNINGS](../../AGENT_LEARNINGS.md).
- **Never delegate a JSON filter to a subagent.** An audit agent asked to "load `results/corpus.json`"
  used the Read tool line-by-line, fanned out to 12 children, estimated 1.4M tokens for one scan, and
  died on the session limit. The same question is a `uv run python` one-liner costing no model tokens.
  Delegate judgement, never deterministic data crunching — and say so in the prompt.
- **Background workflows die — but resume cleanly.** The evidence library needed 7 attempts; 5 of 12
  tailor runs died on session limits (2026-08-09) and 3 of 12 died with the parent process
  (2026-08-11). `Workflow({scriptPath, resumeFromRunId})` replays finished agents from cache, but the
  run ids survive only in the launch notification — capture them. **Persist each result as it lands**:
  task output files are wiped when the scratchpad clears, and that is the only reason zero completed
  work was lost both times.
- **Judge pack liveness on the corpus join, never a URL probe or a slug join.** `meta.json` → `id`
  matched 29/29; `last_seen != max(last_seen)` is the reliable death signal and needs no network.

## Open questions for the owner

1. `config/location.json` values — the advisory is inert until this exists (item 2). **Deferred by
   the owner 2026-08-09**; Phase C proceeds without it.

**Resolved 2026-08-11.** `workatastartup` is wanted but **opt-in only** — see the plan's owner-decision
table; item 9 tiers it and documents it, and it never enters the shipped `default-seed.json`. The
stale `chore/source-freshness-20260801` branch is **deleted**: its only content beyond re-stampable
`_date_verified` dates was the two Greenhouse boards (`fireworksai`, `dbtlabsinc`) that
[#359](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/359) dropped as terminal
404s, so merging it would have resurrected two dead sources. The stray root `MEMORY.md` is deleted
and git-ignored.

## Not this arc

HumanLayer / Lobby AI / Nomadic applications are owner work — outreach and submission are human by
policy (AGENTS.md: no automated submission).

**The research is persisted, not stranded in a transcript** — `results/company-research/`
(git-ignored, alongside the packs):

- `humanlayer.md` — RPI pipeline, the schema-level proof that no eval/goal/criterion table exists,
  unpinned skills + `permissions-mode bypass`, the agent-races pitch strategy, and the honesty
  guardrail on `skills-lock.json` (TRMNLY's prior art, not this candidate's build)
- `lobby-ai.md` — Zurich HQ, two founding roles, **highest expected value of the three** because it
  is the only one with no location or authorization blocker. **OPEN ITEM resolved 2026-08-09:** both
  JDs captured (`lobby-ai-jds.md`, screenshot `lobby-ai-careers-expanded.png`) and now entries 6–7
  of `config/manual-jds.json`. Adds `$2.2M led by Founderful`, the three founders, and the JD's own
  "Evals as a Discipline" / "Minimum 8 years" / "Swiss-Based/Local" must-haves
- `nomadic-ai.md` — Understanding Layer for Physical AI, 6 SF on-site roles, 3 screened at score 3,
  all scored on company context only because the role bodies were never fetched

**Pack state as of 2026-08-09** — 22 packs on disk, all 22 rendering in the dashboard:

| Company | CV + letter | Dashboard |
|---|---|---|
| HumanLayer | yes — being regenerated off the retracted claim | row 417/467, `cv` attached |
| Nomadic AI | **none** — never tailored | 3 rows (360, 361, 467), score 3 / `maybe`, empty detail; `chief-of-staff` is on no shortlist at all |
| Lobby AI | none | **0 rows** — captured but not yet ingested or screened |

HumanLayer sitting at 417 and Nomadic ML dead last at 467 is precisely what items 5–6 fixed
(#384/#385) — pack state above is the 2026-08-09 snapshot that motivated the fix, not current.
