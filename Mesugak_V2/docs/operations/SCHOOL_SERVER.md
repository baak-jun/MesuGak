# 학교 서버 접속·파일 구조·운영

확인: 2026-10-15 22:36 KST. 이 문서는 계정 `YOUR_SCHOOL_ID`의 MesuGak 범위다. 공용 학교 서버 전체의 다른 사용자 서비스나 관리자 전용 설정은 조사하지 않았다.

## 1. 접속

| 항목 | 실제 값 |
|---|---|
| 호스트 | `YOUR_SCHOOL_HOST` |
| SSH 포트 | **102** |
| 사용자 | `YOUR_SCHOOL_ID` |
| 접속 후 호스트 이름 | `school-server-2` |
| 프로젝트 루트 | `/home/YOUR_SCHOOL_ID/mesugak/repo/Mesugak_V2` |
| Python | `/home/YOUR_SCHOOL_ID/micromamba-root/envs/py312/bin/python` |
| 서버 시각 | KST, `+09:00` 관측 |

이 PC의 PowerShell에서 접속:

```powershell
ssh -o StrictHostKeyChecking=yes -o UserKnownHostsFile=C:/Users/local-user/.ssh/known_hosts -o IdentitiesOnly=yes -i C:/Users/local-user/.ssh/id_ed25519_mesugak_school -p 102 YOUR_SCHOOL_ID@YOUR_SCHOOL_HOST
```

자동 조회 때는 `-o BatchMode=yes -o ConnectTimeout=15`도 사용한다. 개인키는 현재 PC의 SSH agent 또는 올바른 패스프레이즈로 사용할 수 있어야 한다. 복사본에는 개인키·패스프레이즈가 없다. 다른 PC에서는 본인에게 승인된 키를 설치하고 서버 호스트 키를 별도로 확인해야 하며, `StrictHostKeyChecking=no`로 우회하지 않는다.

원격 파일 하나를 지정해서 가져오는 예:

```powershell
scp -o StrictHostKeyChecking=yes -o UserKnownHostsFile=C:/Users/local-user/.ssh/known_hosts -o IdentitiesOnly=yes -i C:/Users/local-user/.ssh/id_ed25519_mesugak_school -P 102 YOUR_SCHOOL_ID@YOUR_SCHOOL_HOST:/home/YOUR_SCHOOL_ID/mesugak/repo/Mesugak_V2/server_runtime/run_kis_realtime_trader.sh ./run_kis_realtime_trader.server.sh
```

SSH는 소문자 `-p`, SCP는 대문자 `-P`다. 접속 직후 기준 경로를 확인한다.

```bash
hostname
date -Is
cd /home/YOUR_SCHOOL_ID/mesugak/repo/Mesugak_V2
pwd
/home/YOUR_SCHOOL_ID/micromamba-root/envs/py312/bin/python --version
```

예전 문서의 `~/mesugak/v2`와 `venv/bin/python`을 현재 경로로 가정하지 않는다.

## 2. 디렉터리 구조

```text
/home/YOUR_SCHOOL_ID/
├── micromamba-root/envs/py312/bin/python     실제 Python 3.12.13
└── mesugak/
    ├── repo/
    │   └── Mesugak_V2/                     실제 작업 루트
    │       ├── .env.server                 경로·Python·공통 환경 설정
    │       ├── .firebaserc                 Firebase 프로젝트/Hosting target
    │       ├── firebase.json               학교 서버에 남은 배포 설정
    │       ├── firestore.rules             학교 서버에 남은 규칙 소스
    │       ├── firestore.indexes.json
    │       ├── functions/
    │       │   ├── .env                    공개 분석·사이트용 KIS·Gmail
    │       │   ├── .env.contest            대회 전용 KIS·매매 설정
    │       │   ├── main.py                 V2 서버 실행 경계를 설명하는 stub
    │       │   ├── jobs/                   작업별 진입점
    │       │   ├── strategy_engine/        공용 계산·정책·외부 API·저장소
    │       │   ├── tests/
    │       │   └── requirements.txt
    │       ├── server_runtime/             cron이 호출하는 shell wrapper
    │       ├── frontend/                   서버에 남은 프론트 소스, 최신 Hosting과 다름
    │       ├── docs/                       배포 당시 문서
    │       └── runtime/                    상태·캐시·원장·보고서·로그
    ├── backups/                            날짜별 배포 전 코드·설정·원장 백업
    ├── staging/                            배포 준비 파일, 현재 실행 루트가 아님
    ├── logs/                               구형 paper 로그
    ├── venv/                               구형 Python 환경, 현재 기본 아님
    ├── legacy/                             구형 구현
    ├── .env / kis-paper.env                 구형 설정, 현재 대회 설정과 혼동 금지
    ├── serviceAccountKey.json              Firebase Admin 인증, 복사 제외
    └── local_*.py / oracle_chart_refresh.py 구형 실행 파일, 현재 크론 연결 없음
```

