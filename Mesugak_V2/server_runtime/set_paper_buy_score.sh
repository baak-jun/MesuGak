#!/usr/bin/env bash
set -euo pipefail

# Usage: ./set_paper_buy_score.sh 55 [path/to/functions/.env]
# Updates only the entry threshold used for future paper-trading BUY orders.

SCORE="${1:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$SCRIPT_DIR"
if [[ ! -f "$DEFAULT_ROOT/functions/jobs/school_paper_trader.py" ]]; then
  DEFAULT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
fi
ENV_FILE="${2:-${MESUGAK_ENV_FILE:-$DEFAULT_ROOT/functions/.env}}"
if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="$DEFAULT_ROOT/$ENV_FILE"
fi

if [[ ! "$SCORE" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "Usage: $0 <score 0-100> [env-file]" >&2
  exit 2
fi

if ! awk "BEGIN { exit !($SCORE >= 0 && $SCORE <= 100) }"; then
  echo "Score must be between 0 and 100." >&2
  exit 2
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

BACKUP_FILE="${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
cp -p "$ENV_FILE" "$BACKUP_FILE"

if grep -q '^MESUGAK_BUY_SCORE_MIN=' "$ENV_FILE"; then
  sed -i -E "s/^MESUGAK_BUY_SCORE_MIN=.*/MESUGAK_BUY_SCORE_MIN=$SCORE/" "$ENV_FILE"
else
  printf '\n# Minimum live-adjusted score required for a new paper-trading BUY.\nMESUGAK_BUY_SCORE_MIN=%s\n' "$SCORE" >> "$ENV_FILE"
fi

echo "Updated MESUGAK_BUY_SCORE_MIN=$SCORE"
echo "Backup: $BACKUP_FILE"
grep '^MESUGAK_BUY_SCORE_MIN=' "$ENV_FILE"
echo "Restart an active school_paper_trader.py --loop --execute process before relying on the new value."
