# Quickstart

The full run workflow and optional features. For the one-line overview see the
[README](../README.md#how); for the pipeline internals see [architecture.md](architecture.md); for
the exact commands (dev, run, and release) see [CONTRIBUTING.md §Commands](../CONTRIBUTING.md#commands).

## Install

Prerequisite: [uv](https://docs.astral.sh/uv/) (it provisions Python ≥ 3.11). Then:

```bash
git clone https://github.com/qte77/agentic-job-offer-to-application-kit
cd agentic-job-offer-to-application-kit
make install_uv   # install uv (skip if already installed)
make install      # sync the dev environment (uv)
make preview      # serve the dashboard at http://localhost:8000 (override: PORT=9000 make preview)
```

`make help` lists every target; [CONTRIBUTING.md §Commands](../CONTRIBUTING.md#commands) documents
them in full.

## Run your own search

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (provisions Python ≥ 3.11), **Claude Code** (its
Workflow tool runs the relevance/tailor phases), and a
[`polyfetch-scrape`](https://github.com/qte77/polyfetch-scrape) checkout beside this repo —
`git clone https://github.com/qte77/polyfetch-scrape ../polyfetch-scrape && (cd ../polyfetch-scrape && uv sync)`
— the network-fetch layer every network-touching subcommand borrows (`ingest`, `probe`,
`refresh`, `verify-sources`, `discover`); see
[CONTRIBUTING §Polyfetch venv-borrow](../CONTRIBUTING.md#polyfetch-venv-borrow). The Makefile is the
command source of truth (`make help`); the CLI flags and the `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` /
`POLYFETCH_DIR` overrides are tabulated in [CONTRIBUTING.md](../CONTRIBUTING.md#commands) for
contributors. What you author first is the **source list**:

The kit ships a tracked default (`config/default-seed.json`) and runs out of the box. To use your
own, create `config/seed.json` (git-ignored); it overrides the default, e.g.:

```json
{"feeds": [], "ats": [{"ats": "greenhouse", "slug": "acme", "company": "Acme", "lane": "engineering"}],
 "aggregators": [{"name": "arbeitnow"}, {"name": "themuse"}]}
```

Broad no-auth aggregators are ToS-tiered in [ADR-0002](decisions/0002-source-tos-tiers.md).

Then run the pipeline — Stage 1 builds your evidence library **once**; Stages 2–3 run per search. The
`Workflow({…})` blocks run inside a Claude Code session, and **you save each Workflow's returned JSON
to the file the next `make` / `ajoa-kit` step reads** (that hand-off is manual):

```text
# Stage 1 (once) — save the returned object to results/evidence-library.json:
Workflow({ scriptPath: ".claude/workflows/cc-workflow-evidence-library.js",
           args: { workspaceRoot: "/path/to/portfolio", account: "you" } })

# Stage 2 (per search) — ingest -> chunk -> relevance -> persist:
POLYFETCH_DIR=../polyfetch-scrape make ingest        # -> results/jobs-raw.json
make chunk                                           # -> results/batches/ (+ manifest.json)
# relevance: batchCount = results/batches/manifest.json .batch_count; save the result, then persist:
Workflow({ scriptPath: ".claude/workflows/cc-workflow-relevance.js",
           args: { rootDir: ".", batchCount: <N> } })
make persist FILE=<relevance-output.json>            # -> results/<lane>/shortlist.*
uv run ajoa-kit pack-plan --min-score 5 --json       # -> results/pack-plan.json (which offer ids still need a pack)

# Stage 3 (per offer) — pick an offer id from a shortlist, then tailor -> persist-offer -> ats-check:
Workflow({ scriptPath: ".claude/workflows/cc-workflow-tailor-offer.js",
           args: { rootDir: ".", lane: "engineering", offerId: "<id>" } })
uv run ajoa-kit persist-offer <tailor-output.json>   # -> results/offers/<slug>/*.md
uv run ajoa-kit ats-check results/offers/<slug>/cv.md
```

## Incremental / daily ingest (optional)

`ajoa-kit ingest --merge` additionally folds each pull into a running `results/corpus.json` — a
4-state dedup-merge (new / changed / unchanged / delisted) that stamps `first_seen` / `last_seen` per
JD, so the keyword trends bucket by when a role *first appeared* rather than the run date. The
scheduled `.github/workflows/ingest-daily.yaml` (06:00 UTC + manual `workflow_dispatch`) runs this
daily, keeping the corpus as a private cross-run artifact (no PII on any branch) and pushing only the
aggregate keyword trends to the `data` branch. `--merge` leaves `results/jobs-raw.json` unchanged.

## Keep a shortlist current (optional)

Two halves keep a standing shortlist fresh after a re-ingest: **screen the newly-seen offers** into
it, then **reconcile the stale ones** out.

Screen only the offers first seen in the latest pull (cheap — skips everything already scored) and
union them into the existing shortlists without clobbering:

```bash
POLYFETCH_DIR=../polyfetch-scrape scripts/ingest.sh --merge       # updates results/corpus.json
uv run ajoa-kit chunk --new                                       # batch only the corpus.json delta
# relevance (Workflow tool) over the delta batches; save the result, then:
uv run ajoa-kit persist --merge <relevance-output.json>           # union by id into shortlists
```

Then reconcile — offers get filled or closed, so a shortlist goes stale:

```bash
# refresh re-probes offer URLs, so it runs via the polyfetch venv-borrow
# (see CONTRIBUTING §Polyfetch venv-borrow):
AJOA_CONFIG_DIR="$PWD/config" AJOA_RESULTS_DIR="$PWD/results" PYTHONPATH="$PWD/src" \
  uv run --directory ../polyfetch-scrape --with pydantic --with pydantic-settings --with defusedxml \
  python -m ajoa_kit refresh --lane engineering --dry-run   # report what would be flagged
# same invocation without --dry-run flags dead offers `stale` (default);
# `refresh --delete` removes them from every lane instead
```

Each `results/<lane>/shortlist.json` entry is re-checked against the corpus `delisted` state **and** a
read-only URL re-probe (so an offer whose source you stopped tracking is still caught). Dead entries
are flagged `stale` (kept as an audit trail; `make preview` hides them) or removed with `--delete`; an
inconclusive probe (network error / timeout) never flags a live entry. Omit `--lane` to sweep every
bucket.

## Try the example (no fetch)

The synthetic [`examples/alexis-doe/`](../examples/alexis-doe/) workspace ships a pre-built evidence
library + batches, so run the relevance screen straight against it — no `make ingest`/`make chunk`:

```text
Workflow({ scriptPath: ".claude/workflows/cc-workflow-relevance.js",
           args: { rootDir: "examples/alexis-doe", batchCount: 1 } })
```

## Keyword trends (optional)

The tracked `config/keywords.json` (`{"interest": [...], "title_roles": [...]}`) is the canonical
pre-filter vocabulary (#249) — edit it to change what's tracked, but **keep it non-identifying**:
its terms become the published trend keys on the live dashboard. For a personal/private vocabulary,
point `AJOA_CONFIG_DIR` at your own config dir instead. `trend-snapshot` then writes an aggregate, keyword-only per-ISO-week record to
`public-data/trends.ndjson` (no JD/PII), and pushing it to the `data` branch re-triggers the Pages deploy
to bundle it **same-origin** into the published site (so the live charts load reliably — no
cross-origin runtime fetch) — commands in
[CONTRIBUTING.md §Trends data branch](../CONTRIBUTING.md#trends-data-branch). Local dev and forks
fall back to fetching the `data` branch directly, overridable with `?base=<raw-url>`; the real trends
are never committed to the source `ui/` (see [ui/README.md](../ui/README.md)).

## Postings no adapter can reach (optional)

Some roles are published only behind a JS accordion, a login, or a page with no feed at all. Capture
the JD by hand and add it to a git-ignored `config/manual-jds.json` — a list of
`{id, title, company, companySlug, location, url, description, laneHint, postedAt, remote}` entries,
of which only `id` (conventionally `manual:<company>:<role>`) and `title` are required.

`ingest` injects every entry into each pull, so the record survives the wholesale rewrite of
`results/jobs-raw.json` and is never delisted from the corpus. That durability cuts both ways:
`refresh` can only ever expire a manual entry through its `url`, so **prefer the posting's own URL
over a careers page** — a careers page answers 200 long after the role is filled, and the entry then
has no automatic way to go stale. Manual entries skip the keyword
pre-filter — you already decided the posting is worth keeping. Removing an entry is how you retire
one, and if a board later publishes the same `id` the **pulled** record wins. A malformed entry
fails the run rather than being skipped silently. See
[examples/alexis-doe](../examples/alexis-doe/README.md#adding-a-posting-no-adapter-can-reach) for a
worked entry.

## Location + work-authorization advisory (optional)

Drop a git-ignored `config/location.json` and the screen will flag postings whose stated location or
work-authorization requirement you do not meet:

```json
{"basedIn": "Zurich, Switzerland", "authorizedIn": ["Switzerland", "EU"],
 "remoteOk": true, "relocateTo": [], "notes": ""}
```

Emit it with `ajoa-kit location --json` and pass the payload as the relevance workflow's
`args.location` (same hand-off as `style`). `ajoa-kit location` without `--json` reports whether a
policy is active.

**`authorizedIn` is the on-switch** — without it the policy is inert and the screen ignores location
entirely, because there is no ground truth to test a posting against and it will not guess from
`basedIn`. It is **advisory, never a filter**: a flagged posting keeps its score and stays on the
shortlist, with the constraint quoted in its `deal_breaker`; sponsorship, remote exceptions and
relocation are negotiable in ways a screen cannot judge. A posting that states no requirement is
never flagged from the company's headquarters alone.

Add it *before* a relevance run — applying it later means re-screening.

## Writing style (optional)

Drop a git-ignored `config/style.json` with a `tone` string and/or paths to your own CV /
cover-letter samples; `ajoa-kit style --json` emits the resolved directives to pass as the tailor
workflow's `style` arg (a sample wins over the tone, which wins over a neutral default). Style shapes
voice, not content — the evidence library still supplies the facts.
