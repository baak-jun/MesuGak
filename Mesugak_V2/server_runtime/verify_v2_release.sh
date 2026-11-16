#!/usr/bin/env bash
set -euo pipefail

# Read-only release check for the school server. It never sources .env files,
# prints secret values, calls the public API, or touches Firestore.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$SCRIPT_DIR"
if [[ ! -f "$DEFAULT_ROOT/functions/jobs/analyze_market.py" ]]; then
  DEFAULT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
fi
ROOT="${MESUGAK_V2_ROOT:-$DEFAULT_ROOT}"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"

cd "$ROOT"
echo "root=$ROOT"
echo "python=$PYTHON_BIN"

required_files=(
  "functions/jobs/analyze_market.py"
  "functions/jobs/publish_public_analysis.py"
  "functions/jobs/monitor_school_server.py"
  "functions/jobs/watch_public_data.py"
  "server_runtime/run_v2_kr_close.sh"
  "server_runtime/run_v2_kr_watch.sh"
  "server_runtime/run_v2_health_monitor.sh"
)

missing=0
for relative in "${required_files[@]}"; do
  path="$ROOT/$relative"
  if [[ ! -f "$path" ]]; then
    echo "MISSING $relative"
    missing=1
  else
    if command -v sha256sum >/dev/null 2>&1; then
      digest="$(sha256sum "$path" | awk '{print $1}')"
    else
      digest="sha256-unavailable"
    fi
    echo "OK $relative sha256=$digest"
  fi
done
(( missing == 0 )) || exit 2

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "MISSING executable Python: $PYTHON_BIN"
  exit 3
fi
"$PYTHON_BIN" --version
"$PYTHON_BIN" -m pip check

if [[ -f "$ROOT/functions/.env" ]]; then
  echo "OK functions/.env exists (values hidden)"
else
  echo "MISSING functions/.env"
  exit 4
fi

for key in DATA_GO_KR_SERVICE_KEY MESUGAK_GMAIL_USER MESUGAK_GMAIL_APP_PASSWORD MESUGAK_ALERT_EMAIL_TO; do
  if grep -Eq "^${key}=" "$ROOT/functions/.env"; then
    echo "OK env $key is present"
  else
    echo "MISSING env $key"
    exit 5
  fi
done

if [[ -f "$ROOT/runtime/watch/public_data_KR.json" ]]; then
  "$PYTHON_BIN" - "$ROOT/runtime/watch/public_data_KR.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"INVALID watcher marker: {exc}")
    raise SystemExit(6)
print({
    "watcher_status": payload.get("status"),
    "latestAvailableDate": payload.get("latestAvailableDate"),
    "checkedAt": payload.get("checkedAt"),
    "lastRunAt": payload.get("lastRunAt"),
})
PY
else
  echo "INFO runtime/watch/public_data_KR.json is not present yet"
fi

if command -v crontab >/dev/null 2>&1; then
  echo "--- matching cron entries (secret values are not printed) ---"
  crontab -l 2>/dev/null | grep -E 'run_v2_(kr_watch|health_monitor|kr_close)' || echo "no matching cron entry"
fi

echo "VERIFY_V2_RELEASE_OK"