루트의 `repo`는 저장소 배치 위치다. `backups`, `staging`, `legacy`, 과거 수동 PID 파일이 존재한다는 것만으로 현재 실행 중인 것은 아니다. 전체 개별 경로는 [스냅샷 설명](SNAPSHOT.md)의 inventory를 본다.

### 현재 runtime의 핵심 파일

| 경로 (`runtime/` 아래) | 용도 | 복구·점검 시 주의 |
|---|---|---|
| `realtime_order_state.sqlite3` | 대회 주문·전략 상태·heartbeat·메일 outbox | 핵심 원장. 삭제·빈 파일 교체 금지 |
| `kis_request_rate.sqlite3` | 대회 프로세스 간 KIS 요청 간격 | 주문 우선권·차트 요청 조절 |
| `contest-kis-scan.json` | 일일 KIS 전체 검사 진행률·실패 목록 | 완료 여부는 `status`와 실패 목록을 같이 판단 |
| `checkpoints/contest_candidates_KR.json` | 대회 KIS 전체 검사 점수·미평가 메타데이터 | 현재 대회 후보 입력 |
| `checkpoints/realtime_candidates_KR.json` | 공공데이터 전체 분석 요약 | 이름에 realtime이 있어도 현재 대회 입력 아님 |
| `checkpoints/untradable_KR.json` | 분석·감시 공통 거래 불가 목록 | 수동 삭제하면 제외 종목 재유입 가능 |
| `kis-history/KR_종목코드.json.gz` | KIS 전용 일봉 캐시 | 출처 태그·세션 확인 |
| `realtime-history/` | 과거 공공데이터 기반 실시간 보조 이력 | 새 KIS 점수 캐시와 구분 |
| `checkpoints/analyze_market_KR.json` | 공개 분석 checkpoint | 큰 파일. 원문 전체 출력 불필요 |
| `checkpoints/analysis_keep_KR.json` | 상위 200개 선정 결과 | 점수↓·시총↓·코드↑ 순 |
| `local-analysis/KR/` | 공개 분석의 선택된 상세 gzip | 성공 후 미선택 로컬 결과 정리 |
| `watch/public_data_KR.json` | 공공 API 발견일·처리일·재시도 | 매수 감시 상태 파일이 아님 |
| `reports/daily_YYYY-MM-DD.json` | 정상 마감 계좌 보고서 | 계좌 정보 포함, 공개 업로드 금지 |
| `reports/*-preview.json`, `*-error.json` | 미발송 미리보기·실패 보고 | 정상 마감 성공 기록과 구분 |
| `health/last_success_KR.json` | 공개 분석 마지막 성공 | 대회 매매 heartbeat와 다름 |
| `health/alert_state_KR.json` | 공개 분석 알림 중복·쿨다운 | 대회 outbox와 별도 |
| `cost/budget.sqlite3`, `cost/status.json` | 로컬 일일 실행 횟수·클라우드 제한 상태 | 검사 재실행하려고 임의 초기화 금지 |
| `cost/analysis-retention.json` | 공개 분석 정리 결과 | 이번 결과는 200개 유지 |
| `cloud-archives/` | 예전 후보·분석 정리 전 보존본 | 원장·거래 기록과 다른 보관 영역 |
| `cron/`, `logs/` | 예약·수동 실행 로그 | 로그 회전 뒤 `.gz` 확인 |
| `kis/token.json` | 구형/관련 KIS 인증 캐시 | 인증값. 복사본에서 제외 |
| `analysis.lock`, `maintenance.lock`, `contest_*.lock` | 중복 실행 잠금 대상 | 파일 존재만으로 잠금 보유 여부 판단 불가 |

SQLite `orders`에는 신호 ID·주문일·코드·방향·수량·상태·증권사 주문번호·누적 체결량·평균 체결가가 있다. `runtime_state`에는 `heartbeat`, `strategy`, 대회 알림 상태, 증권사 제외 목록이 있고 `email_outbox`에는 발송 상태가 있다. 스키마·행 수는 증거 파일에, 실제 원장은 서버에 보존했다.

## 3. 환경 설정의 실제 선택 순서

| 작업 | 읽는 환경 |
|---|---|
| 공개 분석·건강 점검·사이트 조회·사이트 매매 | `.env.server` → 지정된 `functions/.env` |
| 대회 실시간 wrapper | `.env.server` → `MESUGAK_CONTEST_ENV_FILE`, 없으면 `.env.contest`, 마지막에 일반 env fallback |
| KIS 검사·마감 보고 wrapper | `.env.server`, job의 `load_server_env(--env-file functions/.env.contest)` |

