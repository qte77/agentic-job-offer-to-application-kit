# Handoff 009 — renew the local job search, CV and letters

**State (2026-07-29): Phase A + B done, C+D pending.** Plan:
[docs/plans/009-renew-search-cv-letters.md](../plans/009-renew-search-cv-letters.md). Arc 008
(`render-pdf`) is closed and shipped — nothing migrated from it.

## What shipped

- [x] **Phase A hygiene.** `refresh` + `verify-sources` + `ingest --merge` + `chunk --new`.
      Corpus 7 563 → **7 997**; delta = **21 batches / 830 JDs**; sources **140/142** live.
- [x] **PR [#354](https://github.com/qte77/agentic-job-offer-to-application-kit/pull/354)** —
      `fix(refresh): only 404/410 expire a shortlist entry`. CI green, **NOT MERGED** (see Blocked).
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

## Blocked — needs the owner

1. **Merge PR #354** — `gh pr merge 354 --squash --admin --delete-branch` was denied by the
   permission classifier. Branch `fix/refresh-probe-3xx-false-stale`, CI green.
2. **Re-run the sweep** — the venv-borrow `refresh` was denied by the classifier on its third
   invocation (it succeeded twice earlier in the same session). Until it runs, shortlist `stale`
   flags come from the buggy rule.

Both are permission grants, not work. Everything else proceeded around them.

## Resume here, in order

1. Merge #354, then re-run `refresh` via the
   [venv-borrow](../../CONTRIBUTING.md#polyfetch-venv-borrow) — expect the stale count to drop
   well below 147 as the 56 false positives return.
2. Settle the `maxProjects` cap (plan → Phase B table): re-resume `wf_bc321d71-472` at ~34 to pull
   in `agentic-cax-gauge`, `__SABI`, `protocols` and the dropped `gha-*` family, or accept 24 and
   record that. Cached miners replay free — only new repos plus a fresh assemble cost tokens.
3. Phase C — relevance over `batchCount: 21`, then `make persist FILE=<out> --merge`.
4. Phase D — top **12** by fit across surviving packs + fresh keepers; `persist-offer` →
   `ats-check` → optional `render-pdf`. Archive non-survivors to `results/offers-archive/<slug>/`
   by **moving**, never deleting.
5. Drop `greenhouse/dbtlabsinc` from `config/default-seed.json` (hard 404 in today's ingest).

## Watch-outs

- **Never resolve liveness by following redirects** — Greenhouse's job-removed page is HTTP 200.
- **Never archive on the corpus-id join** — it reports all 29 packs "absent" while the shortlist
  join matches 29/29. Use the sweep's `stale` flag.
- **The new library is not a superset of the old one.** `maxProjects: 24` over 84 repos dropped ~10
  projects the 06-29 library had, incl. six `gha-*` Actions repos — the cloud/DevOps lane keeps only
  `gha-sec-feed` from that family. Tailoring reads the new library only, so lane evidence thins
  until the cap decision is settled.
- `persist` without `--merge` overwrites the accrued shortlists.
- Phase D at 12 packs ≈ 4–7M tokens; Phase C ≈ 2.1M.
- `env -u GH_TOKEN -u GITHUB_TOKEN` on every `gh` / `git push`; commit with `--no-gpg-sign`.
