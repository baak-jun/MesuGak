#!/usr/bin/env bash
set -euo pipefail

BOT_DIR="${MESUGAK_SERVER_ROOT:-/home/2023112374/chartbot}"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-/home/2023112374/micromamba-root/envs/py312/bin/python}"
SCRIPT="$BOT_DIR/oracle_chart_refresh.py"
CRON_LOG="$BOT_DIR/runtime/cron/us_close.log"
STAMP_FILE="$BOT_DIR/runtime/stamps/us_last_run.txt"

mkdir -p "$BOT_DIR/runtime/cron" "$BOT_DIR/runtime/stamps"
SHOULD_RUN="$(FORCE_RUN="${FORCE_RUN:-0}" STAMP_FILE="$STAMP_FILE" "$PYTHON_BIN" - <<'PY'
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
import os

if os.environ.get("FORCE_RUN") == "1":
    print("1")
    raise SystemExit
now = datetime.now(ZoneInfo("America/New_York"))
stamp = Path(os.environ["STAMP_FILE"])
print("1" if now.weekday() < 5 and now.time() >= time(16, 20) and (not stamp.exists() or stamp.read_text().strip() != now.date().isoformat()) else "0")
PY
)"

{
  echo "[US_CRON] $(date '+%F %T %Z') should_run=$SHOULD_RUN"
  [[ "$SHOULD_RUN" == "1" ]] || { echo "[US_CRON] skip"; exit 0; }
  "$PYTHON_BIN" "$SCRIPT" --market US
  date --iso-8601=date --date='TZ="America/New_York" now' > "$STAMP_FILE"
  echo "[US_CRON] $(date '+%F %T %Z') end status=0"
} >> "$CRON_LOG" 2>&1
