SHELL := bash
.ONESHELL:
.SILENT:
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.PHONY: help install lint format check docs-lint ingest chunk persist probe

help: ## List available targets
	awk 'BEGIN { FS = ":.*##" } /^[a-zA-Z_-]+:.*##/ { printf "  %-11s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Sync the dev environment (uv)
	uv sync

lint: ## Ruff lint
	uv run ruff check .

format: ## Ruff format (write)
	uv run ruff format .

check: ## Lint + format-check + offline tests (CI parity)
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest -m "not network"

docs-lint: ## Markdown lint + link check (local)
	markdownlint-cli2 "*.md" "docs/**/*.md" "examples/**/*.md"
	lychee --config lychee.toml --no-progress README.md CHANGELOG.md AGENTS.md docs examples

ingest: ## Ingest JDs into results/jobs-raw.json (set POLYFETCH_DIR)
	scripts/ingest.sh

chunk: ## Batch the ingested corpus into results/batches/
	uv run ajoa-kit chunk

persist: ## Persist a relevance result: make persist FILE=<output.json>
	test -n "$(FILE)" || { echo "usage: make persist FILE=<workflow-output.json>"; exit 2; }
	uv run ajoa-kit persist "$(FILE)"

probe: ## Probe candidate slugs across ATS platforms (set POLYFETCH_DIR)
	uv run ajoa-kit probe
