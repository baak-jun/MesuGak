# 학교 서버 이관 목록

로컬에서 검증된 V2 국내 분석과 Gmail 감시를 학교 서버에 반영할 때의
파일 배치입니다. 기준 서버 루트는 `~/mesugak/v2`입니다.

## 1. 서버로 복사할 폴더

가장 안전한 방법은 `functions/` 폴더 전체를 복사하는 것입니다. 내부 모듈의
import 관계와 Firebase 저장소 코드를 빠뜨리지 않습니다.

```text
Mesugak_V2/functions/                 -> ~/mesugak/v2/functions/
```

다만 아래 파일은 로컬에서 복사하지 않습니다.

```text
functions/.env                         서버의 기존 파일 유지
functions/venv/                         서버 가상환경 유지
functions/__pycache__/                  복사 불필요
functions/.checkpoints/                서버 체크포인트 유지
```

폴더 전체 복사가 어려우면 최소한 다음 파일을 맞춰 복사해야 합니다.

```text
functions/jobs/analyze_market.py
functions/jobs/publish_public_analysis.py
functions/jobs/publish_private_performance.py
functions/jobs/monitor_school_server.py
functions/strategy_engine/analysis.py
functions/strategy_engine/checkpoints.py
functions/strategy_engine/indicators.py
functions/strategy_engine/market_data.py
functions/strategy_engine/orders.py
functions/strategy_engine/portfolio.py
functions/strategy_engine/performance.py
functions/strategy_engine/repositories.py
functions/strategy_engine/risk.py
functions/strategy_engine/scoring.py
functions/requirements.txt
```

`functions/requirements.txt`에는 공공데이터·Firestore 실행에 필요한 패키지가
있습니다. 서버의 기존 가상환경에서 다시 설치합니다.

## 2. 서버 루트에 복사할 실행 파일

`server_runtime` 안의 파일은 서버 루트로 복사해야 현재 cron 경로와 맞습니다.

```text
Mesugak_V2/server_runtime/run_v2_kr_close.sh
    -> ~/mesugak/v2/run_v2_kr_close.sh

Mesugak_V2/server_runtime/run_v2_health_monitor.sh
    -> ~/mesugak/v2/run_v2_health_monitor.sh
```

이번 국내 전용 운영에는 US 실행 파일이 없습니다.
기존에 등록된 US cron이 있다면 삭제하거나 주석 처리해야 합니다.

## 3. 복사하지 말아야 할 비밀·운영 상태

- 로컬 `functions/.env`를 덮어쓰지 않습니다. 서버의 `.env`를 사용합니다.
- KIS 앱 키·시크릿·계좌번호는 서버에 이미 있는 관리자 전용 설정만 유지합니다.
- Firebase 서비스 계정 JSON은 서버의 기존 보호 파일을 유지합니다.
- `runtime/checkpoints/`, `runtime/health/`, `runtime/cron/`은 서버 상태이므로
  로컬에서 덮어쓰지 않습니다.

서버 `.env`에는 다음 값이 있어야 합니다.

```dotenv
DATA_GO_KR_SERVICE_KEY=원본_Decoding_인증키
MESUGAK_GMAIL_USER=발신용_Gmail
MESUGAK_GMAIL_APP_PASSWORD=Gmail_앱_비밀번호
MESUGAK_ALERT_EMAIL_TO=수신용_이메일
```

## 4. 서버에서 실행할 명령

```bash
cd ~/mesugak/v2
chmod 755 run_v2_kr_close.sh run_v2_health_monitor.sh
chmod 600 functions/.env
venv/bin/pip install -r functions/requirements.txt
```

먼저 실제 메일을 한 통 보내고, 소규모 분석을 수행합니다.

```bash
venv/bin/python functions/jobs/monitor_school_server.py --send-test --market KR --root "$PWD"
venv/bin/python functions/jobs/analyze_market.py --market KR --codes 005930 --dry-run --progress-interval 1
```

두 명령이 각각 `test_email_sent`, `failureCount: 0`을 출력하면 cron을
등록합니다.

## 5. 권장 cron

```cron
10 16 * * 1-5 /usr/bin/flock -n /tmp/mesugak-v2-kr.lock /home/2023112374/mesugak/v2/run_v2_kr_close.sh
*/30 * * * * /usr/bin/flock -n /tmp/mesugak-v2-health.lock /home/2023112374/mesugak/v2/run_v2_health_monitor.sh || true
```

`run_v2_kr_close.sh`는 분석·공개 게시가 모두 끝난 뒤 성공 시각을 기록하고,
중간 오류가 나면 즉시 Gmail을 보냅니다. 별도 감시 cron은 체크포인트가 90분
이상 멈추거나 평일 공개 게시가 누락된 경우 알립니다.

## 6. 현재 확인되지 않은 항목

주식시세 API는 로컬에서 실제 호출과 분석까지 확인했습니다. 지수시세 API는
현재 키로 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`가 반환되어, 공공데이터포털에서
`금융위원회_지수시세정보` 활용신청을 별도로 승인받은 뒤 서버에서 다시 확인해야
합니다. 지수 API가 당장 없어도 개별 종목 기술적 분석과 공개 게시 자체는
주식시세 API로 실행할 수 있습니다.
