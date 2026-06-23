#!/usr/bin/env bash
set -euo pipefail

BOT_DIR="${MESUGAK_SERVER_ROOT:-/home/2023112374/chartbot}"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-/home/2023112374/micromamba-root/envs/py312/bin/python}"
SCRIPT="$BOT_DIR/oracle_chart_refresh.py"
CRON_LOG="$BOT_DIR/runtime/cron/kr_close.log"

mkdir -p "$BOT_DIR/runtime/cron"
{
  echo "[KR_CRON] $(date '+%F %T %Z') start"
  "$PYTHON_BIN" "$SCRIPT" --market KR --kr-markets KOSPI,KOSDAQ
  echo "[KR_CRON] $(date '+%F %T %Z') end status=0"
} >> "$CRON_LOG" 2>&1
