#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT/.env.server" ]]; then
  set -a
  source "$ROOT/.env.server"
  set +a
fi
ROOT="${MESUGAK_V2_ROOT:-$ROOT}"
ENV_FILE="${MESUGAK_ENV_FILE:-functions/.env}"
[[ "$ENV_FILE" == /* ]] || ENV_FILE="$ROOT/$ENV_FILE"
set -a
source "$ENV_FILE"
set +a
cd "$ROOT"
mkdir -p "$ROOT/runtime/cost"
exec 9>"$ROOT/runtime/maintenance.lock"
flock -n 9 || exit 0
"${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}" "$ROOT/functions/jobs/maintain_cloud_storage.py" \
  --mode archive-candidates --limit 5000 >> "$ROOT/runtime/cost/maintenance.log" 2>&1
if [[ ! -f "$ROOT/runtime/cost/analysis-compacted" ]]; then
  "${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}" "$ROOT/functions/jobs/maintain_cloud_storage.py" \
    --mode compact-analysis --limit 5000 >> "$ROOT/runtime/cost/maintenance.log" 2>&1
fi
