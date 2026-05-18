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

## Oracle Free Tier 실행

오라클 프리티어(Ubuntu)에서는 `local_chart_refresh.py` 대신 전용 래퍼 `oracle_chart_refresh.py` 실행을 권장합니다.

### 1. Python 가상환경/의존성

```bash
cd ~/MesuGak/functions
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.oracle.txt
```

### 2. 환경 파일

예시: `functions/.env.oracle`

```env
BOT_KR_MARKETS=KOSPI,KOSDAQ
BOT_MAX_STOCKS_KR=0
BOT_MAX_STOCKS_US=800
BOT_FIREBASE_CRED_PATH=/home/ubuntu/mesugak-secrets/serviceAccountKey.json
BOT_CHECKPOINT_DIR=/home/ubuntu/mesugak-runtime/checkpoints
BOT_LOG_DIR=/home/ubuntu/mesugak-runtime/logs
BOT_LOCK_FILE=/home/ubuntu/mesugak-runtime/oracle_chart_refresh.lock
BOT_SKIP_PENDING_ORDERS=false
```

### 3. 수동 실행

```bash
cd ~/MesuGak/functions
source .venv/bin/activate
python oracle_chart_refresh.py --env-file .env.oracle
```

### 4. cron 예시

한국장과 미국장을 분리해서 실행하는 것을 권장합니다.

- 한국장: `--market KR`
- 미국장: `--market US`

주의:

- `TZ=Asia/Seoul` 기준 미국 정규장은 한국시간 다음날 새벽에 끝납니다.
- 따라서 미국장 cron 요일은 `2-6`(화-토)로 잡아야 월-금 미국장 마감과 맞습니다.
- 미국장은 서머타임 영향을 받으므로 "정확히 마감 직후"를 원하면 계절에 따라 시간을 바꿔야 합니다.
- 운영 단순성을 우선하면 한국시간 `06:10` 실행처럼 여유를 둔 고정 시각이 안전합니다.

예시:

```bash
crontab -e
```

```cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TZ=Asia/Seoul

10 16 * * 1-5 cd /home/ubuntu/MesuGak/functions && /home/ubuntu/MesuGak/functions/.venv/bin/python oracle_chart_refresh.py --env-file /home/ubuntu/MesuGak/functions/.env.oracle --market KR >> /home/ubuntu/mesugak-runtime/logs/cron.log 2>&1
10 6 * * 2-6 cd /home/ubuntu/MesuGak/functions && /home/ubuntu/MesuGak/functions/.venv/bin/python oracle_chart_refresh.py --env-file /home/ubuntu/MesuGak/functions/.env.oracle --market US >> /home/ubuntu/mesugak-runtime/logs/cron.log 2>&1
```

### 5. 래퍼가 추가로 처리하는 것

- 단일 실행 락 파일: 중복 실행 방지
- 실행 로그 파일 저장
- OCI 런타임 경로 기준 체크포인트/로그 디렉터리 분리
- 기존 `run_chart_refresh()` / `pending_orders` 후처리 재사용
