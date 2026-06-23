#!/usr/bin/env bash
set -euo pipefail

ROOT="${MESUGAK_V2_ROOT:-/home/2023112374/mesugak/v2}"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
LOG_DIR="$ROOT/runtime/cron"
STAMP_FILE="$ROOT/runtime/stamps/v2_us_last_run.txt"
ENV_FILE="$ROOT/.env.server"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

mkdir -p "$LOG_DIR" "$(dirname "$STAMP_FILE")"
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
  echo "[V2_US_CRON] $(date '+%F %T %Z') should_run=$SHOULD_RUN"
  [[ "$SHOULD_RUN" == "1" ]] || { echo "[V2_US_CRON] skip"; exit 0; }
  args=(
    --market US
    --checkpoint-dir "$ROOT/runtime/checkpoints"
    --progress-interval "${MESUGAK_PROGRESS_INTERVAL:-25}"
  )
  if [[ -n "${MESUGAK_MAX_STOCKS:-}" ]]; then
    args+=(--max-stocks "$MESUGAK_MAX_STOCKS")
  fi
  "$PYTHON_BIN" "$ROOT/functions/jobs/analyze_market.py" "${args[@]}"
  date --iso-8601=date --date='TZ="America/New_York" now' > "$STAMP_FILE"
  echo "[V2_US_CRON] $(date '+%F %T %Z') end status=0"
} >> "$LOG_DIR/v2_us_close.log" 2>&1
