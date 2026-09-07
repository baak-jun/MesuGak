#!/usr/bin/env bash
set -euo pipefail

# On-demand KIS paper-account refresh worker. This script never submits orders.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$SCRIPT_DIR"
if [[ ! -f "$DEFAULT_ROOT/functions/jobs/school_paper_trader.py" ]]; then
  DEFAULT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
fi
ROOT="${MESUGAK_V2_ROOT:-$DEFAULT_ROOT}"
for ENV_FILE in "$ROOT/.env.server" "${MESUGAK_ENV_FILE:-$ROOT/functions/.env}"; do
  if [[ "$ENV_FILE" != /* ]]; then
    ENV_FILE="$ROOT/$ENV_FILE"
  fi
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
  fi
done
ROOT="${MESUGAK_V2_ROOT:-$ROOT}"
cd "$ROOT"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${MESUGAK_PYTHON_BIN:-python3}"
fi

exec "$PYTHON_BIN" "$ROOT/functions/jobs/school_paper_trader.py" --process-refresh-requests --market "${MESUGAK_MARKET:-KR}"
