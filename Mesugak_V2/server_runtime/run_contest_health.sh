#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MESUGAK_V2_ROOT:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
export TZ=Asia/Seoul
if [[ -f "$ROOT/.env.server" ]]; then
  set -a
  source "$ROOT/.env.server"
  set +a
fi
cd "$ROOT"
mkdir -p runtime/cron
exec 9>runtime/contest_health.lock
flock -n 9 || exit 0
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
exec "$PYTHON_BIN" "$ROOT/functions/jobs/contest_health_monitor.py" \
  --root "$ROOT" --env-file "${MESUGAK_CONTEST_ENV_FILE:-$ROOT/functions/.env.contest}"
