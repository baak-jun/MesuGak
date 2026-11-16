"""Private full-universe scoring, cache-first resume, and after-close warming."""
import argparse
import hashlib
import json
import sys
import time as clock
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
FUNCTIONS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(FUNCTIONS), str(FUNCTIONS/'jobs')]
from school_paper_trader import load_server_env
from strategy_engine.kis_paper import KISPaperClient, KISPaperConfig
from strategy_engine.contest_market_data import SOURCE, atomic_json, load_kis_candles, load_cached_score_history
from strategy_engine.market_data import load_market_universe, MarketTarget, PublicDataClient
import os
from strategy_engine.analysis import analyze_stock, to_summary, StockIdentity
from strategy_engine.realtime_scoring import valid_history, InsufficientHistoryError
from contest_notifications import clean_detail
from strategy_engine.untradable import load_untradable_codes
from strategy_engine.order_state import OrderStateStore
KST = ZoneInfo('Asia/Seoul')


def next_weekday(day):
    day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def cache_digest(root, code):
    try:
        return hashlib.sha256((root/'runtime/kis-history'/f'KR_{code}.json.gz').read_bytes()).hexdigest()
    except OSError:
        return None


def scoring_revision():
    return hashlib.sha256(b''.join((FUNCTIONS/'strategy_engine'/name).read_bytes()
        for name in ['analysis.py','scoring.py','indicators.py','risk.py'])).hexdigest()


def reusable_prepared(root, payload, session_day, codes):
    if payload.get('sessionDate') != session_day.isoformat() or payload.get('scoringRevision') != scoring_revision():
        return {}
    return {r['code']:dict(r) for r in payload.get('summaries', [])
            if r.get('code') in codes and r.get('historyDigest')
            and r['historyDigest'] == cache_digest(root,r['code'])}


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def contest_universe(root, day):
    """Persist identities separately from prices; outage fallback never invents scores."""
    cache_path = root/'runtime/checkpoints/contest-universe-KR.json'
    cache = read_json(cache_path)
    def decode(payload):
        return [MarketTarget(str(r['code']), str(r.get('name') or r['code']), float(r.get('marcap') or 0))
                for r in payload.get('summaries', []) if isinstance(r, dict) and r.get('code')]
    if cache.get('runDate') == day.isoformat() and decode(cache):
        return decode(cache), {'source':'same_day_cache','asOf':cache['runDate']}
    try:
        client = PublicDataClient(os.getenv('DATA_GO_KR_SERVICE_KEY') or os.getenv('PUBLIC_DATA_SERVICE_KEY') or '', timeout=5, retries=0)
        rows = load_market_universe('KR', client=client)
        atomic_json(cache_path, {'runDate':day.isoformat(), 'summaries':[{'code':r.code,'name':r.name,'marcap':r.marcap} for r in rows]})
        return rows, {'source':'public_api','asOf':day.isoformat()}
    except Exception as exc:
        for payload in [cache, read_json(root/'runtime/checkpoints/contest_candidates_KR.json')]:
            rows = decode(payload)
            stamp = payload.get('runDate', '')
            try:
                age = (day-datetime.fromisoformat(stamp).date()).days
            except (ValueError, TypeError):
                continue
            if rows and 0 <= age <= 7:
                return rows, {'source':'outage_cache','asOf':stamp,'errorType':type(exc).__name__}
        raise RuntimeError('Universe unavailable and no valid local snapshot within 7 days') from exc


