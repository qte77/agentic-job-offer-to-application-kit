#!/usr/bin/env bash
# Stage-2 ingestion runner. Borrows polyfetch's uv environment so `polyfetch_scrape`
# imports without installing anything into this repo. Output goes to results/ (repo root),
# regardless of the working directory `uv run --directory` switches to.
#
#   POLYFETCH_DIR=../polyfetch-scrape scripts/ingest.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" # repo root
POLYFETCH_DIR="${POLYFETCH_DIR:-${HERE}/../polyfetch-scrape}"
export AJOA_CONFIG_DIR="${HERE}/config"
export AJOA_RESULTS_DIR="${HERE}/results"
export PYTHONPATH="${HERE}/src"
# --with lists every ajoa_kit dep polyfetch's env doesn't ship (defusedxml stopped being
# transitive when polyfetch dropped its arXiv vertical, 6f42aa2).
exec uv run --directory "${POLYFETCH_DIR}" \
  --with pydantic --with pydantic-settings --with defusedxml \
  python -m ajoa_kit ingest "$@"
