# Synthetic worked example — "Alexis Doe"

A fictional persona demonstrating the **ingest → relevance → tailor** happy path, laid out as a
self-contained mini-workspace that **mirrors the real `config/` + `results/` structure**.
**Generalized from a real run and de-identified** — not a real person, no real scraped job data,
no personally identifiable information (PII).

## Layout

```text
examples/alexis-doe/
├── config/
│   ├── seed.json                  # example sources (copy to the repo-root config/seed.json to start)
│   ├── seed-candidates.json       # example slugs for ajoa_kit.slug_probe
│   └── style.json                 # writing-style config for the tailor pass (see ajoa-kit style)
└── results/
    ├── evidence-library.json      # Stage-1 output — the candidate brief the relevance screen reads
    ├── jobs-raw.json              # ingested corpus (post pre-filter), as ajoa_kit.ingest emits
    ├── batches/                   # pre-generated, so the relevance step runs without chunk
    │   ├── manifest.json
    │   └── batch-000.json
    ├── engineering/shortlist.sample.md
    └── cloud/shortlist.sample.md  # illustrative output (the LLM step is non-deterministic)
```

## Stage 2 — relevance screen against this workspace

The relevance workflow is `rootDir`-aware and the batches are pre-generated, so point it straight
at this folder — no `ingest`/`chunk` needed:

```text
Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
           args: { rootDir: "examples/alexis-doe", batchCount: 1 } })
```

The `results/<lane>/shortlist.sample.md` files show the shape of the output (the LLM step is
non-deterministic, so your run may shortlist a different offer).

## Stage 3 — persist, tailor, finalize one offer

`persist` / `persist-offer` are **not** `rootDir`-aware — they honor `AJOA_RESULTS_DIR`, not the
workflow `rootDir`. To keep the whole chain inside this example workspace, point `AJOA_RESULTS_DIR`
at it so the tailor step can resolve `results/<lane>/shortlist.json`:

```bash
# 1. persist the relevance result INTO this workspace (-> results/<lane>/shortlist.{json,md})
AJOA_RESULTS_DIR="$PWD/examples/alexis-doe/results" uv run ajoa-kit persist <relevance-output.json>

# 2. tailor one shortlisted offer — lane + offerId come from the shortlist you just wrote:
#    Workflow({ scriptPath: "docs/workflows/cc-workflow-tailor-offer.js",
#               args: { rootDir: "examples/alexis-doe", lane: "engineering", offerId: "<id>" } })

# 3. persist the pack, then run the ATS parse-safety gate on the tailored CV
uv run ajoa-kit persist-offer <tailor-output.json>   # -> results/offers/<slug>/*.md
uv run ajoa-kit ats-check results/offers/<slug>/cv.md
```

For a real run you persist without `AJOA_RESULTS_DIR` (writes to the **repo-root** `results/`); then
the tailor workflow's `rootDir` is just `.`. Either way, the persisted shortlist and the tailor
`rootDir` must point at the same `results/` tree.

## Start your own search

```bash
cp examples/alexis-doe/config/seed.json config/seed.json   # then edit
```
