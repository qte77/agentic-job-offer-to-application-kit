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
	# the source ui/ never holds data. Prefer local sources (results/trends.ndjson, then a data ref);
	# only fetch as a last resort. Non-fatal -> synthetic fallback when nothing is found.
	site="$$(mktemp -d)"
	cp -r ui/. "$$site/"
	dst="$$site/public/data/trends.ndjson"
	if [ -f results/trends.ndjson ]; then
		cp results/trends.ndjson "$$dst"
		echo "preview: using local results/trends.ndjson ($$(wc -l < "$$dst") records)"
	elif git show data:results/trends.ndjson > "$$dst" 2>/dev/null \
		|| git show origin/data:results/trends.ndjson > "$$dst" 2>/dev/null \
		|| { git fetch -q origin data 2>/dev/null && git show origin/data:results/trends.ndjson > "$$dst" 2>/dev/null; }; then
		echo "preview: bundled trends from the data branch ($$(wc -l < "$$dst") records)"
	else
		rm -f "$$dst"
		echo "preview: no real trends available -> synthetic fallback"
	fi
	echo "serving $$site -> http://localhost:$${PORT:-8000}/"
	uv run python -m http.server "$${PORT:-8000}" --directory "$$site"

ui-check: ## Headless-browser smoke for the dashboard (CSP/render/console); borrows POLYFETCH_DIR's patchright
	uv run --directory "$${POLYFETCH_DIR:-../polyfetch-scrape}" python "$(CURDIR)/scripts/ui_check.py"

trends-data: ## Push results/trends{,-daily}.ndjson to the `data` branch (real trends for the live dashboard)
	test -f results/trends.ndjson || { echo "no results/trends.ndjson yet — run: uv run ajoa-kit trend-snapshot"; exit 2; }
	# Aggregate trend files committed in a throwaway index (never touches the working tree), force-pushed
	# to the data branch; the dashboard fetches them at runtime via raw.githubusercontent.com. Only the
	# keyword-only {week,counts}/{date,counts} files are added — no JD content can ride along.
	export GIT_INDEX_FILE="$$(mktemp -u)"
	git read-tree --empty
	git add -f results/trends.ndjson
	test -f results/trends-daily.ndjson && git add -f results/trends-daily.ndjson || true
	tree="$$(git write-tree)"
	commit="$$(git -c commit.gpgsign=false commit-tree "$$tree" -m "data: update trends")"
	git push -f origin "$$commit:refs/heads/data"
	echo "pushed trends.ndjson (+ trends-daily.ndjson if present) -> data branch ($$commit)"

# MARK: Changelog & release

changelog_new: ## Create + stage a new changelog fragment (scriv)
	uv run scriv create --add

changelog_preview: ## Preview the assembled release entry (scriv)
	uv run scriv print

changelog_release: ## Collect fragments into CHANGELOG.md: make changelog_release VERSION=X.Y.Z
	test -n "$(VERSION)" || { echo "usage: make changelog_release VERSION=X.Y.Z"; exit 2; }
	uv run scriv collect --version "$(VERSION)"
