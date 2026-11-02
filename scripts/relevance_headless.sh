#!/usr/bin/env bash
# Stage-2 relevance screen as detached headless `claude -p` slices (#342). Run after `make chunk`;
# collect with `make relevance_collect`. Launch it detached so it outlives the Claude session:
#
#   setsid nohup scripts/relevance_headless.sh > results/run/relevance/run.log 2>&1 < /dev/null &
#
# Every slice gets a fresh --session-id, written to $OUT/sessions.txt BEFORE it starts, so a slice
# that dies (container stop, the -p background wait limit) still leaves a findable workflow journal.
# Logs stay under results/ (git-ignored) because /tmp is wiped when the container restarts.
#
# Env: SLICES (default 4) splits all batches evenly; RANGES="start:limit ..." runs exactly those
# (the form `make relevance_collect` prints for gaps). MAX_AGENTS concurrent agents per slice
# (default 4), MIN_FREE_MB disk floor checked before each slice (default 1500).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" # repo root
cd "$HERE"
OUT=results/run/relevance
SLICES="${SLICES:-4}"
MAX_AGENTS="${MAX_AGENTS:-4}"
MIN_FREE_MB="${MIN_FREE_MB:-1500}"
mkdir -p "$OUT"

N=$(python3 -I -c "import json; print(json.load(open('results/batches/manifest.json'))['batch_count'])")
if [[ -z "${RANGES:-}" ]]; then
  # A full run starts a fresh sessions file (an older one would mix in another chunk's batches);
  # a RANGES gap re-run appends to the current one.
  [[ -f "$OUT/sessions.txt" ]] && mv "$OUT/sessions.txt" "$OUT/sessions.$(date -u +%Y%m%dT%H%M%SZ).txt"
  SIZE=$(((N + SLICES - 1) / SLICES))
  RANGES=$(for ((s = 0; s * SIZE < N; s++)); do printf '%s:%s ' $((s * SIZE)) "$SIZE"; done)
fi
# The workflow's runtime inputs: lanes always; location/tenure are inert when unconfigured.
uv run --quiet ajoa-kit lanes --json > "$OUT/lanes.json"
uv run --quiet ajoa-kit location --json > "$OUT/location.json"
uv run --quiet ajoa-kit tenure --json > "$OUT/tenure.json"

for r in $RANGES; do
  start=${r%%:*} limit=${r##*:}
  free=$(df --output=avail -m . | sed -n 2p)
  if ((free < MIN_FREE_MB)); then
    echo "$(date -u +%FT%TZ) ABORT before batch $start: ${free} MB free (< ${MIN_FREE_MB})"
    break
  fi
  sid=$(python3 -I -c "import uuid; print(uuid.uuid4())")
  echo "$sid  # batches $start..$((start + limit - 1)) of $N" >> "$OUT/sessions.txt"
  args=$(python3 -I -c "
import json, sys
out = sys.argv[4]
print(json.dumps({'rootDir': '.', 'batchCount': int(sys.argv[1]), 'startBatch': int(sys.argv[2]),
  'limitBatches': int(sys.argv[3]), 'lanes': json.load(open(f'{out}/lanes.json')),
  'location': json.load(open(f'{out}/location.json')), 'tenure': json.load(open(f'{out}/tenure.json'))}))
" "$N" "$start" "$limit" "$OUT")
  # -p stops background workflows 10 min after its last turn unless this ceiling is 0.
  CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS="$MAX_AGENTS" \
    claude -p --session-id "$sid" \
    "Call the Workflow tool with scriptPath '$HERE/.claude/workflows/cc-workflow-relevance.js' and args $args. Wait for it to finish, then reply with only: done" \
    --allowedTools "Workflow" "Read" --permission-mode acceptEdits --output-format json \
    > "$OUT/slice-$start.json" 2> "$OUT/slice-$start.err" &
  echo "$(date -u +%FT%TZ) slice $sid: batches $start..$((start + limit - 1)) of $N (${free} MB free)"
done
wait
echo "$(date -u +%FT%TZ) all slices ended; collect with: make relevance_collect"
