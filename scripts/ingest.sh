#!/usr/bin/env bash
# Stage-2 ingestion runner. Borrows polyfetch's uv environment so `polyfetch_scrape`
# imports without installing anything into this repo. Output goes to results/ (repo root),
# regardless of the working directory `uv run --directory` switches to.
#
#   POLYFETCH_DIR=../polyfetch-scrape scripts/ingest.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" # repo root
POLYFETCH_DIR="${POLYFETCH_DIR:-${HERE}/../polyfetch-scrape}"
exec uv run --directory "${POLYFETCH_DIR}" \
  python "${HERE}/src/ajoa_kit/ingest.py" "$@"
