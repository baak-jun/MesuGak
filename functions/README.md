# Functions Guide

`functions` 디렉터리의 현재 운영 대상은 아래 2개입니다.

- `index.js`: Cloud Functions 엔트리
- `end_of_day_buy_signals.js`: 평일 15:40(KST) 장마감 갱신 함수

과거 Python 기반 파일은 `functions/legacy`로 이동되어 보관됩니다.

## 배포 대상 함수

- 이름: `refreshPendingOrdersFromBuySignals`
- 리전: `us-central1`
- 트리거: Scheduler (cron: `40 15 * * 1-5`, `Asia/Seoul`)
- 동작:
  - 입력: `stock_analysis` 컬렉션 (`type=buy_signal`, `market=BOT_MARKET`)
  - 출력: `pending_orders/{MARKET}_{CODE}` upsert

## 환경변수

`functions/.env` 예시:

```env
BOT_MARKET=KR
```

## 배포 명령

```bash
cd functions
npm install
cd ..
firebase deploy --only functions:refreshPendingOrdersFromBuySignals
```

## 로컬 비상 실행 (Python)

함수 장애 시 같은 로직을 로컬에서 실행:

```bash
.venv\Scripts\python functions/local_refresh_pending_orders.py --dry-run
.venv\Scripts\python functions/local_refresh_pending_orders.py
```
