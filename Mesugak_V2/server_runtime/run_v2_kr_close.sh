#!/usr/bin/env bash
set -euo pipefail

ROOT="${MESUGAK_V2_ROOT:-/home/2023112374/mesugak-v2}"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-/home/2023112374/micromamba-root/envs/py312/bin/python}"
LOG_DIR="$ROOT/runtime/cron"
ENV_FILE="$ROOT/.env.server"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
mkdir -p "$LOG_DIR"

{
  echo "[V2_KR_CRON] $(date '+%F %T %Z') start"
  "$PYTHON_BIN" "$ROOT/functions/jobs/analyze_market.py" --market KR --kr-markets "${MESUGAK_KR_MARKETS:-KOSPI,KOSDAQ}" --checkpoint-dir "$ROOT/runtime/checkpoints"
  echo "[V2_KR_CRON] $(date '+%F %T %Z') end status=0"
} >> "$LOG_DIR/v2_kr_close.log" 2>&1
