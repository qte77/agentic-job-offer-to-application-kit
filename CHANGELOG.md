# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Types of changes:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bugfixes.
- `Security` in case of vulnerabilities.

<!-- scriv-insert-here -->

## [0.3.0] - 2026-06-27

### Added

- README and quickstart now spell out how to install and start the kit — prerequisite (uv),
  `git clone` → `make install` → `make preview`, plus two concrete usage paths (the bundled
  `examples/alexis-doe/` example with no fetch, and running your own search).
- `make install-uv` to bootstrap the uv toolchain.

- Offline end-to-end smoke test (`tests/test_e2e_pipeline.py`) pinning the deterministic
  pipeline chain — `chunk` → `persist_scored` → `persist_offer` → `ats_check` — with canned
  synthetic Workflow outputs standing in for the non-deterministic LLM steps. Runs under
  `make check` (offline), guarding the cross-stage seams the per-module tests don't. (#165)

- Content-Security-Policy on the dashboard (#52, completes the UI-hardening set):
  `default-src 'self'; connect-src 'self' https://raw.githubusercontent.com; base-uri 'none';
  object-src 'none'` via a `<meta>` tag. Everything is already self-hosted (no CDN), and
  `connect-src` allows the runtime `data`-branch trends fetch. The inline anti-flash theme script
  moved to `ui/src/pre-theme.js` so no inline-script allowance is needed. Verified in headless
  chromium: no CSP violations, full render (shortlist, Chart.js, Inter fonts).

- `make ui-check` + `scripts/ui_check.py` (#172): a headless-browser smoke test for the dashboard.
  It serves `ui/` and loads it in headless Chromium — borrowed from the sibling `polyfetch-scrape`
  venv's patchright (no local browser install) — failing on any console error, page error, or render
  failure (empty shortlist / unsized charts / no fonts), and exercising `connect-src` via the
  cross-origin trends fetch. The local gate for `ui/` changes (CI has no browser).

- `ajoa_kit.corpus.merge_corpus()` (#164, foundation): a pure-stdlib four-state merge that folds a
  fresh ingest pull into a running corpus keyed by JD `id` — `new` / `changed` (content_hash of
  title+location+description differs) / `unchanged` (refresh `last_seen`) / `delisted` (kept with
  `last_seen` frozen). Stamps `first_seen`/`last_seen`/`content_hash`; `today` is injected for
  determinism. The basis for the upcoming `--merge` CLI flag and the daily scheduled ingest.

- `ajoa-kit ingest --merge` (#164): folds the fresh deduped pull into a running
  `results/corpus.json` via the four-state `merge_corpus` (new/changed/unchanged/delisted,
  stamping first_seen/last_seen/content_hash). `jobs-raw.json` is unchanged — it stays today's
  active pull for the relevance screen; the corpus is the growing history the trends snapshot and
  the daily cron read. Default `ingest` (no flag) behaves exactly as before.

- Daily incremental-ingest workflow (`.github/workflows/ingest-daily.yaml`, #164): a scheduled
  (06:00 UTC) + `workflow_dispatch` cron that checks out the public `polyfetch-scrape` fetch stack,
  restores the prior corpus artifact, runs `ajoa-kit ingest --merge` + `trend-snapshot`, pushes the
  aggregate keyword-only trends to the `data` branch, and re-uploads the corpus as a private
  cross-run artifact (no JD/PII content on any branch). Least-privilege permissions; all `uses:`
  SHA-pinned. Runs against the live network by design, so it is validated via `workflow_dispatch`,
  not PR CI.

- docs: ADR-0003 (data-contract enforcement) — maps the typed vs untyped data boundaries across the
  four layers and sets the direction: pydantic models on the Python boundaries (validated on read),
  inline JSON Schema for the sandboxed JS workflows, and JSON Schema as the cross-language contract
  for shared data (e.g. a single `config/lanes.json`); explicitly rejects a JS/TS validation library
  (can't run in the Workflow sandbox). Ships a prioritized backlog of boundaries to harden. Research
  only, no code (closes #158).

### Changed

- Makefile restructured: runs under the default POSIX `/bin/sh` (no `SHELL := bash`), grouped into
  `# MARK:` sections, with a single multi-line `.PHONY` declaration.

- Roadmap: record the offline e2e smoke test (#165) under Shipped, and add daily incremental
  ingest (#164) under Next with its resolved design decisions (artifact corpus store, `last_seen`
  tracking, bucket by `first_seen`, workflow-checkout + cache for polyfetch in CI).

- Dashboard UI hardening (#52, partial): outbound offer/role links now carry
  `rel="noopener noreferrer"` (don't leak the dashboard URL via `Referer`); the Copy button reads
  the raw tailor markdown from in-memory `tailorPacks` instead of inlining it in a `data-md`
  attribute (multi-KB packs no longer bloat the DOM); and the markdown sanitizer boundary is made
  explicit at the renderer. The optional Content-Security-Policy item is deferred — it needs an
  in-browser spike before shipping.

- `trend-snapshot` now prefers the #164 incremental `results/corpus.json` bucketed by each JD's
  `first_seen` (the field we control and always populate), falling back to `results/jobs-raw.json`
  bucketed by the less-reliable `posted_at` when no corpus exists yet. Re-pulled-but-old offers no
  longer inflate the current ISO week.

- Daily ingest workflow now restores the `data` branch's existing `trends.ndjson` before
  `trend-snapshot`, so the per-week upsert **accumulates** (keeps already-published weeks and
  adds/updates the corpus's `first_seen` weeks) instead of replacing the series — the live
  dashboard's trend history is no longer reset on the first scheduled run.

- Daily ingest workflow: bump `actions/upload-artifact` to v7.0.1 (Node 24) — silences the Node-20
  runner-deprecation warning surfaced by the first dispatch run.
- Roadmap: record #164 (daily incremental ingest) under Shipped and add the split-out daily offer
  summary (#175) under Next.

- `corpus.merge_corpus()` now returns records sorted by `id`, so `results/corpus.json` is
  deterministic across runs (stable cross-run diffs / reproducible artifact). "Delisted" is keyed on
  `last_seen`, not position, so nothing downstream depends on order.

- docs: sync the docs after the 0.2.0 work — add ADR-0003 to the README "Refs" ADR index and
  reference it from the architecture boundary-failure policy; refresh the roadmap (ADR-0003 #158, UI
  theming + Inter WOFF2 #112/#117, and the #54 governance safe-subset moved to Shipped; the
  data-contract typing backlog noted under "Later"; the bump → tag → publish release pipeline / v0.2.0
  recorded in the release-tooling line).

- ui: the Inter font is now served as WOFF2 (~64% smaller than the previous TTF — 68KB → 24KB per
  weight) with the TTF kept only as a legacy `@font-face` fallback. Generated from the vendored TTF
  via `fonttools`; still offline-first, no CDN. (#112)

### Fixed

- `ajoa-kit ingest --merge` (#164): the `--merge` flag was read by the dispatcher but never
  registered on the `ingest` subparser, so the CLI rejected it ("unrecognized arguments") and a
  plain `ingest` raised `AttributeError`. Registered the argument and added CLI-wiring regression
  tests (the unit tests had bypassed argparse).

## [0.2.0] - 2026-06-22

### Added

- ui: the dashboard header now shows **Repo** and **Issues** links (inline octicons, pill-styled to
  match the theme toggle) in a right-aligned cluster beside the brand — each opens the GitHub
  repository / issue tracker in a new tab (`rel="noopener"`). Vendored/inline SVG only, no CDN.

- tests: offline coverage for the ingest network helpers `get_json` / `get_bytes` (#53 follow-up) —
  non-200 responses raise `FetchError` (status + polyfetch backend in the message, so a junk error
  body never reaches `json.loads`), and 200 responses parse/return with the backend passed through;
  `get_json` sends an `Accept: application/json` header while `get_bytes` does not. Exercised via a
  fake `polyfetch_scrape` module, so they run under `pytest -m "not network"`.

- ci: AI issue-triage workflow — on newly **opened** issues, runs `qte77/gha-issue-triage`
  (SHA-pinned to v0.3.0) for duplicate detection, relevance/feasibility scoring, and auto-labeling.
  Backend defaults to **GitHub Models** (`openai/gpt-4.1`) via the built-in token (zero-secret),
  with least-privilege permissions (`contents: read`, `issues: write`, `models: read`).

- build: `make preview` now bundles the real `data`-branch trends into `ui/public/data/trends.ndjson`
  (same-origin, git-ignored) via a new `make trends-local` target, so the **local** dashboard shows
  real market data too — not just the live site. Offline-first: prefers a local `results/trends.ndjson`
  or an existing `data` / `origin/data` ref, and only `git fetch`es as a last resort.

- seed: +6 OK-tier AI/eng company boards in `config/default-seed.json` — **Zoox** (lever),
  **Cerebras** / **Perplexity** / **Runway** (ashby), **xAI** / **Scale AI** (greenhouse) —
  reachability-probed (HTTP 200) and ToS-tiered OK on 2026-06-22 (ADR-0002). They reuse the existing
  `greenhouse`/`ashby`/`lever` adapters (no new code) and add ~350–400 eng-relevant postings,
  densifying the keyword-trend signal.

- ui: shortlist rows are now expandable — click (or focus + Enter/Space) a row to reveal the
  tailored **CV** and **cover letter** for that offer in a detail panel. Demo uses synthetic
  `cv`/`cover_letter` strings (the canonical tailor-pack keys); real packs stay local
  (`results/offers/<slug>/`, gated on #52). Rendered as plain `<pre>` (esc'd, no new deps); a
  follow-up issue tracks an optional lightweight markdown renderer.

- ui: each expanded shortlist row's **Tailored CV** and **Cover letter** pane now has a **Copy**
  button (right-aligned next to the title) that copies the raw Markdown source to the clipboard,
  with brief "Copied" feedback. The raw `cv`/`cover_letter` is carried in an esc'd `data-md`
  attribute; the click never toggles the row.

- ui: a **time-frame picker** (All / 5y / 2y / 1y / 6mo / 3mo / 1mo / 2w / 1w) on the market-trends
  view, to the right of the heading. Selecting a range windows both charts to that trailing span
  (filtered by ISO-week *date*, so the sparse early weeks aren't miscounted). Vanilla `<select>`,
  no new dependencies.

### Changed

- docs: attribute the vendored `marked` (MIT) in `NOTICE` and the README License line (both
  previously credited only Chart.js), and reorder the README status badges to the qte77 canon
  (CodeQL · CodeFactor · CI · lint).

- docs: commands are now tracked once in a canonical CONTRIBUTING.md "Commands" section (the Makefile
  named as the source of truth) — covering the dev loop, the full pipeline, a CLI subcommand/flags
  table, and an environment-variable table (`AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` / `POLYFETCH_DIR` /
  `PORT`, previously undocumented). README and quickstart now reference it instead of repeating
  command spell-outs, and the workflow-script headers de-stale their prerequisite/persist steps
  (the old `python -m ajoa_kit.persist_scored` / `python -m ajoa_kit.chunk` forms) to point at the
  same reference. The relevance workflow's hardcoded lane keys now carry a comment noting the
  canonical lane definitions live in the evidence-library workflow.

- docs: synced the docs with this iteration's shipped features. Corrected the README's stale
  "trends fetched at runtime / never bundled into `ui/`" wording (now: bundled **same-origin** at
  deploy + the Pages deploy re-runs on `data`-branch pushes), and reflected the dashboard UX
  (expandable CV/cover-letter rows, market-trends time-frame picker, Repo/Issues header links,
  throwaway-copy `make preview`) and the issue-triage CI across `README.md`, `docs/architecture.md`,
  `docs/roadmap.md`, and `ui/README.md`; noted #54's attempted-then-reverted rulesets in the roadmap.

- Docs: documented the dashboard's runtime trends source switch — `?base=<raw-url>` takes a branch-
  bearing raw base (no separate `?branch=`; the branch lives in the `?base=` value) — and added the
  previously-undocumented CLI flags (`chunk --batch-size`, `persist-offer --slug`, `prefill-fields
  --ats/--slug/--job-id`) to the README; added `trend-snapshot` to the ADR-0001 subcommand list.

- ui: the header **Repo**/**Issues** links now match the agenthud dashboard — bordered chips on
  the surface tone (4px corners, border highlights on hover) with the GitHub octocat icon, and
  `rel="noopener noreferrer"`.

- build: `make preview` now serves real trends from a **throwaway assembled copy** of `ui/` (mirroring
  the gh-pages deploy) instead of writing them into the source tree — so the `ui/` code directory
  never holds data. Drops the `make trends-local` target and the `ui/public/data/trends.ndjson`
  gitignore entry; the `data` branch stays the single source of truth.

- docs: README now follows the qte77 doc-structure canon — **What → How → Why → Refs** order (was
  Why → What → How → Docs). The long How is trimmed to a minimal example that links to a new
  `docs/quickstart.md` (full ingest → tailor workflow + keyword-trends and writing-style options);
  build internals (the `LANES` array / evidence-library workflow) move out of What to
  `docs/architecture.md`; `## Docs` → `## Refs`; the live-demo link folds into How. Screenshots are
  self-hosted at `assets/images/` as two theme-aware `<details>` (shortlist with an expanded offer,
  market trends at the 3-month default). Closes #126.

- README: the dashboard's **market trends are now live** (real aggregate `{week,counts}` from the
  `data` branch), so dropped the "synthetic demo data" framing — moved the live-demo link into the
  **What** section and added a live-market-data screenshot pair (`docs/assets/dashboard-market-*.png`).

- README: completed the keyword-trends flow in "How" with the `make trends-data` publish step (push
  `results/trends.ndjson` to the `data` branch the live dashboard fetches at runtime), and dropped
  the `▶` glyph from the live-demo link.

- ci: the Pages deploy now also re-runs on **`data`-branch pushes** (matching `results/trends.ndjson`),
  so `make trends-data` automatically refreshes the live dashboard's trends — no manual redeploy. It
  always checks out the default branch's `ui/`, regardless of which branch triggered it.

- ui: the shortlist now behaves as an accordion — expanding an offer row collapses any other open
  row, so only one tailored CV / cover letter detail is shown at a time.

- ui: the tailored **CV** and **cover letter** in an expanded shortlist row now render as
  formatted Markdown (headings, bold, lists, paragraphs) instead of raw `<pre>` text, via a
  vendored, version-pinned [marked](https://github.com/markedjs/marked) ESM build (no CDN).
  marked does not sanitize, so its output passes through a tiny tag/attribute allowlist before
  hitting the DOM — keeping the renderer safe for the future #52-gated, model-generated packs.
  Falls back to the esc'd `<pre>` if the vendor import fails. Closes #138.

- ui: the header theme toggle (System/Auto) now matches the Repo/Issues chips — bordered on the
  surface tone, 4px corners, border-only hover — so the whole header action row is consistent. The
  shared chip visuals are now a single rule (`.header-link, .theme-toggle`).

- The live dashboard's real **market-trends** data now lives on a dedicated orphan **`data`** branch
  (never in `ui/` or `main`) and is fetched at **runtime** from `raw.githubusercontent.com` —
  mirroring `qte77/analyze-stock-kpi`. `ui/src/app.js` auto-derives the base from the GitHub Pages
  origin (`<owner>.github.io/<repo>` → that repo's `data` branch), so any fork self-hosts its own
  trends; `?base=` overrides for local, with the synthetic `demo.json` fallback on any miss. Replaces
  the `make trends-ui` copy-into-`ui/public/data/` flow with `make trends-data` (push to the `data`
  branch). (#128)

- ui: the market-trends time-frame picker now defaults to **3mo** (was "All"), so the charts
  open on the most recent quarter; other ranges (incl. All) remain one click away.

### Fixed

- ui: the GitHub octocat in the header **Repo**/**Issues** links is no longer tinted with the
  theme text color (`currentColor`) — GitHub's logo guidelines forbid recoloring its mark. It now
  renders in GitHub's permitted colors: **black on light themes, white on dark** (new `--gh-logo`
  token), so it stays theme-legible without being recolored to the palette.

- docs: the relevance workflow no longer hardcodes the lane count ("5 lanes" / "five target lanes")
  in its `meta.description`, header, and agent prompt — they now say "the target lanes" (the prompt
  still enumerates the actual lane keys), so the wording stays correct if the lane set changes.

- ui: the live dashboard now renders the **real** market trends reliably. It previously depended on
  a cross-origin runtime fetch to `raw.githubusercontent.com`, which some networks / browser
  extensions block (`CORS request did not succeed`) — silently dropping the charts to the synthetic
  fallback. `gh-pages.yaml` now bundles the PII-free aggregate trends (`{week,counts}`) from the
  `data` branch into the published site at deploy time, and `app.js` loads them **same-origin**
  first (the `data` branch / `?base=` remain fallbacks; synthetic is the last resort). The
  bundled copy is deploy-only — gitignored, never committed into `ui/`.

## [0.1.0] - 2026-06-21

### Added

- Per-adapter error/edge tests for the ingest adapters (#53): value-add offline cases for
  greenhouse / ashby / lever / recruitee / workable pinning each adapter's real normalization
  (multi-department joins, location/url fallbacks, `isRemote`/`workplaceType`/`telecommuting` →
  `remote` mapping, Lever's non-list-payload guard, shortcode-vs-id) plus missing/null-field
  tolerance, and a `collect()` warn-and-continue resilience case (one failing source is recorded
  and never aborts the run). The adapters were already tolerant, so no hardening was needed.

- ADR-0002 (`docs/decisions/0002-source-tos-tiers.md`): explicit OK/CAUTION/BLOCKED ToS/ToU tiers for
  ingest sources, the Feist/hiQ/Van Buren legal backbone, and the 2026-06-20 polyfetch-verified
  per-source findings (arbeitnow cleanest; jobicy/himalayas/remotive gated; RemoteOK/Google for Jobs
  blocked). Roadmap notes the aggregator broad lane (#94) and the slug-discovery / keyed-source
  (Jooble) outlook. (#95)

- `AppSettings` (pydantic-settings) runtime config and an `ajoa-kit` CLI — an `argparse`
  dispatcher with `ingest` / `chunk` / `persist` / `probe` subcommands. `config/` and
  `results/` are env-overridable via `AJOA_CONFIG_DIR` / `AJOA_RESULTS_DIR` and resolve from
  the working directory, so the package works as an installed wheel. Formalized in ADR-0001
  (backend / CLI / orchestration / UI four-layer separation with a one-way import rule).

- `ats-check` (#9): a deterministic résumé parse-safety pass — `src/ajoa_kit/ats_check.py` and the
  `ajoa-kit ats-check <cv.md>` subcommand flag ATS-hostile markdown (tables, raw HTML, images,
  hidden HTML comments, missing section headings) and exit non-zero when any is found. Run it over
  a tailored pack's `cv.md`. Parse-safety only; JD must-have *coverage* (semantic) stays with the
  tailor workflow.

- `docs/research.md`: a no-auth ATS feed/API endpoint table (Greenhouse, Ashby, Lever, Recruitee,
  Workable, Personio, RSS/Atom) documenting the sources `src/ajoa_kit/ingest.py` already pulls from
  — closing the last open task of #5 (the engine was built; the docs named no vendors).

- Structured, type-grouped job-sources catalog in `research.md §Market / boards` (general tech,
  startup, AI/ML, remote-first, research/RSE, executive/fractional, co-founder/VC, aggregators),
  region-agnostic, with a feed/API-first vs SPA/paste ingest note per type and cross-references to
  the §ATS endpoints and §Delivery boundary (#10).

- Pre-filter keywords are now runtime-configurable: `config/keywords.json`
  (`{"interest": [...], "title_roles": [...]}`) overrides the hardcoded defaults, so a caller or
  consumer can drive the ingest vocabulary per run without code changes. Absent the file, the existing
  defaults apply (#31).

- `CONTRIBUTING.md` — a human-contributor guide owning the dev loop, PR/branch workflow, and the
  scriv changelog process, and pointing to AGENTS.md / README.md for the rest. Linked from README
  and added to the `make docs-lint` link check (#35).

- Coverage gate in `make check` via `pytest-cov` (`--cov=ajoa_kit`), with
  `fail_under` set to the current floor (41%) in `[tool.coverage.report]`. This
  guards against coverage regression; it is not a target to chase with trivial
  tests (#33).

- `ui/`: two-tab dashboard (#11 PR-B) — **Shortlist** tab (synthetic offers) + **Market trends** tab
  rendering the real aggregate `{week, counts}` keyword timeline as a line chart (per-keyword over
  weeks) and a horizontal bar chart (top keywords, latest week). WAI-ARIA tabs (roving tabindex +
  arrow keys); charts rebuild on theme flip. Vendored Chart.js only — no CDN.
- `src/ajoa_kit/trend_snapshot.py`: `WeekCounts` pydantic model as the single typed contract for the
  publishable `{week, counts}` shape; `upsert_week` now writes through it.

- `config/default-seed.json`: added the WeWorkRemotely RSS feed to the shipped defaults (ToS: explicit
  aggregated-data clause + attribution; handled by the existing RSS adapter), and a test guarding that
  the shipped default parses and every entry has the required keys.

- `config/default-seed.json` — a tracked, ToS-vetted default source list (49 reachability-probed
  company boards across Greenhouse/Ashby/Lever/Personio + the swissdevjobs RSS feed) so `ajoa-kit
  ingest` works out of the box. `ingest.load_sources` now falls back to it when the git-ignored
  `config/seed.json` is absent; copy + trim the default into `config/seed.json` for your own runs.
  ToS/ToU-blocked platforms (Recruitee, Workable, LinkedIn) are recorded under `_blocked` and never
  loaded. Productizes the job-research `DEFAULT_SEED` model anticipated in ADR-0001 (#10).

- `docs/research.md` §Delivery: a cited "delivery safety" synthesis (#8) establishing the safe/unsafe
  boundary for reaching the employer — no-auth READ of public job-board APIs plus a human-submitted
  pre-fill pack is on the safe side of platform ToU and US CFAA (Van Buren, 2021); automated
  submission, CAPTCHA bypass, RPA, and autofill extensions are not. Per-platform submit-gating
  (Greenhouse/Ashby/Lever/Workable all require an employer key) is verified against primary API docs,
  with residual uncertainties (Personio/Recruitee, non-US computer-misuse law, GDPR specifics)
  flagged explicitly. Research synthesis, not legal advice.

- `src/ajoa_kit/ingest.py`: `from_arbeitnow` adapter + an `AGGREGATORS` dispatch dict for the broad
  no-auth arbeitnow job-board API (the recall lane alongside the curated per-company ATS sources).
  Job `tags` populate the `department` field so the existing word-boundary pre-filter applies with no
  change. Promoted arbeitnow from `_deferred` into a new loaded `aggregators` key in
  `config/default-seed.json`; the ToS §11 backlink is rendered in the dashboard footer (#94, ADR-0002).

- `src/ajoa_kit/` engine: feed/API-first job-description (JD) ingestion with no-auth
  adapters (Greenhouse, Ashby, Recruitee, Lever, Workable, Personio, RSS), a deterministic
  word-boundary pre-filter, batching, ATS slug discovery, and per-lane shortlist persistence.
- `docs/workflows/cc-workflow-relevance.js`: LLM lane-fit relevance screen over batched JDs;
  reads the evidence library and JD batches at run time.
- Config-driven sources: `config/seed.example.json`, `config/seed-candidates.example.json`
  (real config and all generated data are git-ignored to keep PII out of the repo).
- Baseline conformance: ruff config, a value-add `pytest` suite, CodeQL + Dependabot + CI
  workflows (SHA-pinned), and markdownlint.
- Governance: `LICENSE`, `AGENTS.md`, `CODEOWNERS`.
- A synthetic worked example under `examples/`.

- JD must-have coverage in the tailor pass (#55): the Stage-3 Match agent
  (`cc-workflow-tailor-offer.js`) now returns an optional structured `must_haves` array
  (`{requirement, covered, evidence}`), and `persist_offer` writes a `coverage-report.md`
  (a `Must-have | covered/gap | Evidence` table) into the offer pack when the pack carries it —
  outside the all-or-nothing artifact set, so existing packs are unaffected. New pure
  `ajoa_kit.coverage.coverage_summary` renders the table defensively (escapes pipes, collapses
  newlines, tolerates missing/`None` keys). Adds `hypothesis` (dev) for property-based tests.

- CI markdown + link linting (`.github/workflows/lint-md-links.yml`: markdownlint-cli2 + lychee),
  matching local `make docs-lint`. Markdownlint rule config split into `.markdownlint.jsonc`.

- `NOTICE` file (Apache-2.0 convention) reproducing the license of the one redistributed
  third-party component — the vendored Chart.js (MIT) in `ui/vendor/`. Declared Python
  dependencies are installed separately (not redistributed) and are not reproduced. Mirrors the
  `paperverse` NOTICE pattern.

- `ajoa-kit persist-offer` now auto-runs the ATS parse-safety check on the tailored CV (#75): when the
  CV trips a warning, `persist_offer` writes a non-blocking `cv-ats-check.md` into the offer pack for
  human review (a clean CV adds no file). Closes the gap where a parse-unsafe CV could ship silently;
  the deterministic check stays in L1 (`ats_check`), so the tailor workflow no longer needs a manual step.

- Stage-3 `prefill-pack` artifact (#50), completing the per-offer pack. The tailor workflow assembles a
  human-review prefill pack (field → grounded value, `[NEEDS HUMAN INPUT]` where it can't be evidenced)
  written to `results/offers/<slug>/prefill-pack.md`. `src/ajoa_kit/prefill.py` + `ajoa-kit
  prefill-fields` resolve the application-field schema — Greenhouse's public no-auth `?questions=true`
  (the one ATS that exposes it; see research.md §Delivery) or a generic fallback set. Read-only,
  human-submit only — no automated submission, ever.

- Property-based tests (`hypothesis`, added to dev deps in #55) pinning invariants across
  `safe_slug` (path confinement), `canonical_url` (idempotent, strips `utm_`, ingest/persist_scored
  copies stay in lockstep), `build_patterns`, `extract_counts`, `upsert_week`, `html_to_text`,
  `parse_safety_warnings` (monotone), `dedupe`, `render_fields`, and `style.directive`. (#98)

- Static-analysis gates: `pyright` (basic mode) and `complexipy` (cognitive complexity ≤ 10),
  wired into `make check` and exposed as `check_types` / `check_complexity` targets.

- README: a "▶ Live demo" link to the gh-pages dashboard, and a collapsible **Screenshots** section
  at the end of "What" — theme-aware `<picture>` (dark/light follows the GitHub theme) showing the
  tailored-shortlist and market-trends tabs (synthetic demo data, no PII).

- **Automated release flow** (modeled on `qte77/paperverse`): `bump-my-version.yaml` (a
  `workflow_dispatch` bump that opens a `chore(release)` PR — bumping `pyproject.toml` + the README
  badge + `src/ajoa_kit/__init__.py`, syncing `uv.lock`, and collecting `changelog.d/` fragments into
  `CHANGELOG.md`), `tag-release.yaml` (annotated-tags the merge commit on a version change), and
  `publish-release.yaml` (cuts a GitHub Release from the matching `CHANGELOG.md` block). Adds the
  `[tool.bumpversion]` config + the `bump-my-version` dev dep + `__version__` in the package, and a
  CONTRIBUTING.md "Releasing" section.

- `SECURITY.md` (private vulnerability-disclosure policy) and `.editorconfig`.

- `run-with-keywords` GitHub workflow (reusable `workflow_call` + `workflow_dispatch`) that runs the
  keyword-trend pipeline with a **consumer-supplied** keyword set and emits the keyword-only
  `trends.ndjson` as an artifact. The demo path uses the committed synthetic example corpus (no
  network); output is keyword-only by construction. Lets consumers (gh-pages demo; `ai-agents-research`
  triage) drive the vocabulary per run (#79).

- Changelog fragments via [scriv](https://github.com/nedbat/scriv): each PR adds one file
  under `changelog.d/` (`make changelog_new`); `make changelog_preview` shows the assembled
  entry and `make changelog_release VERSION=X.Y.Z` collects fragments into `CHANGELOG.md`.

- `config/default-seed.json`: +21 reachability-probed company ATS boards for geographic breadth
  (2026-06-20, each `_date_verified`) —
  **FR (9):** Qonto, Alan, Doctolib, Back Market, Contentsquare, Dataiku, Ledger, Aircall, Pigment ·
  **UK (7):** Monzo, GoCardless, Wayve, SumUp, Synthesia, Quantexa, Multiverse ·
  **IT (3):** Satispay, Docebo, Musixmatch · **US (2):** Figma, Plaid.
  Probed but **dropped** (resolve on no OK no-auth ATS — likely SmartRecruiters/Workable/Teamtailor):
  Spendesk, Wise, Revolut, Starling, Onfido, Bending Spoons, Scalapay, Translated, Soldo, Moneyfarm,
  Rippling, Retool.

- `src/ajoa_kit/ingest.py`: `from_themuse` adapter — The Muse public job-board API as a second
  broad-lane aggregator (robots-allowed, no-auth 200 with full JD + nested metadata; page-1 + an
  eng-relevant `category` filter). Wired into `AGGREGATORS` + the `aggregators` key in
  `config/default-seed.json`; value-add normalization test (nested `company`/`locations`/`refs`
  flattening + missing-field tolerance).

- `config/default-seed.json`: added 11 reachability-probed OK-tier company boards (2026-06-20) —
  Greenhouse: Arize AI, Isomorphic Labs, Recursion; Ashby: Aleph Alpha, Braintrust, Composio, Corti,
  Cursor, Langfuse, Chroma; Lever: Zilliz (#96). Each carries a `_date_verified` stamp.

- Writing style / tone for the Stage-3 tailor pass (#16): a git-ignored `config/style.json` lets the
  candidate set a `tone` and/or point to their own CV / cover-letter samples; per artifact a sample
  wins over the tone, which wins over a neutral default. `src/ajoa_kit/style.py` resolves it (with a
  sample-size cap and fail-loud on a missing referenced file), `ajoa-kit style [--json]` previews the
  directives, and `cc-workflow-tailor-offer.js` applies them via an optional `style` arg. The evidence
  library still supplies the facts — style shapes voice, not content.

- Stage-3 tailor pass (first vertical slice): `docs/workflows/cc-workflow-tailor-offer.js`
  turns one shortlisted offer into a per-offer application pack (match → tailored CV → cover
  letter → gap report), grounded in the evidence library. The companion `persist_offer` module
  (and `ajoa-kit persist-offer` subcommand) validates the returned pack and writes
  `results/offers/<slug>/{match,cv,cover-letter,gap-report}.md`, with the offer slug sanitized
  to a confined path segment. Pre-fill + human submit only — no auto-apply; the `ats-check`
  (#9) and `prefill-pack` (gated on the ToU/CFAA/GDPR verification, #8) artifacts are deferred.

- Dashboard theme toggle a11y: a polite `aria-live` region (`#theme-status`) now announces the selected
  mode to screen readers on change (the focused button's changed `aria-label` alone isn't re-read), and
  a `::before` width-sizer reserves the widest label so the pill no longer resizes as it cycles
  auto/light/dark. Additive only — the converged theme cycle, tokens, fonts, and favicon are unchanged.

- `ajoa-kit trend-snapshot` — derives an aggregate, **keyword-only** per-ISO-week frequency record
  from `results/jobs-raw.json` into `results/trends.ndjson` (document frequency over the
  config-driven keyword vocabulary; no JD text/company/title/url/per-posting rows). Keyword-only by
  construction, so it clears the ADR-0001 PII gate. Foundation for the trends dashboard (#11) and the
  run-with-keywords workflow (#79).

- Dashboard market-trends tab renders the **real** backfilled series from `ui/data/trends.ndjson`
  when present (sorted by ISO week), falling back to the synthetic `demo.json` trends; the
  shortlist stays synthetic. `make trends-ui` copies `results/trends.ndjson` into `ui/data/` for
  local preview (gitignored — live Pages publishing stays on the #11/#52 data-branch track).

- Static, no-build dashboard shell under `ui/` (vanilla HTML/CSS/JS + vendored Chart.js v4.5.1):
  a tailored-shortlist table with filter and a job-market keyword-trends chart, rendering synthetic
  demo data only (no PII). EyeRest brand tokens (zero-blue) with a three-state system/light/dark
  theme. The skeleton for the live trends dashboard (#11); live data-branch wiring stays gated on
  the PII helper (#52) per ADR-0001.
- `make preview` — serve the `ui/` dashboard locally (`PORT` defaults to 8000).
- GitHub Pages deploy workflow (`.github/workflows/gh-pages.yaml`) publishing `ui/` on changes to
  `main` (synthetic data only).

### Changed

- Coverage floor (`pyproject.toml` `fail_under`) raised 41 → 58 to lock in the gain from the new
  value-add tests (#33/#53).

- `config/default-seed.json`: block Google for Jobs, correct the RemoteOK `_reason` to match the
  2026-06-20 probe (API returns 200 + attribution notice; AI-crawlers blocked — not a blanket 403),
  point `_comment` at ADR-0002, add a `_date_verified` stamp to every `_blocked`/`_deferred` entry,
  and refresh the `_deferred` `_tos` notes to the verified findings. (#95)

- Dropped the hardcoded `ROOT = Path(__file__).resolve().parents[2]` from the pipeline
  modules; path resolution now flows through `AppSettings`. `scripts/ingest.sh` reduced to a
  thin env shim that anchors `AJOA_*_DIR` and delegates to `ajoa-kit ingest`; `Makefile`
  targets map to the CLI subcommands.

- `persist-offer` / `persist` now render each generated artifact's title as YAML **frontmatter**
  (`---` / `title:` / `---`) instead of a wrapping `# H1`, so each file keeps a single H1 from its
  own body — markdownlint strips frontmatter, so the packs no longer emit MD025 "multiple
  top-level headings".

- Skip the `CI` (ruff + pytest) and `CodeQL` workflows for docs-only changes
  (`docs/**`, `changelog.d/**`, `*.md`, `examples/**/*.md`, `lychee.toml`,
  `.markdownlint-cli2.jsonc`) via `paths-ignore`. The `Lint MD and Links`
  workflow still runs on those changes (#34).

- `ui/` Tab B: the weekly bar chart is **stacked** again (keywords piled per ISO week; each week is
  its own counts, no running total across weeks). The line chart stays as normal overlaid per-keyword
  lines.

- `ui/` Tab B: the weekly bar chart is now **grouped** (one bar per keyword, side by side) instead of
  stacked, and the **bubble chart was removed**. Tab B is now line (keyword frequency over weeks) +
  grouped weekly bars.

- `ui/data/demo.json`: `trends` reshaped from the pivoted `{weeks, series}` to an array of
  `{week, counts}` records (the WeekCounts shape); the JS derives the line/bar shapes at render time.

- `ui/`: Tab B now shows three weekly views of the `{week,counts}` log — line (keyword frequency over
  weeks) + **vertical stacked weekly bars** (volume + keyword composition per week) + **weekly
  bubbles** (keyword × week, radius ∝ √count). Replaces the previous "top keywords, latest week"
  horizontal bar.
- `ui/index.html`: simplified the footer — dropped the arbeitnow link and the demo-driven `Generated`
  span; the date is now the static site-creation date. Corrected the synthetic-data note to reflect
  that the live page publishes only aggregate `{week,counts}` facts (no pseudonymized per-posting
  data / no #52 gate).
- `config/default-seed.json` + `docs/decisions/0002-source-tos-tiers.md`: arbeitnow attribution is
  recorded in config/ADR for provenance — the published dashboard emits only non-copyrightable
  aggregate facts (Feist), not arbeitnow listings, so no on-page backlink is required.

- `config/default-seed.json`: recorded every ToS/ToU-vetted exclusion under `_blocked` (Recruitee,
  Workable, RemoteOK, LinkedIn, Indeed, StepStone, jobs.ch — no public API and/or automation barred) and
  added a `_deferred` registry for public JSON aggregators (arbeitnow, jobicy, himalayas, remotive) that
  need a JSON-feed adapter plus per-source attribution/permission. The loader still reads only `feeds` + `ats`.

- Deduplicate the shared invariants to single sources of truth: the git-ignored path list lives
  only in `docs/architecture.md §Data layout` (completed with `library/`/`input/`), the safe/unsafe
  submission boundary only in `docs/research.md §Delivery`, and the default lanes only in the
  `cc-workflow-evidence-library.js` `LANES` array. AGENTS.md, README.md, and SECURITY.md now state
  each rule once and link to its source instead of restating the detail (#57).

- Add scope cross-references: AGENTS.md now points to the four-layer model + one-way import rule
  (ADR-0001) and the orchestration mechanics (architecture.md §Three mechanics), so an agent can
  derive layer boundaries from its own rulebook; README's Docs section now links AGENTS.md and
  SECURITY.md (#57).

- Sync the docs with the shipped keyword-trend capability: README CLI list + a `config/keywords.json`
  / `trend-snapshot` note; architecture §Data layout (`keywords.json`, `trends.ndjson`) and Built lists;
  roadmap Shipped/Next/Later. The roadmap subcommand enumeration now points to `src/ajoa_kit/__main__.py`
  instead of re-listing (stops the per-subcommand drift) (#83).

- Pre-filter keyword lists (`INTEREST` / `TITLE_ROLES` in `ingest.py`) are now English-only —
  the German terms were dropped (their English equivalents already match the same roles).
  Locale-aware / i18n keyword support is tracked in #31.

- Greenhouse adapter dates JDs by their true publish date: `posted_at` = `first_published` (falling
  back to `updated_at`), and records now also carry `last_modified` (= `updated_at`).
  `trend_snapshot.bucket_by_week` gains a `date_of` selector (default `posted_at`) enabling
  activity-dating (`last_modified` ∨ `posted_at`).

- `ui/` dashboard footer: the "Generated" date is now stamped with the **real gh-pages deploy date**
  (`.github/workflows/gh-pages.yaml` seds it into the published copy at deploy time; the committed
  `#gen-date` value is just the local-preview default). Dropped the "EyeRest brand" and "no PII"
  labels (the synthetic-data note already covers the privacy framing).

- Hardened the GitHub Actions workflows (`ci.yaml`, `codeql.yaml`): deny-all top-level
  `permissions: {}` with least-privilege per job, `concurrency` cancellation, `timeout-minutes`,
  and `persist-credentials: false` on checkout.

- `ingest.load_sources` now returns `(feeds, ats, aggregators)` — a third source type per ADR-0001.

- Renamed the Stage-1 workflow to `docs/workflows/cc-workflow-evidence-library.js`
  (the `cc-workflow-*.js` naming convention for Workflow-tool scripts).

- Track the backlog solely in GitHub issues + `docs/roadmap.md` (Next/Later reconciled to the
  current open issues). The separate `docs/plans/backlog.md` execution doc was dropped to avoid
  duplicating issue content (it had already drifted from the open issues).

- Replace the inlined `lint-md-links` jobs with a call to the org reusable workflow
  `qte77/.github/.github/workflows/lint-md-links.yml` (SHA-pinned), matching `qte77/qte77` — a single
  source of truth instead of a hand-synced mirror. Also git-ignore the `.coverage` data file.

- Exclude the EU legal/regulatory citation URLs in `research.md` (eur-lex, EDPB) from the
  lychee link check — they return 403 to CI-runner IPs (bot protection) while resolving for
  humans, which was failing the `links` CI job.

- Consolidate markdownlint configuration into a single `.markdownlint-cli2.jsonc`
  (rules moved under its `config` key); remove the separate `.markdownlint.jsonc`.
  CI and `make docs-lint` behavior is unchanged (#45).

- Docs synced to shipped Stage-3: `roadmap.md` (tailoring moved to Shipped), `architecture.md`
  (pipeline + built-vs-designed), and `userstory.md` (US4/US5 no longer "next").

- Align the README badge row with the qte77 default set: License · Version · CodeFactor · CI ·
  CodeQL · Lint MD and Links (standard shields colors, matching polyfetch-scrape / analyze-stock-kpi).
  Drop the now-stale `*badge.svg` lychee exclusion — all three workflows are on `main`, so the badge
  SVGs are link-checked again (#22).

- README: reflect shipped Stage-3 (tailor → CV/cover-letter/gap-report, `ats-check`, style/tone) instead
  of "designed", and list the full `ajoa-kit` subcommand set (`persist-offer`, `ats-check`, `style`).

- Docs reconciled with the merged #55 (JD must-have coverage) and #95 (ADR-0002 source ToS tiers):
  `architecture.md` / `userstory.md` / `roadmap.md` / `research.md` now reflect the optional
  `coverage-report.md` artifact + the `must_haves` return; #55 moved to Shipped and ADR-0002 recorded;
  Google for Jobs flagged blocked; README / AGENTS / ADR-0001 now link ADR-0002. (#95, #55)

- Renamed `.github/workflows/pages.yaml` → `.github/workflows/gh-pages.yaml` (paperverse naming).

- Moved `CODEOWNERS` to `.github/CODEOWNERS`; renamed the Dependabot uv group `python` → `python-deps`.

- Market broad-lane ToS research (ADR-0002 + `docs/research.md` + roadmap): The Muse tiered **OK**
  (robots allows `/api/public`); keyed aggregators **Adzuna / Reed / Jooble** stay outside the
  no-auth/no-key model (#109 outlook), and SPA boards (Welcome to the Jungle) are paste-only. No
  clean generic market RSS feed surfaced this round (e.g. jobs.ac.uk `?format=rss` is not RSS).

- `config/default-seed.json`: recorded CrewAI + LatticeFlow under `_blocked` — both resolve only on
  Workable, which stays blocked per ADR-0002. sourcegraph / dagger / qdrant probed but resolved on no
  no-auth ATS endpoint, so they were dropped (not added).

- `ajoa-kit` CLI dispatch refactored to argparse `set_defaults(func=...)` handlers (flat complexity as
  subcommands grow); behavior unchanged.

- Move the operational writing-style configuration (`config/style.json` + `ajoa-kit style` usage)
  out of `research.md` into README §Run your own search, where users look for usage; `research.md`
  keeps a one-line rationale + pointer. Closes the last docs scope-separation item (#57).

- `ajoa-kit trend-snapshot` now buckets each JD by the ISO week of its `posted_at` (epoch
  seconds/milliseconds, ISO-8601, RFC-822) instead of stamping the run week — so a single scrape
  **backfills** a real multi-week `{week, counts}` timeline into `results/trends.ndjson` (JDs with
  no parseable date are skipped and counted). Output stays keyword-only (ADR-0001 PII gate).
  Backfill is survivorship-biased: live boards only expose currently-open postings, so older weeks
  thin out.

- `ui/`: converged theming onto the shared qte77 brand-kit naming (#112) — renamed CSS custom
  properties (`--panel`→`--surface`, `--muted`→`--text-muted`, `--accent`→`--primary`) across
  `style.css` + `app.js`, the theme storage key (`theme`→`qte77-theme`), and the auto mode label
  (`Auto`→`System`); added `clip-path: inset(50%)` to `.sr-only`. Zero behavior change (renames).
  JetBrains Mono (issue item 5) deferred — no mono consumer yet.

- `ui/`: reorganized into a `paperverse`-style folder layout (`src/`, `public/`, `tests/`) while
  staying **no-build** — `app.js`/`theme.js`/`style.css` moved to `src/`; `favicon.svg`, `data/`, and
  the vendored `vendor/` (Chart.js + Inter fonts) to `public/`; an empty `tests/` placeholder
  (`.gitkeep`) for parity (no JS test runner — Python modules are the tested surface). `index.html`
  stays at the served root and `gh-pages.yaml` (verbatim `cp -r ui/.`) / `make preview` are unchanged;
  asset paths in `index.html`/`src/*`, the `make trends-ui` target, `.gitignore`, and `NOTICE` were
  repointed accordingly.

- `ui/`: the header brand icon is now a neutral inline SVG — the canonical qte77 "q7_" mark in
  `currentColor` (zero-blue, theme-adaptive), replacing the blue-accent favicon image. This honors
  the EyeRest zero-blue rule (the brand's own mark SVGs still carry a legacy blue accent). The
  browser-tab favicon keeps the full brand mark.

- `ui/`: vendored the Inter font (Regular/Bold TTF, SIL OFL 1.1) under `ui/vendor/fonts/` with
  `@font-face` (offline, no CDN) and switched the body stack to `"Inter", system-ui, …` — the same
  fonts as the `paperverse` UI; replaced the favicon with the shared qte77 brand mark (from
  `paperverse`); and constrained the header and footer to the same `max-width` as the content column.
  `NOTICE` now reproduces the Inter OFL (also shipped at `ui/vendor/fonts/OFL.txt`).

- `ui/` theme toggle now mirrors the canonical `qte77.github.io` control: an `auto`/`light`/`dark`
  cycle button applied as `data-theme` on `<html>` (was a three-button segmented control on a `body`
  class), with an inline `<head>` anti-flash script and a `:focus-visible` ring. Theme logic moved to
  a self-contained `ui/theme.js`; the chart rebuilds on a `themechange` event. The `?theme=` URL param
  was dropped to match the canonical toggle. The button keeps a dynamic `aria-label` announcing state.

### Fixed

- `ats-check` no longer flags a bare `---` thematic break / Setext underline as a table — the
  table check now requires a pipe (a GFM delimiter row always has one). A clean single-column
  tailored CV with `---` section separators now passes the gate instead of failing with a spurious
  "table detected" warning.

- `docs/workflows/cc-workflow-*.js`: the Workflow tool delivers a script's `args` as a JSON
  **string**, so the documented `Workflow({ scriptPath, args: { … } })` invocation threw
  `args.<field> required`. The relevance / tailor-offer / evidence-library scripts now `JSON.parse`
  a string `args`, so the documented one-liner runs as written (no wrapper needed).
- `examples/alexis-doe/README.md`: refreshed the stale `python -m ajoa_kit.persist_scored` line to
  `ajoa-kit persist`, added a **Stage-3** walkthrough (tailor → `persist-offer` → `ats-check`), and
  documented persisting into the example workspace via `AJOA_RESULTS_DIR` (`persist` is not
  `rootDir`-aware). The two workflow-script header comments now cite `ajoa-kit persist` / `persist-offer`.

- Correct stale Stage-3 documentation that contradicted the shipped code: the prefill
  pack is documented as shipped (not "next"/"out of scope"); the persisted-artifact lists
  in the tailor workflow header and `persist_offer` docstring now include `prefill-pack.md`
  (5 files); the README CLI list includes `prefill-fields`; the ADR and roadmap reflect the
  full eight-subcommand set; the `persist_scored` prerequisite shows its required argument;
  the US3 path points to `examples/alexis-doe/`; the example layout lists `config/style.json`;
  and the AGENTS.md pydantic rule no longer reads as pending (#57).

- ats-check monotonicity property test now newline-joins its inputs — the table/HTML detectors are
  line-anchored (`^…$`), so bare concatenation could merge two lines and erase a match (flaky test).

- `ingest.html_to_text`: a `>` inside a quoted HTML attribute value no longer truncates the tag
  mid-match — the greedy `<[^>]+>` is now quote-aware. (#98)
- `trend_snapshot.upsert_week`: read the NDJSON log with `split("\n")` instead of `str.splitlines()`,
  which also split on Unicode line separators (NEL/LS/PS) that `json.dumps` leaves unescaped —
  corrupting a record when a week/keyword contained one. Surfaced by the new property test. (#98)

- Keyword pre-filter (`ingest.build_patterns`) now matches tech terms with punctuation as whole
  tokens — `c++`, `.net`, `node.js`, `ci-cd`, `c#` — and no longer leaks a short term into a larger
  token (`c` is not matched inside `c++`), while plain words still match before ordinary sentence
  punctuation. Pinned by a hypothesis property. (#97)
