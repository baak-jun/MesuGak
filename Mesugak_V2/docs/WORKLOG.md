# Mesugak V2 Worklog

## 2026-10-16 대회 일봉 캐시 재사용·실시간 준비 분리

- 감시 39종목의 KIS 과거 봉 캐시가 모두 존재하며 로컬 검증에 약 0.22초 걸리는 것을 서버에서 확인. 낮은 heartbeat 준비 수를 일봉 조회 불가로 단정한 설명을 바로잡음.
- 구독 전 디스크 캐시 일괄 준비, 감시 교체 후 메모리 유지, 실제 누락만 단일 REST 보충하도록 변경. 실행 중 to_thread 작업을 교체 때 취소하지 않아 버려진 HTTP worker 누적을 피함.
- 마지막 실시간 점수 관측 시각을 저장·복원하고 heartbeat에 준비·누락·보충 수와 관측 점수 상위를 추가. 장전 점수를 실시간 매수 신호로 대체하지 않음.
- 로컬/서버 staging 각각 185개 테스트 통과. 보유·미확정 주문이 없는지 확인 후 백업, 실행 코드 2개·테스트 2개 반영 및 기존 execute 프로세스 재시작.
- 백업 `~/mesugak/backups/contest-cache-20261016-150142`.
- 15:05 실측: 감시 39/준비 39, 이력 누락·보충 대기 0, 메모리 이력 98종목, 로컬 준비 0.2543초, 일봉 보충 0회, 3번째 교체·454틱·새 관측 시각 포함 점수 40종목. 보유/미확정 0, 오류 없음.
- 상세: `CONTEST_CACHE_REUSE_2026-10-16.md`. 매수·매도 기준·계좌·크론 변경 없음. 신규 매수 체결 검증으로 확대해 표현하지 않음.

## 2026-10-15 학교 서버·대회·웹 운영 인수인계

- `docs/operations/`에 총괄, 서버 접속·구조·전체 크론, 대회 로직, 웹 서비스, 복사·복구 범위, 배포 파일 색인 6개 문서 작성.
- p102 `school-server-2`의 22:36 KST 배포 소스 146개를 인증값 제거 후 별도 로컬 스냅샷으로 복사. 파일 5,350개 메타데이터, 크론, 안전한 환경값, SQLite 스키마·운영 집계를 함께 확보.
- 서버 환경 로더/인자 파서 확인 결과 대회 최대 보유는 공통 env에서 상속한 3종목. 코드 기본값 5와 구분해 기록. 매매 설정은 변경하지 않음.
- 첫 KIS 전 종목 검사는 18:00 제한 시점 성공 1,457/2,755, 실패 36, `interrupted`. 전체 완료로 기록하지 않음.
- 대회 마지막 상태는 15:35 `session_complete`, 보유·미확인 주문 0. 마감 보고 메일은 15:40:14 SMTP 발송 처리, outbox 미발송 0 확인.
- Hosting 주요 HTML 3개와 robots.txt는 HTTP 200 및 로컬 dist와 일치. 서버 프론트/규칙 사본은 최신 로컬과 달라 별도로 기록.
- 클라우드에 과거 함수 ACTIVE/FAILED 리소스가 남아 있음. Billing은 비활성, Scheduler 조회는 결제 사유 403. 실제 예약 실행 여부·배포 규칙 전체는 미확인으로 명시.
- 스냅샷 원본 해시 146개, 압축 무결성·문서 링크·인증 파일 제외 확인. 전달용 ZIP 작성. 서버 배포·재시작·주문·메일·크론 변경 없음.

## 2026-10-15 대회 한투 일봉 전환·전체/감시 분리·마감 메일

- 10월 13일 공공 일봉에 15일 봉만 붙이던 대회 이력을 한투 전용 일봉 캐시로
  전환했다. 실제 14일 완성 봉과 15일 진행 봉을 확인했다. 사이트 공개 분석은 별도다.
