"""Cron watchdog independent of the quote loop, including process stalls."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
FUNCTIONS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(FUNCTIONS), str(FUNCTIONS/'jobs')]
from strategy_engine.order_state import OrderStateStore
from strategy_engine.contest_health import assess_contest_health
from contest_notifications import ContestNotifications
from school_paper_trader import load_server_env


def check(root, now):
    try:
        scan = json.loads((root/'runtime/contest-kis-scan.json').read_text())
    except (OSError, ValueError):
        scan = {}
    with OrderStateStore(root/'runtime/realtime_order_state.sqlite3') as store:
        h = store.get_runtime('heartbeat') or {}
        checks, issues = assess_contest_health(scan, h, now)
        notifications = ContestNotifications(store, enabled=os.getenv('MESUGAK_CONTEST_EMAIL_ENABLED','false').lower() == 'true')
        # Debounce non-held single-symbol idle warnings only; held/feed outages remain immediate.
        if 'quote_idle' in checks:
            previous = store.get_runtime('quote_idle_debounce') or {}
            if previous.get('day') != now.date().isoformat():
                previous = {}
            detail = issues.get('quote_idle')
            hits = int(previous.get('hits',0))+1 if detail else 0
            clears = 0 if detail else int(previous.get('clears',0))+1
            active = detail if hits >= 2 else previous.get('active')
            if clears >= 2:
                active = None
            store.set_runtime('quote_idle_debounce', {'day':now.date().isoformat(),'hits':hits,'clears':clears,'active':active})
            issues.pop('quote_idle',None)
            if active:
                issues['quote_idle'] = active
        for key in checks:
            if key == 'score_stale':
                # Do not emit recovery for an incident opened under the old 30s policy.
                policy = store.get_runtime('score_stale_email_policy') or {}
                if policy.get('delaySeconds') != 1200:
                    previous = store.get_runtime('contest_health:'+key) or {}
                    store.set_runtime('contest_health:'+key, {**previous,'active':False,'detail':''})
                    store.set_runtime('score_stale_email_policy', {'delaySeconds':1200})
            # Queue policy silently closes scan_failures below the threshold,
            # while resetting the incident so a future outage can notify again.
            notifications.health(key, issues.get(key), now=now)
        store.set_runtime('health_check', {'checkedAt':now.isoformat(), 'issues':issues, 'checks':checks,
                          'calculationUnavailableCount':len(scan.get('failedCodes',[])), 'calculationEmailThreshold':100})
        sent = asyncio.run(notifications.deliver())
    return {'checkedAt':now.isoformat(), 'issues':issues, 'sent':sent}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root', default=str(FUNCTIONS.parent))
    parser.add_argument('--env-file', default='functions/.env.contest')
    args=parser.parse_args()
    load_server_env(args.env_file)
    print(json.dumps(check(Path(args.root).resolve(), datetime.now(ZoneInfo('Asia/Seoul'))),ensure_ascii=False))
