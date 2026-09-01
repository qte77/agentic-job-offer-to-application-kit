# Plan 003 — deploy hygiene (#251) · hardening batch (#256) · StyleBrief typing (#257)

Three small PRs, each closing one issue filed 2026-07-05, each grounded in evidence gathered that
session (the #251/#252 deploy incidents and the verified security-teardown triage). Approved in-session
2026-07-05; handoff: [docs/handoffs/003-deploy-hygiene-hardening-typing.md](../handoffs/003-deploy-hygiene-hardening-typing.md).

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
