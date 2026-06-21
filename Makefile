SHELL := bash
.ONESHELL:
.SILENT:
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.PHONY: help install lint format preview trends-data check check_types check_complexity docs-lint ingest chunk persist probe changelog_new changelog_preview changelog_release

help: ## List available targets
	awk 'BEGIN { FS = ":.*##" } /^[a-zA-Z_-]+:.*##/ { printf "  %-11s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Sync the dev environment (uv)
	uv sync

lint: ## Ruff lint
	uv run ruff check .

format: ## Ruff format (write)
	uv run ruff format .

preview: ## Serve the ui/ dashboard locally (PORT defaults to 8000)
	uv run python -m http.server "$${PORT:-8000}" --directory ui

trends-data: ## Push results/trends.ndjson to the `data` branch (real trends for the live dashboard)
	test -f results/trends.ndjson || { echo "no results/trends.ndjson yet — run: uv run ajoa-kit trend-snapshot"; exit 2; }
	# One-file commit built in a throwaway index (never touches the working tree), force-pushed to the
	# data branch; the live dashboard fetches it at runtime via raw.githubusercontent.com.
	export GIT_INDEX_FILE="$$(mktemp -u)"
	git read-tree --empty
	git add -f results/trends.ndjson
	tree="$$(git write-tree)"
	commit="$$(git -c commit.gpgsign=false commit-tree "$$tree" -m "data: update trends.ndjson")"
	git push -f origin "$$commit:refs/heads/data"
	echo "pushed results/trends.ndjson -> data branch ($$commit)"

check: ## Lint + types + complexity + format-check + offline tests + coverage (CI parity)
	uv run ruff check .
	uv run ruff format --check .
	uv run pyright src/ajoa_kit
	uv run complexipy src/ajoa_kit --max-complexity-allowed 10
	uv run pytest -m "not network" --cov=ajoa_kit --cov-report=term-missing

check_types: ## Pyright type check
	uv run pyright src/ajoa_kit

check_complexity: ## Complexipy cognitive-complexity gate (max 10)
	uv run complexipy src/ajoa_kit --max-complexity-allowed 10

docs-lint: ## Markdown lint + link check (local)
	markdownlint-cli2 "*.md" "docs/**/*.md" "examples/**/*.md"
	lychee --config lychee.toml --no-progress README.md CHANGELOG.md AGENTS.md CONTRIBUTING.md docs examples

ingest: ## Ingest JDs into results/jobs-raw.json (set POLYFETCH_DIR)
	scripts/ingest.sh

chunk: ## Batch the ingested corpus into results/batches/
	uv run ajoa-kit chunk

persist: ## Persist a relevance result: make persist FILE=<output.json>
	test -n "$(FILE)" || { echo "usage: make persist FILE=<workflow-output.json>"; exit 2; }
	uv run ajoa-kit persist "$(FILE)"

probe: ## Probe candidate slugs across ATS platforms (set POLYFETCH_DIR)
	uv run ajoa-kit probe

changelog_new: ## Create + stage a new changelog fragment (scriv)
	uv run scriv create --add

changelog_preview: ## Preview the assembled release entry (scriv)
	uv run scriv print

changelog_release: ## Collect fragments into CHANGELOG.md: make changelog_release VERSION=X.Y.Z
	test -n "$(VERSION)" || { echo "usage: make changelog_release VERSION=X.Y.Z"; exit 2; }
	uv run scriv collect --version "$(VERSION)"
