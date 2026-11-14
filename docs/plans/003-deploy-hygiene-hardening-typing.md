# Plan 003 — deploy hygiene (#251) · hardening batch (#256) · StyleBrief typing (#257)

> **Closed plan, kept as a record.** Commands in it are one machine's history, not procedure; for current steps see the repo's CONTRIBUTING and the newest plan.

Three small PRs, each closing one issue filed 2026-07-05, each grounded in evidence gathered that
session (the #251/#252 deploy incidents and the verified security-teardown triage). Approved in-session
2026-07-05; handoff: [§Handoff](#handoff).

**Status: SHIPPED (confirmed 2026-09-01).** All 3 tracked issues closed: #251, #256, #257.
Retroactively confirmed — predates the SHIPPED-stamp convention plans 004+ use.

## Context

- **#251 (bug)** — `data`-branch pushes never re-trigger the Pages deploy: `make trends-data`
  force-pushes a **parentless** commit (`git commit-tree`, no `-p`), so GitHub's `paths:` filter has
  nothing to diff and never matches. The same-origin trends bundle staled silently for weeks. A second
  reliability wart (stuck Pages deployment masking as `building`, recovery recipe) is documented in
  the issue comments.
- **#256 (hardening)** — three verified items: `GITHUB_TOKEN` interpolated into `git push` argv
  (visible in `/proc/<pid>/cmdline`; LOW–MEDIUM on ephemeral runners), no `http(s)` scheme guard on
  the two fetch helpers (a hostile config URL like `file:///…` reaches `polyfetch.fetch`), and zero
  direct test coverage on the `safe_slug` traversal sanitizer.
- **#257 (typing)** — `style.StyleBrief` is the repo's last `@dataclass` (AGENTS.md rule: pydantic
  only); all other models were consolidated into `models.py` by the #249 epic.

**Decisions (settled with the owner):** drop the gh-pages `paths:` filter entirely (deploy on every
`main`/`data` push — ~20 s, idempotent, also covers *local* `make trends-data` pushes) · **no**
cache-busting (Pages `max-age=600` self-heals) · **no** `#gen-sha` footer stamp (YAGNI after the
trigger fix) · `safe_slug` pin ships examples **plus** a small Hypothesis property · three separate
PRs, executed 1 → 2 → 3.

## Conventions

- Topic branch off fresh `main` per PR → commit by topic (`--no-gpg-sign`, plain push) → squash-merge
  only on fully green CI → prune remote + local branches.
- **Strict TDD on module logic only**: scheme guard red→green; the `safe_slug` and `--json` pins ARE
  the deliverable tests. PR 1 is pure glue — zero tests. No trivial tests.
- **Gate runs LAST** before every push (mutators — `ruff --fix`, formatters — first; any post-gate
  edit re-runs the full gate): `make check`; `markdownlint-cli2 --no-globs <files>` on doc-touching
  PRs; security read per diff (PR 2's token fix additionally proven by a real dispatched deploy).

---

## PR 1 — `fix/deploy-hygiene` (closes #251) — glue only, no tests

1. `.github/workflows/gh-pages.yaml` — **trigger only**: delete the `paths:` block (keep
   `branches: [main, data]` + `workflow_dispatch`); update the header comment (deploys on every
   push; the parentless data-branch force-push is why no path filter can work).
2. Doc truthfulness corrections:
   - `CONTRIBUTING.md` §Trends data branch **and** `ui/README.md`: both claim *"the live dashboard
     picks it up on the next page load — no redeploy"* — now false; a `data` push auto-redeploys
     the same-origin bundle.
   - `CONTRIBUTING.md` env table: add the missing **`TRENDS_FORCE`** row (shrink-guard escape,
     shipped in PR #253 but documented only in a Makefile comment).
   - `docs/architecture.md`: align the "Pages re-deploys on `data`-branch pushes" claim (now true,
     unconditional).
   - `docs/roadmap.md`: add the missed **#249 epic Shipped bullet** (models consolidation ·
     defaults/config-SSOT `keywords.json` · ingest split into `sources`/`normalize` · trends shrink
     guard · UI module split) + a deploy-reliability line (#251/#252).
   - `docs/userstory.md`: **no change** — verified against its own conventions (ops/data-layer
     deltas route to roadmap; #234 vs #145 commit history is the evidence).
3. Scriv fragment: one-line `Fixed` (user-visible site-freshness bug; not changelog-exempt).

**Verify:** the merge push itself must trigger a deploy (`gh run list --workflow=gh-pages.yaml`) —
that IS the test; tonight's cron `data` push must also deploy (check next day, or force via a manual
`make trends-data`).

## PR 2 — `harden/batch` (closes #256) — the TDD PR

1. **Scheme guard, red→green** — `src/ajoa_kit/sources.py`:
   - Tests first (in `tests/test_fetch.py`, reusing its fake-`polyfetch_scrape`-via-`sys.modules`
     pattern): `get_json("file:///etc/passwd")` and `get_bytes("javascript:alert(1)")` **raise
     `ValueError`** without touching the fake fetch; `https://` still fetches. Red.
   - Implement: module-local `_is_http(url)` predicate + raise at the top of both helpers.
     **Contract note:** fetchers fail loud; `slug_probe.fetch_status` keeps its `None`-on-non-http
     contract and is NOT touched (contracts differ — only a 1-line predicate would be shared, so no
     cross-module extraction).
2. **`safe_slug` pin (test IS the deliverable)** — new `tests/test_persist_offer.py`: examples
   (`safe_slug("../../etc/passwd") == "etc-passwd"`; empty-after-sanitize raises `ValueError`)
   plus a small Hypothesis property over arbitrary text: when it doesn't raise, the output contains
   no `/` and no `..` (mirror `tests/test_canonical_url.py`'s invariant style). No production change.
3. **Token out of argv** — `gh-pages.yaml` publish step: replace the URL-embedded token with a lazy
   credential helper (token expanded at helper **runtime** by `sh`, never in argv or resolved
   config):

   ```bash
   git remote add origin "https://github.com/${GITHUB_REPOSITORY}.git"
   git config credential.helper '!f() { echo "username=x-access-token"; echo "password=${GH_TOKEN}"; }; f'
   git push -f origin gh-pages
   ```

   (single-quoted config value; `GH_TOKEN` is already step-level `env`.)
4. Scriv fragment (`Security`).

**Verify:** `make check` green (new tests offline); after merge **dispatch `gh-pages.yaml`** — the
credential-helper swap is only proven by a real push; then polyfetch-fetch any `src/*.js` on the
live site to confirm fresh content.

## PR 3 — `refactor/style-brief` (closes #257)

1. **Pin first (green→green)** — add to `tests/test_style.py`: call `style.main(config_dir,
   as_json=True)` with a tmp `style.json` + sample file, capture stdout (`capsys`), assert the
   exact `{"cv": …, "coverLetter": …}` JSON byte-for-byte (`indent=2`, no sort_keys). This is the
   missing contract test for the JS seam (`cc-workflow-tailor-offer.js` consumes this output).
2. **Convert**: `StyleBrief` → pydantic `BaseModel` in `src/ajoa_kit/models.py` (same 3 str fields,
   `""` defaults; kwarg construction unchanged). `style.py` gains
   `from ajoa_kit.models import StyleBrief` (so `style.StyleBrief` still resolves — zero test
   churn), drops the `dataclasses` import. `models.py` docstring adds StyleBrief.
3. Docs: `docs/architecture.md` contracts-table row (`style.StyleBrief` `@dataclass` →
   `models.StyleBrief` pydantic); scriv fragment (`Changed`).

**Verify:** pin green before AND after; full `make check`; diff `uv run ajoa-kit style --json`
output against `main`'s (byte-identical).

---

## Source map (verified 2026-07-05 — symbol anchors, no line numbers; re-verify before editing)

### `.github/workflows/gh-pages.yaml` (PR 1 + PR 2)

- `on.push`: `branches: [main, data]` + a `paths:` list of three entries (`ui/**`, the workflow
  itself, `public-data/trends.ndjson`) → **delete the whole `paths:` block** (PR 1).
- Job `deploy`: `permissions: contents: write`; checkout pins
  `actions/checkout@9c091bb…  # v7.0.0` with `ref: ${{ github.event.repository.default_branch }}`,
  `persist-credentials: false`.
- Publish step (`env: GH_TOKEN`, `TRENDS_FILE: public-data/trends.ndjson`): mktemp site copy →
  same-origin bundle via `git show "origin/data:$TRENDS_FILE"` → `sed` stamps `#gen-date` →
  `git init -q -b gh-pages` → commit → **`git push -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" gh-pages`**
  ← the PR 2 target line.
- Known wart (documented in #251 comments): a stuck Pages deployment blocks successors — recovery:
  `gh api -X POST repos/…/pages/deployments/<sha>/cancel` + push a fresh gh-pages commit.

### `src/ajoa_kit/sources.py` (PR 2)

- `get_json(url) -> tuple[Any, str]` and `get_bytes(url) -> tuple[bytes, str]` sit at the top of
  the module, both with the lazy `from polyfetch_scrape import FetchError, fetch` inside; both raise
  `FetchError(f"HTTP {status}…")` on non-200. Guard goes before the lazy import.
- Module imports: `json`, `urlencode`, `defusedxml…xml_fromstring`,
  `from ajoa_kit.normalize import canonical_url, html_to_text, record`. No cycle risk: nothing
  imports back into sources except `ingest.py`.
- Contrast: `src/ajoa_kit/slug_probe.py::fetch_status` has the inline guard
  `if not url.lower().startswith(("http://", "https://")): return None` — the **None** contract;
  do not unify.

### `tests/test_fetch.py` (PR 2)

- 4 tests covering `sources.get_json/get_bytes` (Accept header, non-200 → `FetchError`); injects a
  fake module via `monkeypatch.setitem(sys.modules, "polyfetch_scrape", mod)` — copy that fixture
  shape for the scheme tests (the fake must NOT be reached on rejected schemes).

### `src/ajoa_kit/persist_offer.py` (PR 2)

- `_NON_SLUG = re.compile(r"[^a-z0-9]+")`; `safe_slug(raw) -> str` =
  `_NON_SLUG.sub("-", raw.lower()).strip("-")`, raises `ValueError` when empty after sanitizing.
  Callers: `offer_dir = results_dir / "offers" / safe_slug(slug)` and `meta.json` write.
- **`tests/test_persist_offer.py` does not exist yet** — the pin test creates it (persist_offer is
  otherwise covered only via `tests/test_e2e_pipeline.py`).

### `src/ajoa_kit/style.py` + `tests/test_style.py` (PR 3)

- `@dataclass class StyleBrief`: `tone: str = ""`, `cv_sample: str = ""`,
  `cover_letter_sample: str = ""` — no methods, no `frozen`, `asdict` unused repo-wide.
- `load_style(config_dir) -> StyleBrief`: missing `style.json` → neutral brief; else
  `tone=cfg.get("tone","") or ""` + samples read via `_read_sample` (cap `SAMPLE_CAP = 6000`,
  missing referenced file raises `FileNotFoundError`).
- `directive(brief, artifact)` → precedence sample > tone > neutral;
  `as_directives(brief) -> {"cv": …, "coverLetter": …}` (hand-built dict — **the `--json` shape
  never touches the dataclass**); `main(config_dir, as_json)` prints
  `json.dumps(directives, indent=2, ensure_ascii=False)`.
- Importers of `StyleBrief`: only `style.py` itself and `tests/test_style.py` (kwarg construction
  in a Hypothesis property). `__main__.py` imports only `style.main`.
- `tests/test_style.py`: 5 example tests + 1 property class; **none pins `main(as_json=True)`
  stdout** — that's the new pin.

### `src/ajoa_kit/models.py` (PR 3)

- Holds `Lane`, `ScoredItem` (`extra="allow"`), `WeekCounts`, `DayCounts`, `MonthCounts`; docstring
  enumerates the family — StyleBrief joins it. `AppSettings` stays in `settings.py` by convention.

### Docs (PR 1 targets)

- `CONTRIBUTING.md`: §Trends data branch carries the stale "no redeploy" sentence; the env table
  (`AJOA_*`, `POLYFETCH_DIR`, `PORT`) lacks `TRENDS_FORCE`.
- `ui/README.md`: same stale sentence near the `make trends-data` block; files table already
  reflects the module split.
- `docs/architecture.md`: same-origin bundling paragraph + a "(re-deploys on data-branch pushes)"
  claim; contracts table row for style is the PR 3 target.
- `docs/roadmap.md`: Shipped list ends at the Wave-2 monthly bullet — **no #249 epic bullet exists**.
- `Makefile`: `TRENDS_PUBLISH` variable + shrink guard with `TRENDS_FORCE` escape (context for the
  env-table row; not modified by this plan).

## Doc-impact matrix

| Doc | PR 1 | PR 2 | PR 3 |
|---|---|---|---|
| CHANGELOG fragment | ✅ Fixed (1 line) | ✅ Security | ✅ Changed |
| Root README | — | — | — |
| architecture.md | ✅ redeploy claim | — | ✅ contracts row |
| roadmap.md | ✅ #249 bullet + reliability line | — | — |
| userstory.md | no change (verified) | — | — |
| CONTRIBUTING | ✅ redeploy sentence + TRENDS_FORCE row | — | — |
| ui/README | ✅ redeploy sentence | — | — |

**Switch audit:** no new URL/env/CLI switches in any PR; pre-existing `TRENDS_FORCE` gap closed (PR 1).

## Issue lifecycle

`Closes #251` (PR 1) · `Closes #256` (PR 2) · `Closes #257` (PR 3). Post-batch housekeeping
(owner's call, outside plan): close #199 as declined-until-evidence; merge dependabot #240
(complexipy is a gate tool — check its CI) and plugins#181 on green.

## Handoff

The session handoff for this arc, merged in from the former `docs/handoffs/` folder (one file per arc). Historical: this arc is closed.

**State:** `main` clean, synced (post PR #258). Plan (approved, with full source map):
[docs/plans/003-deploy-hygiene-hardening-typing.md](003-deploy-hygiene-hardening-typing.md).
**Nothing of plan 003 is implemented yet** — three PRs, execute in order.

**Session context (2026-07-05, all shipped):** Wave 1 `verify-sources` + seed backfill (#217½,
PR #247) · Wave 2 monthly trends data layer (#188½, PR #248) · refactor epic #249 closed via
PRs #250/#253/#254 (models → `models.py`; `defaults.py` + tracked `config/keywords.json` SSOT;
`ingest.py` split into `sources.py` / `normalize.py`; `TRENDS_PUBLISH` + shrink guard; `app.js` →
orchestrator + 3 ES modules) · cron heal (#252, `defusedxml` `--with` trio) · button contrast fix
(#255, `appearance: none`, reporter-confirmed) · footer version (#258, bump-managed) · plugins repo:
`triaging-security-report` skill v1.2.0. Issues #251/#256/#257 were filed from this session's
evidence — plan 003 closes all three.

### The three PRs (detail + source map in the plan — don't re-explore)

1. **`fix/deploy-hygiene`** (closes #251): delete gh-pages.yaml's `paths:` block; fix the stale
   "no redeploy" claim in CONTRIBUTING + ui/README; add `TRENDS_FORCE` to the CONTRIBUTING env
   table; add the missing #249 epic bullet + a reliability line to roadmap; 1-line `Fixed` fragment.
   **Glue only — zero tests.**
2. **`harden/batch`** (closes #256): TDD scheme guard on `sources.get_json/get_bytes`
   (`ValueError` on non-http(s); `slug_probe` untouched — different contract); new
   `tests/test_persist_offer.py` pinning `safe_slug` (examples + small Hypothesis property);
   token-out-of-argv credential-helper swap in gh-pages.yaml (exact snippet in the plan);
   `Security` fragment. **Verify by a real dispatched deploy** — the credential swap is only proven
   by an actual push.
3. **`refactor/style-brief`** (closes #257): pin `ajoa-kit style --json` stdout byte-for-byte
   FIRST (green→green — the swap can't change it: `as_directives` hand-builds the dict), then
   `StyleBrief` → pydantic in `models.py`; `style.py` re-imports it (zero test churn);
   architecture contracts-table row; `Changed` fragment.

### Per-slice recipe

branch off fresh `main` → (PR 2/3) tests first → implement → **gate LAST** (`make check`; changed
docs via `markdownlint-cli2 --no-globs <files>`) → CHANGELOG fragment → commit by topic
(`--no-gpg-sign`) → `env -u GH_TOKEN -u GITHUB_TOKEN git push` → PR with `Closes #n` →
`gh pr checks <n> --watch` → `gh pr merge <n> --squash --delete-branch` → prune local
branch → sync `main` before the next PR.

### Gotchas (this environment)

- All `gh` / `git push`: prefix `env -u GH_TOKEN -u GITHUB_TOKEN` (bare `gh` 401s;
  `gh auth setup-git` once per session before the first push).
- **Gate runs LAST**: run `ruff --fix` / formatters BEFORE `make check`; any edit *after* the gate
  (even a comment) → re-run the full gate. (Two CI reds this session from skipping this.)
- Borrowed polyfetch venv for live/import checks:
  `PYTHONPATH=src AJOA_CONFIG_DIR=config uv run --directory ../polyfetch-scrape --with pydantic
  --with pydantic-settings --with defusedxml python -m ajoa_kit <verb>` (all three `--with` needed;
  `defusedxml` is no longer transitive from polyfetch).
- Denied Bash here: `tail`/`cat`/`head`/`grep`-with-pipe/`-A`/`ls`/`find`/`;`-chains/`sleep` — use
  Read/Grep tools and `&&`-chains; write long command output to the scratchpad then Read it.
- `make ui-check` needs `POLYFETCH_DIR` (patchright); it now allowlists the by-design
  `shortlist.json` 404. ruff line length = 100; complexipy max = 10/function.
- Pages deploy can wedge (stuck `building`) — recovery in #251 comments; a raw `polyfetch.fetch` of
  an expected `src/*.js` beats render checks for "is the split actually live" (a stale bundle
  renders identically).

### Next / open (post-plan-003)

- **Wave 3** (#187 + #188 UI half): Daily/Monthly dropdown + same-origin bundles + synthetic-data
  banner, built on the now-isolated `ui/src/trends.js`. Do once ~3–4 wks of daily data accrue.
- **Deferred/parked (leave open):** #195 (JobRecord half), #217 (scheduled re-probe). **Blocked:**
  #193 (`qte77/.github#33` still OPEN). **Decision pending:** #199 (recommend close as declined).
- **Plugins repo:** #190 (OWASP-LLM skill + ATLAS→`securing-mas`; recon attached — ATLAS half is a
  copy/reformat from `ai-agents-research/docs/sdlc-lcm/ai-security-governance-analysis.md`).
- **`temp/docs/`** (outside repo): PDF-author feedback + live-verification report — owner to send.

### Touch points (current state — verify, don't re-map)

> Pre-implementation snapshot. Full symbol-level source map is in the
> [plan](#source-map-verified-2026-07-05--symbol-anchors-no-line-numbers-re-verify-before-editing).

| PR | File | Current state to verify against |
|---|---|---|
| 1 | `.github/workflows/gh-pages.yaml` | `on.push` has `branches: [main, data]` **+ a `paths:` list** → delete the list. |
| 1 | `CONTRIBUTING.md` / `ui/README.md` | both carry "no redeploy" wording; CONTRIBUTING env table lacks `TRENDS_FORCE`. |
| 1 | `docs/roadmap.md` | Shipped list ends at the Wave-2 monthly bullet — **no #249 epic bullet**. |
| 2 | `src/ajoa_kit/sources.py` | `get_json`/`get_bytes` — no scheme guard; lazy `polyfetch_scrape` import inside; raise `FetchError` on non-200. |
| 2 | `tests/test_fetch.py` | fakes `polyfetch_scrape` via `monkeypatch.setitem(sys.modules, …)` — copy for scheme tests. |
| 2 | `src/ajoa_kit/persist_offer.py` | `safe_slug` = `_NON_SLUG.sub("-", raw.lower()).strip("-")`, raises on empty. **`tests/test_persist_offer.py` absent** → the pin creates it. |
| 2 | `.github/workflows/gh-pages.yaml` | publish step pushes via `https://x-access-token:${GH_TOKEN}@…` → credential-helper swap. |
| 3 | `src/ajoa_kit/style.py` | `@dataclass StyleBrief(tone, cv_sample, cover_letter_sample = "")`; `as_directives` hand-builds `{cv, coverLetter}` (dataclass never serialized); only `style.py` + `test_style.py` reference it. |
| 3 | `src/ajoa_kit/models.py` | holds Lane/ScoredItem/Week/Day/MonthCounts → StyleBrief joins; docstring enumerates the family. |
| 3 | `tests/test_style.py` | 5 examples + 1 property; **no `main(as_json=True)` stdout pin** → the new test adds it. |