- 대회 전 종목 한투 스캔을 평일 05:00 시작하도록 하고 첫 재검사는 서버 백그라운드에서
  진행 중이다. 공유 요청 간격·주문 우선·조회 대기 보호를 적용했다. 전체 검사가
  다 끝난 것으로 표시하거나 조회 대기를 0점으로 보고하지 않는다.
- 평일 15:40 계좌·보유·당일 거래·오류·전체/고정/랜덤 점수 메일을 추가했다.
  날짜별 중복 방지·조회/SMTP 오류 재시도와 실제 계좌 기반 미리보기를 검증했다.
- 로컬·서버 전체 테스트 각각 182개 통과.
  상세: [한투 데이터·마감 메일 기록](CONTEST_KIS_DATA_AND_DAILY_MAIL_2026-10-15.md).

## 2026-10-15 시장가 전용·주문 직후 확인·안전한 자동 재판단

- 대회 매수·매도 시장가 제출을 확인하고 미사용 지정가 재주문 코드를 제거했다.
  주문 전 클라우드 보고를 접수 뒤로 옮겨 보고 장애가 주문 전송을 막지 않게 했다.
- 별도 작업이 접수 직후 체결을 확인하며 API 제한 안에서 재조회한다. 명시적
  거절은 잔고 확인과 종목별 대기 후 최신 조건으로 재판단하고, 불명확한 접수는
  중복 제출 없이 확인·알림을 유지한다. 잔고 오류도 주기 작업을 기다리지 않고 복구한다.
- 잔고 갱신·체결 대조 중 신호 중복 발생을 막는다. 로컬·서버 전체 테스트 각각
  176개 통과 후 반영. 상세: [운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-15.md).

## 2026-10-15 주문 체결 확인 누락·전일 주문 조회 오류 복구

- 전일 주문까지 오늘 날짜로만 조회해 신규 매수가 정지된 문제를 실제 주문일별
  조회로 수정했다. 실행 중에도 누락 체결을 누적 수량·금액과 실제 잔고로 복구한다.
- 이미 체결된 매도 예약이 잔여 청산을 막던 상태를 해제했다. 잔여 삼성SDI
  16주는 기존 하락 규칙에 따라 11:33 자동 매도·체결됐다. 체결·재개 메일도 확인했다.
- 로컬·서버 전체 테스트 각각 170개 통과. 11:34 기준 신규 매수 활성,
  보유·미체결·오류 0건. 상세: [운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-15.md).

## 2026-10-13 매수 이후 최고가 기준 정정

- 매수 전 감시 최고가가 매도 기준에 섞이던 문제를 수정했다. 첫 매수 체결가에서
  시작하고 보유 중 가격·추가 체결로만 갱신한다. 부분 매도는 유지, 전량 매도는 초기화한다.
- 다음 날 재시작에도 보유 최고가·분할 단계를 복원한다. 기존 비보유 감시 기록은
  복원하지 않는다. 체결 메일의 매도 사유 문구도 매수 이후 최고가로 정정했다.
- 로컬·서버 전체 테스트 각각 166개 통과 후 서버 반영.

## 2026-10-13 장전 전체 검사·55점 감시 하한·60점 매수

- 장전 서버 전용 전체 검사를 평일 06:30에 추가하고 중단 시 07:30·08:30에
  재개한다. 오늘 검사도 백그라운드에서 시작했다. 추가 Firebase 접근은 없다.
- 고정 감시는 55점 이상만 편입하고 빈 슬롯은 무작위 탐색으로 채운다.
  최근 점수 기준 승격, 보유·미체결 보호와 기존 최고가 분할매도는 유지한다.
- 사용자가 매수 기준을 60점으로 변경해 실시간 점수 60점 초과에 즉시
  시장가 제출하도록 서버 설정·기본값·테스트를 반영했다.
- 로컬 전체·서버 전체 테스트 164개, 마지막 60점 변경 후 로컬 관련 테스트
  13개·서버 전체 164개 통과. 상세: [운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-13.md).

## 2026-10-12 최근 점수 기준 감시 교체 유지

