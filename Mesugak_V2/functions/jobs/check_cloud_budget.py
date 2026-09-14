"""Reserve one bounded cron attempt, or stop before Firestore I/O."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strategy_engine.cost_control import check_cloud_budget, scheduler_guard

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['analysis', 'refresh'], required=True)
    parser.add_argument('--reserve', action='store_true', help='Consume the local daily allowance after the check')
    args = parser.parse_args()
    try:
        print(scheduler_guard(args.kind) if args.reserve else check_cloud_budget())
    except Exception as exc:
        print(f'[COST_BLOCKED] {exc}', file=sys.stderr)
        sys.exit(3)
