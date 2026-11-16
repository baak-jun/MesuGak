#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MESUGAK_V2_ROOT:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"

if [[ -f "$ROOT/.env.server" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env.server"
  set +a
fi
if [[ -n "${MESUGAK_CONTEST_ENV_FILE:-}" ]]; then
  FUNCTIONS_ENV_FILE="$MESUGAK_CONTEST_ENV_FILE"
elif [[ -f "$ROOT/functions/.env.contest" ]]; then
  FUNCTIONS_ENV_FILE="$ROOT/functions/.env.contest"
elif [[ -n "${MESUGAK_ENV_FILE:-}" ]]; then
  FUNCTIONS_ENV_FILE="$MESUGAK_ENV_FILE"
else
  FUNCTIONS_ENV_FILE="$ROOT/functions/.env"
fi
if [[ "$FUNCTIONS_ENV_FILE" != /* ]]; then
  FUNCTIONS_ENV_FILE="$ROOT/$FUNCTIONS_ENV_FILE"
fi
if [[ -f "$FUNCTIONS_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$FUNCTIONS_ENV_FILE"
  set +a
fi

PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
cd "$ROOT"
ARGS=("$ROOT/functions/jobs/kis_realtime_trader.py" --env-file "$FUNCTIONS_ENV_FILE")
if [[ "${MESUGAK_REALTIME_EXECUTE:-false}" == "true" ]]; then
  ARGS+=(--execute)
fi
ARGS+=("$@")

set +e
/usr/bin/flock -n -E 75 /tmp/mesugak-kis-realtime.lock "$PYTHON_BIN" "${ARGS[@]}"
RESULT=$?
set -e

EXECUTE_MODE=false
for ARG in "${ARGS[@]}"; do
  if [[ "$ARG" == "--execute" ]]; then EXECUTE_MODE=true; fi
done
if [[ "$EXECUTE_MODE" == true && "$RESULT" != 0 && "$RESULT" != 75 && "$RESULT" != 130 && "$RESULT" != 143 ]]; then
  "$PYTHON_BIN" "$ROOT/functions/jobs/contest_notifications.py" \
    --env-file "$FUNCTIONS_ENV_FILE" \
    --state-path "${MESUGAK_REALTIME_STATE_PATH:-runtime/realtime_order_state.sqlite3}" \
    --process-exit "$RESULT" || true
fi
exit "$RESULT"
