#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# The summary has its own durable retry/outbox. A mail outage must not block data preparation.
bash "$SCRIPT_DIR/run_contest_daily_report.sh" || true
exec bash "$SCRIPT_DIR/run_contest_premarket.sh" --warm-only --until 23:50
