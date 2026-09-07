#!/usr/bin/env bash
set -euo pipefail

# On-demand KIS paper-account refresh worker. This script never submits orders.
ROOT="${MESUGAK_V2_ROOT:-/home/2023112374/mesugak/v2}"
PYTHON_BIN="${MESUGAK_PYTHON_BIN:-$ROOT/venv/bin/python}"

exec "$PYTHON_BIN" "$ROOT/functions/jobs/school_paper_trader.py" --process-refresh-requests --market "${MESUGAK_MARKET:-KR}"
