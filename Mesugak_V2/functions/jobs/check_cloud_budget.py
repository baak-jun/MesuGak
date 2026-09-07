"""Reserve one bounded cron attempt, or stop before Firestore I/O."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strategy_engine.cost_control import scheduler_guard

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['analysis', 'refresh'], required=True)
    args = parser.parse_args()
    try:
        print(scheduler_guard(args.kind))
    except Exception as exc:
        print(f'[COST_BLOCKED] {exc}', file=sys.stderr)
        sys.exit(3)
