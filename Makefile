# Makefile — agentic-job-offer-to-application-kit
# `make help` lists every target; CONTRIBUTING.md §Commands is the prose reference.
#
# Recipes run under the default /bin/sh (POSIX — no `SHELL := bash`); `-e -u` keep
# the .ONESHELL recipes failing fast on the first error / unset variable.

.ONESHELL:
.SILENT:
.SHELLFLAGS := -eu -c
.DEFAULT_GOAL := help

.PHONY: \
	help \
	install-uv install install_docs_tools \
	check lint format check_types check_complexity docs-lint \
	ingest chunk persist probe \
	preview trends-data ui-check \
	changelog_new changelog_preview changelog_release

# MARK: Help

help: ## List available targets
	awk 'BEGIN { FS = ":.*##" } /^[a-zA-Z_-]+:.*##/ { printf "  %-19s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# MARK: Setup

install-uv: ## Install the uv toolchain (prerequisite for `make install`)
	curl -LsSf https://astral.sh/uv/install.sh | sh

install: ## Sync the dev environment (uv) — needs uv (see `make install-uv`)
	uv sync

install_docs_tools: ## Install docs-lint tools — markdownlint-cli2 (npm) + lychee (cargo); needs npm + cargo
	npm install -g markdownlint-cli2
	cargo install lychee

# MARK: Quality gates

check: ## Lint + types + complexity + format-check + offline tests + coverage (CI parity)
	uv run ruff check .
	uv run ruff format --check .
	uv run pyright src/ajoa_kit
	uv run complexipy src/ajoa_kit --max-complexity-allowed 10
	uv run pytest -m "not network" --cov=ajoa_kit --cov-report=term-missing

lint: ## Ruff lint
	uv run ruff check .

format: ## Ruff format (write)
	uv run ruff format .

check_types: ## Pyright type check
	uv run pyright src/ajoa_kit

check_complexity: ## Complexipy cognitive-complexity gate (max 10)
	uv run complexipy src/ajoa_kit --max-complexity-allowed 10

docs-lint: ## Markdown lint + link check (local)
	markdownlint-cli2 "*.md" "docs/**/*.md" "examples/**/*.md"
	lychee --config lychee.toml --no-progress *.md docs examples

# MARK: Pipeline

ingest: ## Ingest JDs into results/jobs-raw.json (set POLYFETCH_DIR)
	scripts/ingest.sh

chunk: ## Batch the ingested corpus into results/batches/
	uv run ajoa-kit chunk

persist: ## Persist a relevance result: make persist FILE=<output.json>
	test -n "$(FILE)" || { echo "usage: make persist FILE=<workflow-output.json>"; exit 2; }
	uv run ajoa-kit persist "$(FILE)"

probe: ## Probe candidate slugs across ATS platforms (set POLYFETCH_DIR)
	uv run ajoa-kit probe

# MARK: Dashboard

preview: ## Serve the dashboard locally with real trends in a throwaway copy (ui/ stays data-free)
	# Mirror the gh-pages deploy: copy ui/ into a temp dir and inject the PII-free trends THERE, so
	# the source ui/ never holds data. Prefer local sources (public-data/trends.ndjson, then a data ref);
	# only fetch as a last resort. Non-fatal -> synthetic fallback when nothing is found.
	site="$$(mktemp -d)"
	cp -r ui/. "$$site/"
	dst="$$site/public/data/trends.ndjson"
	if [ -f public-data/trends.ndjson ]; then
		cp public-data/trends.ndjson "$$dst"
		echo "preview: using local public-data/trends.ndjson ($$(wc -l < "$$dst") records)"
	elif git show data:public-data/trends.ndjson > "$$dst" 2>/dev/null \
		|| git show origin/data:public-data/trends.ndjson > "$$dst" 2>/dev/null \
		|| { git fetch -q origin data 2>/dev/null && git show origin/data:public-data/trends.ndjson > "$$dst" 2>/dev/null; }; then
		echo "preview: bundled trends from the data branch ($$(wc -l < "$$dst") records)"
	else
		rm -f "$$dst"
		echo "preview: no real trends available -> synthetic fallback"
	fi
	# Real shortlist (PII) -> aggregate the per-lane results/<lane>/shortlist.json into the throwaway
	# copy ONLY; never written to source ui/, never bundled by gh-pages.yaml (published stays synthetic).
	uv run python scripts/build_ui_shortlist.py "$$site/public/data/shortlist.json"
	echo "serving $$site -> http://localhost:$${PORT:-8000}/"
	uv run python -m http.server "$${PORT:-8000}" --directory "$$site"