대회 job의 공통 로더는 일반 환경도 읽어 Gmail/공공데이터 설정을 확보하고 대회 env로 덮어쓴다. 실제 기준은 shell wrapper와 `school_paper_trader.load_server_env`의 조합이다. 단순히 `.env` 하나만 열어 대회 설정이라고 판단하지 않는다.

`MESUGAK_MAX_LIVE_CANDIDATES=20`, 일반 env의 매수 55점 등은 **사이트용 설정**이다. 대회 실시간은 39개 감시·60점 초과·20% 비중을 사용한다. `.env.contest`에 남은 구형 6% trailing 설정이 현재 1.8%/3% 규칙을 덮어쓰는 것도 아니다.

인증 설정은 KIS app key/secret·계좌/HTS ID, 공공 API service key, Gmail 앱 비밀번호, Firebase service account로 나뉜다. 실제 값은 문서에 적지 않았다. 이름·설정 여부와 비민감 운영값만 redacted JSON에 있다.

## 4. 실제 등록된 전체 크론

아래 시간은 서버에서 확인한 **KST**다. `1-5`는 월~금이며 한국 공휴일을 뜻하지 않는다. 대회 실시간 job의 휴장 확인에는 모의 API 특정 실패에 한해 평일 fallback이 있다. 검사·마감 메일은 평일 크론 자체로 공휴일을 완전히 걸러내지 않는다.

| 식 | 작업 | 실제 의미 |
|---|---|---|
| `25 3 * * *` | logrotate | 로그 회전, 상태 `runtime/logrotate.state` |
| `35 3 * * 0` | checkpoint 임시 파일 정리 | 일요일, 하루 넘은 `*.tmp` 삭제 |
| `40 3 * * 0` | 구형 paper 로그 정리 | 일요일, 180일 지난 `~/mesugak/logs/paper*.log`만 |
| `*/3 13-23 * * 1-5` | `run_v2_kr_watch.sh` | 새 공개 데이터 기준일 검사. 매번 전체 분석하는 것은 아님 |
| `*/30 * * * *` | `run_v2_health_monitor.sh` | 공개 분석 상태·정체·실패 점검 및 알림 |
| `*/10 9-16 * * 1-5` | `run_paper_refresh_requests.sh` | 관리자 계좌 조회 요청 처리, 주문 없음 |
| `5 17 * * *` | `run_storage_maintenance.sh` | 후보 정리·분석 압축. 완료 marker면 실제 작업 생략 |
| **주석** `5 9 * * 1-5` | `run_school_paper_trader.sh` | 사이트 자동매매 중단, contest priority 주석 유지 |
| `*/5 9-14 * * 1-5` | `run_kis_realtime_trader.sh --execute` | 장중 대회 프로세스 시작·종료 시 재기동 기회 |
| `0-35/5 15 * * 1-5` | 같은 대회 wrapper | 15시대 재기동 기회, 15:35 이후 job은 `session_closed` |
| `0 5 * * 1-5` | `run_contest_premarket.sh` | KIS 전체 검사 첫 실행 |
| `30 6-8 * * 1-5` | 같은 검사 wrapper | 06:30·07:30·08:30 미완료 재개 |
| `40,45,50,55 15 * * 1-5` | `run_contest_daily_report.sh` | 15:40 마감 요약, 뒤 시간은 미발송·오류 재시도 |
| `*/15 16-17 * * 1-5` | 같은 마감 wrapper | 16~17시 15분마다 재시도, 정상 중복 발송 방지 |

실제 전체 명령은 스냅샷 `evidence/crontab.txt`에 보관했다. 이 표의 정리 작업은 **이미 서버에 있던 크론**이며 이번 문서 작업에서 실행하거나 추가한 것이 아니다.

5분 크론은 5분마다 매매 판단한다는 뜻이 아니다. 대회 프로세스는 한 번 시작하면 WebSocket 이벤트를 계속 받고, 잠금 때문에 다음 크론은 중복 프로세스를 만들지 않는다. 장애 후 외부 재기동 간격은 최대 약 5분이며, 프로세스 내부 재접속은 기본 10초다. 실제 복구 시간에는 API 응답·백오프가 더해진다.

## 5. 잠금·프로세스·로그

| 대상 | 잠금 또는 기록 |
|---|---|
| 공개 데이터 watcher | `/tmp/mesugak-v2-watch.lock` |
| 공개 분석 본체 | `runtime/analysis.lock` |
| 건강 점검 | `/tmp/mesugak-v2-health.lock` |
| 사이트 조회 worker | `/tmp/mesugak-paper-refresh.lock` |
| 사이트 매매(중단) | `/tmp/mesugak-paper-trade.lock` |
| 대회 크론 진입 | `/tmp/mesugak-kis-realtime-cron.lock` |
| 대회 실시간 본체 | `/tmp/mesugak-kis-realtime.lock` |
| 대회 검사 | `runtime/contest_kis_scan.lock` |
| 대회 마감 보고 | `runtime/contest_daily_report.lock` |
| 저장소 관리 | `runtime/maintenance.lock` |

