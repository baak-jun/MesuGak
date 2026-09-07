#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$SCRIPT_DIR"
if [[ ! -f "$DEFAULT_ROOT/functions/jobs/analyze_market.py" ]]; then
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
LOG_DIR="$ROOT/runtime/cron"
FUNCTIONS_ENV_FILE="${MESUGAK_ENV_FILE:-$ROOT/functions/.env}"
if [[ "$FUNCTIONS_ENV_FILE" != /* ]]; then
  FUNCTIONS_ENV_FILE="$ROOT/$FUNCTIONS_ENV_FILE"
fi
if [[ -f "$FUNCTIONS_ENV_FILE" ]]; then
  set -a
  source "$FUNCTIONS_ENV_FILE"
  set +a
fi
cd "$ROOT"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
mkdir -p "$LOG_DIR"

set +e
(
  set -e
  echo "[V2_KR_CRON] $(date '+%F %T %Z') start"
  args=(
    --market KR
    --kr-markets "${MESUGAK_KR_MARKETS:-KOSPI,KOSDAQ}"
    --checkpoint-dir "$ROOT/runtime/checkpoints"
    --progress-interval "${MESUGAK_PROGRESS_INTERVAL:-25}"
  )
  if [[ -n "${MESUGAK_MAX_STOCKS:-}" ]]; then
    args+=(--max-stocks "$MESUGAK_MAX_STOCKS")
  fi
  "$PYTHON_BIN" "$ROOT/functions/jobs/analyze_market.py" "${args[@]}"
  "$PYTHON_BIN" "$ROOT/functions/jobs/publish_public_analysis.py" --market KR
  echo "[V2_KR_CRON] public analysis feed published"
  "$PYTHON_BIN" "$ROOT/functions/jobs/publish_private_performance.py" --market KR
  echo "[V2_KR_CRON] private paper-performance comparison processed"
  "$PYTHON_BIN" "$ROOT/functions/jobs/monitor_school_server.py" --mark-success --market KR --root "$ROOT"
  echo "[V2_KR_CRON] $(date '+%F %T %Z') end status=0"
) >> "$LOG_DIR/v2_kr_close.log" 2>&1
status=$?
set -e

if (( status != 0 )); then
  "$PYTHON_BIN" "$ROOT/functions/jobs/monitor_school_server.py" \
    --notify-failure \
    --market KR \
    --root "$ROOT" \
    --detail "run_v2_kr_close.sh exited with status=$status. Log: $LOG_DIR/v2_kr_close.log" \
    >> "$LOG_DIR/v2_kr_close.log" 2>&1 || true
  exit "$status"
fi
