#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ROOT="${MESUGAK_V2_ROOT:-$DEFAULT_ROOT}"

ENV_FILE="$ROOT/.env.server"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
ROOT="${MESUGAK_V2_ROOT:-$ROOT}"
FUNCTIONS_ENV_FILE="${MESUGAK_ENV_FILE:-$ROOT/functions/.env}"
if [[ "$FUNCTIONS_ENV_FILE" != /* ]]; then
  FUNCTIONS_ENV_FILE="$ROOT/$FUNCTIONS_ENV_FILE"
fi
if [[ -f "$FUNCTIONS_ENV_FILE" ]]; then
  set -a
  source "$FUNCTIONS_ENV_FILE"
  set +a
fi

PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
exec "$PYTHON_BIN" "$ROOT/functions/jobs/watch_public_data.py" \
  --root "$ROOT" \
  --runner "$ROOT/server_runtime/run_v2_kr_close.sh" \
  --marker "$ROOT/runtime/watch/public_data_KR.json" \
  --start-hour "${MESUGAK_PUBLIC_DATA_WATCH_START_HOUR:-13}" \
  --end-hour "${MESUGAK_PUBLIC_DATA_WATCH_END_HOUR:-23}" \
  --max-age-days "${MESUGAK_PUBLIC_DATA_MAX_AGE_DAYS:-14}" \
  --retry-minutes "${MESUGAK_PUBLIC_DATA_RETRY_MINUTES:-30}"