- 감시에서 빠진 종목의 최근 실시간 점수를 유지해 예전 일봉 점수로 우선
  슬롯에 재진입하는 문제를 수정했다. 높은 점수 탐색 종목은 우선 슬롯으로 승격한다.
- 당일 순위 점수 보관·재시작 복원, 보유·미체결 보호, 탐색 순환을 유지한다.
- 로컬·서버 테스트 각각 161개 통과 후 대회 프로세스 적용.

## 2026-10-12 매매불가 종목의 지속적인 감시·분석 제외

- 감시·분석이 공통 제외 목록을 사용하고 날짜 변경·재시작 후에도 제외를 유지한다.
  새 매매불가 거절도 자동 등록하며 보유·미체결 관리 감시는 보호한다.
- 티와이홀딩스우(36328K)를 현재 전체 분석에서 제거: 사용 가능한 분석 2,727개.
  기존 선정 200개·Firestore에는 없어서 추가 클라우드 삭제는 없었다.
- 로컬·서버 테스트 각각 159개 통과, 백업 후 대회 프로세스 적용.
- 상세: [대회 운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-12.md).

## 2026-10-12 대회 체결·정지·재개 메일

- 기존 수신 주소로 체결 상세와 오류 정지·정상 재개를 자동 발송. SQLite에
  알림을 저장하고 비동기 발송·재시도·중복 통보 차단을 적용했다.
- 실제 설정 확인 메일 발송 성공, 로컬·서버 테스트 각각 155개와 래퍼 구문 검사 통과.
- 모의 매매불가 종목의 명확한 주문 거절은 당일 해당 종목만 제외한 뒤
  계좌 확인 후 재개하며, 결과 불명 주문의 안전 중지는 유지한다.
- 상세: [대회 운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-12.md).

## 2026-10-12 대회 실시간 점수 진입과 최고가 분할매도

- 대회 매수: 진행 중인 한투 당일 봉으로 공통 지표를 갱신, 점수 63점 초과 시
  추가 단타 돌파 조건 없이 시장가 제출. 사이트용 설정은 별도로 유지.
- 감시 최고가 대비 1.8% 하락에서 50%를 한 번 매도하고 3%에서 나머지 전량 매도.
  보유·미체결 종목 감시 보호, 최고가·분할 단계 복원, 겹치는 매도 수량 검증.
- 로컬·학교 서버 테스트 각각 147개 통과, 백업 후 대회 프로세스 재시작.
- 상세: [대회 운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-12.md).

## 2026-10-12 대회 자동매매 복구 및 전체 분석

p102의 시세 프레임 해석과 요청 제한 대응을 수정하고 코스피·코스닥 2,765개
전체 분석을 완료했다(성공 2,728개, 자료 부족 37개). 대회는 전체 로컬 점수를
읽어 35개 고득점·보호 종목과 4개 무작위 종목을 순환 감시한다. 사이트 매매는
대회 우선 요청에 따라 중지 상태다. 로컬·서버 테스트 각각 139개 통과와 실제
시세 수신을 확인했으며 아직 주문 신호·체결은 없다. 최종 운영 증거·자료 기준일·
복구 위치는 [대회 운영 기록](SCHOOL_SERVER_CONTEST_AUDIT_2026-10-12.md)에 기록했다.

This document is the running handoff list for continuing V2 work without re-asking for direction.

## Done

- Split the repository into preserved `Mesugak_V1/` and active `Mesugak_V2/`.
- Added V2 strategy engine modules:
  - `indicators.py`
  - `scoring.py`
  - `risk.py`
  - `portfolio.py`
  - `orders.py`
  - `analysis.py`
  - `market_data.py`
  - `repositories.py`
  - `checkpoints.py`
  - `backtest.py`
- Implemented multi-indicator analysis:
  - Ichimoku Cloud
  - moving average support
  - Bollinger Bands
  - RSI
  - confidence score
  - risk flags
  - cash target
  - stop-loss
- Implemented V1-compatible analysis payloads:
  - `stock_analysis/{MARKET}_{CODE}`
  - `meta_data/meta_v2_{MARKET}_{N}`
