#!/usr/bin/env bash
set -euo pipefail

ROOT="${MESUGAK_V2_ROOT:-/home/2023112374/mesugak/v2}"
for ENV_FILE in "$ROOT/.env.server" "${MESUGAK_ENV_FILE:-$ROOT/functions/.env}"; do
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
  fi
done

PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
mkdir -p "$ROOT/runtime/cron"
"$PYTHON_BIN" "$ROOT/functions/jobs/monitor_school_server.py" --check --market KR --root "$ROOT" \
  >> "$ROOT/runtime/cron/v2_health_monitor.log" 2>&1
