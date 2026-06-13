# Synthetic worked example — "Alexis Doe"

A fictional persona demonstrating the **ingest → relevance** happy path end-to-end.
**Generalized from a real run and de-identified** — not a real person, no real scraped job
data, no personally identifiable information (PII).

## Files

- `evidence-library.json` — the Stage-1 output; the candidate brief the relevance screen reads.
- `jobs-raw.json` — a few job descriptions (JDs) generalized from real postings (fictional
  companies), in the shape `ajoa_kit.ingest` emits (post pre-filter).
- `shortlist.sample.md` — an illustrative relevance result (the LLM step is non-deterministic).

## Run it

The pipeline reads `results/` under `rootDir`, so copy this example's inputs into `results/`,
batch them, then run the relevance workflow:

```bash
mkdir -p results
cp examples/alexis-doe/evidence-library.json results/evidence-library.json
cp examples/alexis-doe/jobs-raw.json results/jobs-raw.json
uv run python -m ajoa_kit.chunk                     # -> results/batches/ + manifest.json

# Claude Code Workflow tool (batchCount = results/batches/manifest.json .batch_count):
#   Workflow({ scriptPath: "docs/workflows/cc-workflow-relevance.js",
#              args: { rootDir: ".", batchCount: 1 } })

uv run python -m ajoa_kit.persist_scored <output.json>   # -> results/<lane>/shortlist.*
```

`results/` is git-ignored, so this leaves the repo clean.