- Implemented the active KR market universe through the Financial Services
  Commission public stock-price API. The current deployment does not run a US universe.
- Implemented checkpoint/resume support for long analysis runs.
- Fixed dry-run behavior so default `--dry-run` analysis does not read or write production checkpoint files.
- Implemented rebalance target allocation and staged order generation.
- Implemented Firestore repository methods for:
  - stock analysis
  - meta chunks
  - strategy runs
  - strategy candidates
  - target allocations
  - rebalance orders
  - risk state
  - current V1-compatible positions
- Implemented a reusable backtest engine with N+1 trade execution to avoid lookahead bias.
- Implemented V2 pure paper ledger logic.
- Implemented Firestore persistence helpers for V2 paper positions, trade logs, account snapshots, rebalance order reads, and latest price reads.
- Added `apply_paper_orders.py` job to apply staged orders to the V1-compatible paper account collections.
- Added integration tests for the rebalance-to-ledger job path using a fake repository.
- Added duplicate allocation protection through `appliedAllocationIds`.
- Enhanced the frontend paper panel with source/mode, total equity, cash, realized PnL, and recent trade logs.
- Added `run_paper_flow.py` orchestration command for analyze -> rebalance -> apply.
- Added `paper_order_applications/{allocationId}` audit writes for applied paper orders.
- Split the frontend build into manual chunks for Firebase, charting, and core vendor packages.
- Added Firestore rules coverage for `paper_order_applications`.
- Added Firebase Python scheduled function wiring for the paper flow.
- Added dedicated frontend execution history table with action/source filters and execution summary.
- Added deployment notes and Firestore index notes.
- Added Firestore-free local smoke-test command for the operator flow.
- Added production scheduler validation checklist and CI verification commands.
- Added GitHub Actions workflow for V2 backend tests, Python compile, smoke test, and frontend build.
- Added separate frontend workspace mode for execution history.
- Added scheduler environment validation helper.
- Added optional Firestore emulator smoke path guarded by `FIRESTORE_EMULATOR_HOST`.
- Split CI Python dependencies into `functions/requirements.ci.txt`.
- Confirmed GitHub Actions CI success on run `26025876706`.
- Added CI badge to root and V2 README files.
- Added V2 release checklist.
- Built V2 frontend strategy console:
  - signal list
  - technical chart
  - indicator toggles and style controls
  - score breakdown
  - risk panel
  - staged rebalance orders
  - Firestore-backed data loading with mock fallback
  - Google login and per-user chart setting persistence
  - paper portfolio snapshot panel reading V1-compatible bot collections
- Added backend tests for:
  - indicators
  - scoring
  - risk
  - analysis payloads
  - market data helpers
  - checkpoint behavior
  - portfolio allocation
  - order generation
  - backtest behavior
- Last verified:
  - `python -m unittest discover -s Mesugak_V2\functions\tests`: 43 tests passing
  - `python Mesugak_V2\functions\jobs\smoke_test_flow.py`: passing
  - `python Mesugak_V2\functions\jobs\validate_scheduler_env.py`: passing
  - `npm run build` in `Mesugak_V2\frontend`: passing

## Current Gaps

- Scheduled paper flow is wired for Firebase Functions, but production runtime limits need to be validated on a real deploy with the target market size.
- CI workflow has been observed passing on GitHub.
- Firebase Functions environment variables are documented and validated locally; production runtime limits still need real deploy observation.

## Next Work Queue

1. Add production runtime observations after the first scheduled run.
2. Add emulator-backed CI job only if Firebase emulator startup is needed in CI.
3. Add deployment result notes after the first Firebase deploy.

## Operating Rule

When continuing work, take the first incomplete item in `Next Work Queue`, implement it, add focused tests, run verification, then update this file before moving to the next item.

## 2026-10-21 Contest volume watch and health upgrade