대회 wrapper의 잠금 충돌 종료값 75는 중복 실행 회피다. 0, 75, 130, 143을 제외한 execute 프로세스 종료는 알림 job으로 넘긴다. 일반 공개 분석 오류 알림과 대회 주문·정지 알림은 별도 경로다.

읽기 전용 점검:

```bash
cd /home/YOUR_SCHOOL_ID/mesugak/repo/Mesugak_V2
date -Is
crontab -l
pgrep -af '[k]is_realtime_trader.py'
pgrep -af '[c]ontest_market_scan.py'
pgrep -af '[a]nalyze_market.py'
cat runtime/contest-kis-scan.json
cat runtime/watch/public_data_KR.json
cat runtime/health/last_success_KR.json
tail -n 60 runtime/cron/kis_realtime.log
tail -n 60 runtime/cron/contest_premarket.log
tail -n 40 runtime/cron/contest_daily_report.log
tail -n 40 runtime/cron/v2_kr_close.log
```

대회는 배포 시 수동 시작 로그가 `runtime/logs/kis_*.log`에 남을 수도 있다. `runtime/cron/kis_realtime.log`가 비어 있다는 사실만으로 대회가 작동하지 않았다고 단정하지 않는다. 실시간 상태의 주 근거는 SQLite `runtime_state/heartbeat`다.

SQLite에서 필요한 상태만 읽기:

```bash
/home/YOUR_SCHOOL_ID/micromamba-root/envs/py312/bin/python - <<'PY'
import json, sqlite3
from pathlib import Path
p = Path('runtime/realtime_order_state.sqlite3').resolve()
with sqlite3.connect(p.as_uri()+'?mode=ro', uri=True) as c:
    row = c.execute("SELECT value_json FROM runtime_state WHERE key='heartbeat'").fetchone()
    h = json.loads(row[0]) if row else {}
    print({k:h.get(k) for k in ['checkedAt','status','watchCount','scoreHistoryReadyCount','holdingCount','pendingOrderCount','entryEnabled','reconciliationRequired','error']})
    print(c.execute('SELECT status,COUNT(*) FROM orders GROUP BY status').fetchall())
    print('unsent mail:', c.execute('SELECT COUNT(*) FROM email_outbox WHERE sent_at IS NULL').fetchone()[0])
PY
```

`.env*`, 인증 JSON, token 파일이나 메일 본문 전체를 진단 출력으로 붙이지 않는다. 이번 복사본에도 넣지 않았다.

`systemctl --user`는 SSH 세션의 사용자 DBus가 없어 조회에 실패했다. 따라서 systemd 사용자 서비스가 절대 없다고 확인한 것은 아니다. 확인한 자동 실행의 근거는 위 crontab과 실제 wrapper다. 조사 시점 MesuGak 프로세스·그 프로세스에 귀속되는 TCP listener는 없었다. 학교 서버의 모든 HTTP 서비스가 없다는 뜻은 아니다.

## 6. 증상별 확인 순서

| 증상 | 먼저 확인할 것 |
|---|---|
| 장중 프로세스 없음 | 서버 시각·크론·휴장 판단·Python 경로·최근 종료 로그·flock 보유자 |
| 감시는 많은데 매수 없음 | 최신 실시간 점수 `>60`, 이력 준비, 현금·현재 3종목 한도, 거래 불가/재진입 차단, 신규 진입 마감, reconciliation |
| 주문 접수 후 멈춤 | 로컬 주문 상태·원 주문일의 REST 체결·실제 잔고, UNKNOWN 원인. 임의 상태 삭제/재주문 금지 |
| 전체 검사 미완료 | `contest-kis-scan.json`, 08:50 deadline, 실패 유형, shared KIS pacing, 이력 수 |
| 사이트 자료가 하루 전 | 공공 API latest date와 refreshed date. 대회 KIS 시세와 비교해 오류로 단정하지 않음 |
| 마감 메일 없음 | outbox 해당 날짜 key·sent_at·재시도 시간·Gmail 설정 여부·마감 로그 |
| 공개 분석 지연 | watcher marker·analysis.lock·progress·health·cost 상태, API 공개 지연 |
| 재실행이 거부됨 | 일일 실행량 예약은 실패도 소모. budget DB를 지워 우회하지 않음 |

복구·재시작은 [복사본·복구 문서](SNAPSHOT.md)를 먼저 읽는다. 이 문서의 조회 예제에는 매매 실행이나 강제 재시작 명령을 넣지 않았다.