def run(args):
    now = datetime.now(KST)
    day = now.date()
    root = Path(args.root).resolve()
    warm = bool(getattr(args, 'warm_only', False))
    score_day = next_weekday(day) if warm else day
    if warm and now.time() < time(15, 40):
        raise ValueError('Completed-session history warming starts after 15:40')
    path = root/'runtime/checkpoints/contest_candidates_KR.json'
    state_path = root/'runtime'/('contest-history-warm.json' if warm else 'contest-kis-scan.json')
    state = read_json(state_path)
    previous = read_json(path)
    excluded_path = root/'runtime/checkpoints/untradable_KR.json'
    excluded = load_untradable_codes(excluded_path)
    try:
        universe, universe_status = contest_universe(root, day)
    except Exception as exc:
        atomic_json(state_path, {'runDate':day.isoformat(), 'status':'failed', 'stage':'universe',
                                'updatedAt':now.isoformat(), 'errorType':type(exc).__name__})
        raise
    targets = [r for r in universe if r.code not in excluded]
    target_codes = {r.code for r in targets}
    prepared_path = root/'runtime/checkpoints/contest-prepared-KR.json'
    prepared = reusable_prepared(root, read_json(prepared_path), score_day, target_codes)
    if state.get('runDate') != day.isoformat():
        if state.get('runDate'):
            atomic_json(root/'runtime/scan-audit'/f"{state_path.stem}-{state['runDate']}.json", state)
        state = {'runDate':day.isoformat(), 'startedAt':now.isoformat(), 'failedCodes':[], 'completedCodes':[], 'cacheHitCount':0, 'restCount':0}
    summaries = {r['code']:r for r in previous.get('summaries', [])
                 if r.get('kisCheckedSession') == day.isoformat() and r.get('scoreBasis') == 'completed_daily_candles' and r['code'] in target_codes}
    if warm:
        summaries = prepared
    else:
        for code,row in prepared.items():
            summaries.setdefault(code, row)
    complete = set(summaries)
    state['preparedReuseCount'] = len(prepared)
    state['universeStatus'] = universe_status
    failures = {r['code']:r for r in state.get('failedCodes', []) if r['code'] in target_codes and r['code'] not in complete}
    state.update(status='running', totalCount=len(targets), resumedAt=now.isoformat())
    with OrderStateStore(root/'runtime/realtime_order_state.sqlite3') as store:
        watched = set((store.get_runtime('heartbeat') or {}).get('watchCodes', []))
    targets.sort(key=lambda r:(r.code in failures, r.code not in watched, -r.marcap, r.code))
    deadline = datetime.combine(day, time.fromisoformat(args.until), tzinfo=KST)
    client = KISPaperClient(KISPaperConfig.from_env())
    last_save = 0.0

    def save():
        nonlocal last_save
        excluded_now = load_untradable_codes(excluded_path)
        selected_targets = [r for r in targets if r.code not in excluded_now]
        active_codes = {r.code for r in selected_targets}
        ok = complete & active_codes
        failed = {c:r for c,r in failures.items() if c in active_codes and c not in ok}
        remaining = active_codes - ok - set(failed)
        state.update(totalCount=len(active_codes), successCount=len(ok), remainingCount=len(remaining),
                     failedCodes=list(failed.values()), updatedAt=datetime.now(KST).isoformat(timespec='seconds'),
                     requestIntervalSeconds=client.request_interval,
                     dataUnavailableCount=sum(r.get('category') == 'insufficient_history' for r in failed.values()),
                     errorCount=sum(r.get('category') != 'insufficient_history' for r in failed.values()),
                     completionPct=round(len(ok)/max(1,len(active_codes))*100,2))
        if warm:
            state['completedCodes'] = sorted(ok)
            atomic_json(prepared_path, {'sessionDate':score_day.isoformat(), 'preparedFromDate':day.isoformat(),
                'scoringRevision':scoring_revision(), 'updatedAt':state['updatedAt'],
                'successCount':len(ok), 'failureCount':len(failed), 'pendingCount':len(remaining),
                'summaries':[summaries[c] for c in summaries if c in ok]})
        else:
            selected = [summaries[c] for c in summaries if c in ok]
            pending = [{'code':r.code,'name':r.name,'marcap':r.marcap,'confidenceScore':None,
                        'scorePending':r.code in remaining, 'scoreUnavailable':r.code in failed,
                        'scoreUnavailableReason':failed.get(r.code,{}).get('category')}
                       for r in selected_targets if r.code not in ok]
            atomic_json(path, {'market':'KR','runDate':day.isoformat(),'source':SOURCE,'scanStatus':state['status'],
                              'targetCount':len(active_codes),'successCount':len(ok),'pendingCount':len(remaining),
                              'failureCount':len(failed),'updatedAt':state['updatedAt'],'summaries':selected+pending})
        atomic_json(state_path, state)
        atomic_json(root/'runtime/scan-audit'/f'{state_path.stem}-{day.isoformat()}.json', state)
        last_save = clock.monotonic()

    def score(row, frame):
        frame = valid_history(frame.to_dict('records'), score_day)
        payload = analyze_stock(frame, StockIdentity('KR',row.code,row.name,row.marcap))
        if not payload:
            raise ValueError('insufficient valid KIS candles')
        summaries[row.code] = {**to_summary(payload), 'scoreSource':SOURCE,'kisCheckedSession':score_day.isoformat(),
                              'scoreBasis':'completed_daily_candles', 'scoreCheckedAt':datetime.now(KST).isoformat(timespec='seconds')}
        if warm:
            summaries[row.code].update(historyDigest=cache_digest(root,row.code), preparedFromDate=day.isoformat())
        complete.add(row.code)
        failures.pop(row.code, None)

    save()
    missing = []
    # Visit every disk cache before spending any time in slow REST requests.
    for row in targets:
        if row.code in complete:
            continue
        failure = failures.get(row.code, {})
        if failure.get('category') == 'insufficient_history' and failure.get('retryAfterDate', '') > day.isoformat():
            continue
        if not warm:
            try:
                score(row, load_cached_score_history(root/'runtime/kis-history',row.code,day))
                state['cacheHitCount'] = state.get('cacheHitCount',0)+1
                if clock.monotonic()-last_save >= 15: save()
                continue
            except (OSError, ValueError, EOFError, TypeError, KeyError):
                pass
        missing.append(row)
    save()
    for row in missing:
        if datetime.now(KST) >= deadline:
            state.update(status='interrupted', interruptionReason='deadline', deadline=deadline.isoformat())
            break
        if row.code in load_untradable_codes(excluded_path):
            continue
        started = clock.monotonic()
        state['lastCode'] = row.code
        try:
            frame = load_kis_candles(client, root/'runtime/kis-history', row.code, day, refresh=warm)
            state['historyLoadCount'] = state.get('historyLoadCount',0)+1
            score(row,frame)
        except Exception as exc:
            failures[row.code] = {'code':row.code,'reason':type(exc).__name__, 'detail':clean_detail(exc),
                                 'category':'insufficient_history' if isinstance(exc,InsufficientHistoryError) else 'error',
                                 'checkedAt':datetime.now(KST).isoformat(timespec='seconds')}
            if isinstance(exc,InsufficientHistoryError):
                failures[row.code].update(availableCandles=exc.available, requiredCandles=exc.required,
                                         retryAfterDate=(day+timedelta(days=1)).isoformat())
        state['lastCodeSeconds'] = round(clock.monotonic()-started,3)
        if clock.monotonic()-last_save >= 15: save()
    else:
        state.update(status='done_with_errors' if failures else 'done',finishedAt=datetime.now(KST).isoformat(timespec='seconds'))
    save()
    print(json.dumps({k:state.get(k) for k in ['runDate','status','totalCount','successCount','remainingCount','cacheHitCount','preparedReuseCount','historyLoadCount']},ensure_ascii=False),flush=True)
    return state


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(FUNCTIONS.parent))
    parser.add_argument('--env-file',default='functions/.env.contest')
    parser.add_argument('--until',default='08:50')
    parser.add_argument('--warm-only',action='store_true')
    args=parser.parse_args()
    load_server_env(args.env_file)
    run(args)
