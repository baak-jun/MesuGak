#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$SCRIPT_DIR"
if [[ ! -f "$DEFAULT_ROOT/functions/jobs/monitor_school_server.py" ]]; then
  DEFAULT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
fi
ROOT="${MESUGAK_V2_ROOT:-$DEFAULT_ROOT}"
ENV_FILE="$ROOT/.env.server"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
ROOT="${MESUGAK_V2_ROOT:-$ROOT}"
ENV_FILE="${MESUGAK_ENV_FILE:-$ROOT/functions/.env}"
if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="$ROOT/$ENV_FILE"
fi
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
cd "$ROOT"

PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
mkdir -p "$ROOT/runtime/cron"
"$PYTHON_BIN" "$ROOT/functions/jobs/monitor_school_server.py" --check --market KR --root "$ROOT" \
  >> "$ROOT/runtime/cron/v2_health_monitor.log" 2>&1
