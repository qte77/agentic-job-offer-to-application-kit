# Synthetic worked example — "Alexis Doe"

A fictional persona demonstrating the **ingest → relevance** happy path, laid out as a
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

## Run the relevance step against this workspace

The relevance workflow is `rootDir`-aware and the batches are pre-generated, so point it straight
at this folder — no ingest/chunk needed:

```text
Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
           args: { rootDir: "examples/alexis-doe", batchCount: 1 } })
```

The `results/<lane>/shortlist.sample.md` files show the shape of the output. Persisting it
(`uv run python -m ajoa_kit.persist_scored <output.json>`) writes real shortlists to the
**repo-root** `results/` — `chunk`/`persist_scored` are not `rootDir`-aware yet (tracked follow-up).

## Start your own search

```bash
cp examples/alexis-doe/config/seed.json config/seed.json   # then edit
```