- User-authorized p102 mock contest deployment: maximum 39 watched, protected holdings/pending, volume ranking discovery, inclusive score 58 entry and score <50 momentum entry.
- Added 6-minute observed price/volume windows and faster surge-position trailing exits (0.8% half, 1.5% all); ordinary entries retain 1.8%/3%.
- Moved scoring off quote handling; exchange timestamps, 3-second score freshness, independent health alerts and cache-first resumable universe scans.
- Local and p102 staging: 197 backend tests passed. Backups, research sources, schedules, limitations and rollback: `CONTEST_VOLUME_UPGRADE_2026-10-21.md`.
- 14:58 KST live verification: 39 watched, 2,429 ticks, 37 recently updated scores, 38 prepared histories; one history failure remains explicitly blocked and recorded. Full scan resumed; completion is tracked rather than assumed.
- Final follow-up: 198 local/server staging tests passed, including correct surge exit email thresholds. Actual surge signals produced three mock market-order attempts, all explicitly rejected as nontradable and excluded; no fills at that check. Full scan ended with 2,712 successes, 39 failures, zero unprocessed after three exclusions. See the upgrade document for timestamped evidence.
- 16:28 후속 배포: 마감 요약 후 16:05 다음 평일용 점수까지 사전 계산, 저녁 재개, 아침 08:00/08:30 원본·알고리즘 지문 확인 후 결과 재사용. 로컬/서버 201개 테스트 통과. 실시간 trader 재시작 없음. 서버 백업: `/home/YOUR_SCHOOL_ID/mesugak/backups/contest-night-20261021-162805`.

## 2026-10-22 Contest repeated-alert reliability

- Diagnosed active trading separately from repeated calculation availability and isolated quote-idle notices; confirmed two short-history samples.
- Added typed/counted short-history failures, preserved short valid caches and next-day retry limits, avoiding repeated same-day history API requests.
- User threshold: no dedicated calculation-unavailable emails at <=100; alert at >=101. Whole-feed/held quote failures remain immediate; non-held idle/recovery requires consecutive observations.
- Local and p102 staging: 207 tests passed. Backup: `/home/YOUR_SCHOOL_ID/mesugak/backups/contest-errors-20261022-100017`. Deployed without restarting active trader. Detailed evidence in `CONTEST_VOLUME_UPGRADE_2026-10-21.md`.

2026-10-22 10:04 최종 보완: 새 구독 체결을 포함해 전체 수신 중단 오탐 방지. 로컬/서버 208 tests OK.
재분류 완료: 성공 2690, 미처리 0, 일봉 부족 38, 기타 계산 오류 0; 계산 불가 메일 대기 0.
보유 3/미체결 0, trader 재시작 없이 streaming_execute 유지. 비보유 단일 종목 체결 공백은 별도 주의.

## 2026-10-22 AdSense content review and calculation practice

- Rechecked the deployed 25-route surface; all route, metadata, ad-disabled and unknown-path checks passed. Existing six long-form articles were already published.
- Added local-only synthetic Bollinger calculation practice, reversed-sequence/flat-price comparisons, initial static worked output and home/article entry links. Fixed one 404 pandas reference among 21 checked external source URLs.
- Verified build/content (11), calculation (6), static (3), policy (4), lint and browser interactions at desktop, 390px and 320px. No Hosting deployment, review submission, backend changes or advertising activation in this task.
- Backup, evidence, remaining account/operational checks and rollback: `ADSENSE_AUDIT_2026-10-22.md`.
- Follow-up user approval: deployed only mesugak-target Hosting (36 files, 1,415,151 bytes). CLI release completed despite auxiliary authentication/update errors; live 25-route preflight passed with zero failures and new calculator interactions were verified. No AdSense submission or ad activation.

2026-10-29: 대회 Firestore 동기 의존성 제거(Local SQLite+제한된 비동기 보고), 공공 종목목록 캐시/최대7일 fallback,
일봉부족 오탐 제거, 같은날 재매수제한 복원, KIS 잔고/체결/구독준비 API 우선순위 보완. 서버 219 tests OK.
백업·활성화·확인 범위는 CONTEST_VOLUME_UPGRADE_2026-10-21.md의 2026-10-29 항목 참고.
