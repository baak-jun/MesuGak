#!/usr/bin/env bash
set -euo pipefail

# Scheduled site-linked KIS paper trader. Load server settings before functions/.env
# so Firebase credential paths and the selected Python runtime are available.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
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

if [[ -n "${MESUGAK_PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$MESUGAK_PYTHON_BIN"
elif [[ -x "$ROOT/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "MesuGak paper trader Python is not executable" >&2
  exit 1
fi

ARGS=(--market "${MESUGAK_MARKET:-KR}")
if (( $# == 0 )); then
  ARGS+=(--execute)
else
  ARGS+=("$@")
fi

exec "$PYTHON_BIN" "$ROOT/functions/jobs/school_paper_trader.py" "${ARGS[@]}"
