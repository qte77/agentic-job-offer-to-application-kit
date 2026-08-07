# Handoff 009 — renew the local job search, CV and letters

> **CLOSED 2026-08-07.** Arc complete. Two items migrated to
> [handoff 010](010-screen-quality-shortlist-usability.md) / [plan 010](../plans/010-screen-quality-shortlist-usability.md):
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
[docs/plans/009-renew-search-cv-letters.md](../plans/009-renew-search-cv-letters.md). Arc 008
(`render-pdf`) is closed and shipped — nothing migrated from it.

## What shipped

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

## The defect, because it changes how you read old sweeps

`refresh.classify` treated any non-2xx probe as proof of death. Board URLs 301 to the canonical
posting (Stripe/Databricks `gh_jid` links) and WeWorkRemotely answers an unattended probe with 403 —
so the 2026-07-28 sweep buried **56 live offers**. Verified: `direct=301 follow=200 ->
stripe.com/jobs/listing/staff-engineer-agentic-commerce/8047789`.

Fix narrows the kill rule to `GONE_STATUSES = {404, 410}`. **Any `stale` flag written before this
fix is suspect** — the shortlists currently on disk were flagged by the old rule and must be
re-swept before Phase D picks packs.

## Blocked / resume order — RESOLVED, kept for history

Both blockers cleared on 2026-08-07: #354 merged (along with #355/#358/#359/#360), and the
owner-gated `refresh` re-sweep was superseded rather than run — pack liveness is judged on the
corpus join, which needs no network. The resume order that lived here is finished except for
Phase C and the second tailor round, both now
[plan 010](../plans/010-screen-quality-shortlist-usability.md) items 3 and 10.

## Watch-outs

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
