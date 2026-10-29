#!/usr/bin/env bash
# Preflight for the network-touching subcommands (#341): checks the polyfetch-scrape checkout,
# its patchright Chromium, and the Stage-1 evidence library, then prints exactly what is missing.
#
#   POLYFETCH_DIR=../polyfetch-scrape scripts/doctor.sh          # report only
#   POLYFETCH_DIR=../polyfetch-scrape scripts/doctor.sh --fix    # also install a missing Chromium
#
# Run --fix unsandboxed: a sandboxed `patchright install` can exit 0 and print a full download
# while its writes to $HOME are discarded. That is why the Chromium binary is asserted on disk
# below rather than trusting the installer's exit code.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" # repo root
POLYFETCH_DIR="${POLYFETCH_DIR:-${HERE}/../polyfetch-scrape}"
RESULTS_DIR="${AJOA_RESULTS_DIR:-${HERE}/results}"
fail=0

if [ ! -f "${POLYFETCH_DIR}/pyproject.toml" ]; then
  echo "polyfetch: missing at ${POLYFETCH_DIR} — git clone https://github.com/qte77/polyfetch-scrape there and run uv sync (or set POLYFETCH_DIR)"
  exit 1
fi
echo "polyfetch: ok (${POLYFETCH_DIR})"

# `polyfetch doctor` launches Chromium (a real headless launch); --fix installs it when missing.
uv run --directory "${POLYFETCH_DIR}" polyfetch doctor "$@" || fail=1

# Ask patchright where its Chromium executable should be, then check that file exists.
exe="$(uv run --directory "${POLYFETCH_DIR}" python -c \
  'from patchright.sync_api import sync_playwright
with sync_playwright() as pw: print(pw.chromium.executable_path)' 2>/dev/null)"
if [ -n "${exe}" ] && [ -x "${exe}" ]; then
  echo "chromium binary: ok (${exe})"
else
  echo "chromium binary: not on disk (${exe:-path unknown}) — run: make doctor FIX=1, unsandboxed"
  fail=1
fi

if [ -f "${RESULTS_DIR}/evidence-library.json" ]; then
  echo "evidence library: ok (${RESULTS_DIR}/evidence-library.json)"
else
  echo "evidence library: missing — build it with .claude/workflows/cc-workflow-evidence-library.js (see docs/quickstart.md)"
  fail=1
fi

exit "${fail}"
