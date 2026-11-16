"""Pure health checks; counts and event times, never a running PID alone."""
from datetime import datetime, time


def epoch(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (ValueError, TypeError):
        return 0.0


def assess_contest_health(scan, heartbeat, now):
    checks, issues = [], {}
    if now.weekday() >= 5:
        return checks, issues
    day = now.date().isoformat()
    if now.time() >= time(8, 50):
        checks += ['scan_incomplete', 'scan_failures']
        if scan.get('runDate') != day:
            issues['scan_incomplete'] = '오늘 전체 검사 기록이 없습니다.'
        elif scan.get('remainingCount', 0) or scan.get('status') == 'failed' or (scan.get('status') == 'running' and now.timestamp()-epoch(scan.get('updatedAt')) > 300):
            issues['scan_incomplete'] = f"전체 검사 {scan.get('status')}: 성공 {scan.get('successCount',0)}/{scan.get('totalCount',0)}, 미처리 {scan.get('remainingCount',0)}, 마지막 갱신 {scan.get('updatedAt')}"
        unavailable = scan.get('failedCodes', [])
        failures = [r for r in unavailable if r.get('category') != 'insufficient_history']
        if scan.get('runDate') == day and len(unavailable) > 100:
            sample = '; '.join(f"{r.get('code')}: {r.get('detail') or r.get('reason')}" for r in failures[:3])
            issues['scan_failures'] = f"계산 불가 {len(unavailable)}종목으로 알림 기준 100개를 초과했습니다. 일봉 부족 {len(unavailable)-len(failures)}개, 조회·계산 오류 {len(failures)}개. {sample}"
    if time(9, 3) <= now.time() < time(15, 35):
        checks += ['heartbeat_stale','quote_stale','held_quote_stale','quote_idle','score_stale','history_missing','volume_rank_stale']
        if heartbeat.get('sessionDate') != day or now.timestamp()-epoch(heartbeat.get('checkedAt')) > 120:
            issues['heartbeat_stale'] = f"실시간 실행 상태가 120초 이상 갱신되지 않았습니다: {heartbeat.get('checkedAt')}"
        watch = heartbeat.get('watchCodes', [])
        starts = heartbeat.get('watchStartedAt', {})
        matured = [c for c in watch if now.timestamp()-epoch(starts.get(c, 0)) > 180]
        ticks = heartbeat.get('lastTicks', {})
        scores = heartbeat.get('scoreObservedAt', {})
        stale = [c for c in matured if now.timestamp()-epoch(ticks.get(c)) > 120]
        if matured and len(stale) == len(matured) and not any(now.timestamp()-epoch(ticks.get(c)) <= 120 for c in watch):
            issues['quote_stale'] = '준비가 끝난 감시 종목 전체에서 2분 이상 체결 시세가 없습니다. 연결·구독 상태를 확인해야 합니다.'
        held_stale = set(stale) & set(heartbeat.get('heldCodes', []))
        if held_stale:
            issues['held_quote_stale'] = '보유 종목 체결 시세가 2분 이상 없습니다. 청산 판단 지연 가능: ' + ', '.join(sorted(held_stale))
        idle = [c for c in matured if c not in heartbeat.get('heldCodes', []) and now.timestamp()-epoch(ticks.get(c)) > 300]
        if idle and 'quote_stale' not in issues:
            issues['quote_idle'] = '일부 비보유 종목에 5분 이상 체결이 없습니다. 거래 공백·거래정지·구독 문제를 구분해야 하며 전체 수신 장애를 뜻하지 않습니다: ' + ', '.join(idle)
        short_history = {c for c, error in heartbeat.get('scoreHistoryErrors', {}).items() if 'InsufficientHistoryError' in str(error)}
        bad_score = [c for c in matured if c not in short_history and now.timestamp()-epoch(ticks.get(c)) <= 30 and now.timestamp()-max(epoch(scores.get(c)), epoch(starts.get(c))) >= 1200 and c not in heartbeat.get('heldCodes', [])]
        if bad_score:
            issues['score_stale'] = '시세는 들어오지만 점수가 20분 이상 갱신되지 않는 종목: ' + ', '.join(bad_score)
        missing = (set(heartbeat.get('watchHistoryMissingCodes', [])) & set(matured)) - short_history
        if missing:
            issues['history_missing'] = '과거 일봉 준비 지연: ' + ', '.join(sorted(missing))
        if heartbeat.get('watchMode') == 'volume' and now.timestamp()-epoch(heartbeat.get('volumeRankObservedAt')) > 180:
            issues['volume_rank_stale'] = '거래량 순위가 3분 이상 갱신되지 않았습니다.'
    return checks, issues