ui-check: ## Headless-browser smoke for the dashboard (CSP/render/console); borrows POLYFETCH_DIR's patchright
	uv run --directory "$${POLYFETCH_DIR:-../polyfetch-scrape}" python "$(CURDIR)/scripts/ui_check.py"

# The publishable aggregate trend files (#210 allowlist + #188 monthly): weekly is required (the
# "did you run trend-snapshot" guard), the finer/coarser series are added when present. One
# definition feeds the add loop, the boundary guard and the echo below — extend it here only.
TRENDS_PUBLISH := public-data/trends.ndjson public-data/trends-daily.ndjson public-data/trends-monthly.ndjson

trends-data: ## Push $(TRENDS_PUBLISH) to the `data` branch (real trends for the live dashboard)
	test -f public-data/trends.ndjson || { echo "no public-data/trends.ndjson yet — run: uv run ajoa-kit trend-snapshot"; exit 2; }
	# Shrink guard (#249 slice D): refuse to overwrite the data branch with a SMALLER (or locally
	# absent) series — a silently-failed restore would otherwise wipe accumulated history on the
	# force-push (how the pre-#210 weekly history was lost). One NDJSON line == one bucket.
	# TRENDS_FORCE=1 skips the guard for an intentional prune.
	git fetch -q origin data 2>/dev/null || true
	for f in $(TRENDS_PUBLISH); do
		old="$$(git show "origin/data:$$f" 2>/dev/null | wc -l)"
		new="$$(test -f "$$f" && wc -l < "$$f" || echo 0)"
		if [ -z "$${TRENDS_FORCE:-}" ] && [ "$$new" -lt "$$old" ]; then
			echo "trends-data: refusing push — $$f would shrink $$old -> $$new buckets (TRENDS_FORCE=1 to override)"
			exit 1
		fi
	done
	# Aggregate trend files committed in a throwaway index (never touches the working tree), force-pushed
	# to the data branch; the dashboard fetches them at runtime via raw.githubusercontent.com. Only the
	# keyword-only {week,counts}/{date,counts}/{month,counts} files are added — no JD content can ride along.
	export GIT_INDEX_FILE="$$(mktemp -u)"
	git read-tree --empty
	for f in $(TRENDS_PUBLISH); do test -f "$$f" && git add -f "$$f" || true; done
	tree="$$(git write-tree)"
	# Boundary guard (#210): the pushed tree may contain ONLY the allowlisted aggregate files — abort
	# before push if any other path slipped in (structural defense for the PII boundary). Fail-closed:
	# an empty allowlist variable matches nothing and refuses every path.
	for f in $$(git ls-tree -r --name-only "$$tree"); do
		case " $(TRENDS_PUBLISH) " in
			*" $$f "*) ;;
			*) echo "trends-data: refusing to push unexpected path: $$f"; exit 1 ;;
		esac
	done
	commit="$$(git -c commit.gpgsign=false commit-tree "$$tree" -m "data: update trends")"
	git push -f origin "$$commit:refs/heads/data"
	echo "pushed $(TRENDS_PUBLISH) (where present) -> data branch ($$commit)"

# MARK: Changelog & release

changelog_new: ## Create + stage a new changelog fragment (scriv)
	uv run scriv create --add

changelog_preview: ## Preview the assembled release entry (scriv)
	uv run scriv print

changelog_release: ## Collect fragments into CHANGELOG.md: make changelog_release VERSION=X.Y.Z
	test -n "$(VERSION)" || { echo "usage: make changelog_release VERSION=X.Y.Z"; exit 2; }
	uv run scriv collect --version "$(VERSION)"
