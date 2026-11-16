# 저장 정리 운영 상태 — 2026-09-08

## 2026-09-09 20:09 KST 후속 확인 완료

- 사용자 CLI 인증으로 조회한 Monitoring 최신 표본(11:06 UTC): 저장량 284,943,275 bytes, 약 271.7 MiB. 내부 700 MiB 및 무료 1 GiB 기준 이하로 반영됐다.
- Billing API 재조회: billingEnabled=false. Spark 유지.
- 오늘 실제 cron `KR_20260909_161003`: 916종목 성공, 실패 0, 16:33:49 KST 종료 status=0.
- 공개 manifest 916종목, 첫 페이지 30개, 갱신 시각 16:33:46 KST를 직접 조회해 확인.
- 이후 별도 작업에서 저장 대상이 최신 KR 최대 1,000종목으로 제한됐으며 오늘 retention 로그상 916개 유지·잔여 삭제 대상 0이다. 아래 4,315개는 09-08 당시 기록이다.
- 서버 서비스 계정은 Spark에서 Monitoring 결제 제한 응답을 받아 로컬 한도 방식으로 실행한다. 이번 실제 저장량은 사용자 CLI 인증 조회 결과이며 서버 측 실시간 용량 측정 성공과 혼동하지 않는다.
- 저장량 반영과 다음 정상 분석 완료 조건을 충족해 `mesugak-spark` 후속 자동화만 PAUSED로 전환했다. 서버 cron은 변경하지 않았다.

사용자가 모니터링 권한, 기존 예약 작업 중지, 재생성 가능한 과거 데이터 정리 및 반복 정리 cron을 명시 승인했다. 정리·점검 후 Spark 전환 승인도 유효하다.

## 적용 및 확인 완료

- 서버 서비스 계정에 roles/monitoring.viewer 추가.
- 기존 Cloud Scheduler refreshPendingOrdersFromBuySignals 예약 PAUSED 확인.
- 학교 서버 functions/.env에 로컬 최신 분석 압축 보관 경로 설정. 비밀 값은 출력하지 않았고 파일 권한은 0600.
- 서버 crontab에 매일 17:05 KST run_storage_maintenance.sh 설치 및 셸 문법 확인.
- cron은 과거 strategy_candidates를 검증된 로컬 백업 후 하루 최대 5000개 삭제하고 기존 stock_analysis 차트를 축소한다. 완료 후 재스캔을 생략하며 새 분석은 저장 시마다 130행·64KiB JSON 제한을 적용한다.
- 새 분석의 저장량 차단을 실제 서버 환경변수로 검증: 6,332,808,899 bytes > 700 MiB로 차단.

## 09-08 일회성 유료 정리 승인 및 실행

사용자가 정리 비용이 저장 유지비보다 낮으면 즉시 진행하도록 승인했다. 비교 기간은 한 달로 명시했다. Iowa 공개 USD 단가로 무료 할당량을 전혀 가정하지 않고 문서 최대 크기까지 적용한 일회성 예상 상한은 $0.54136, 실행 허용 상한은 $0.60이다. 기존 5.90 GiB 중 무료 1 GiB를 제외한 30일 저장 유지비는 약 $0.725이다. 세금·원화 청구 단가는 별도이며 청구 확정 금액이 아니다.

이번 전용 스크립트 runtime/cleanup-once.py는 후보 11,000개·최신 분석 4,500개 상한 및 예상 비용을 실행 전에 확인한다. 자동 cron의 요청 제한은 변경하지 않았다. 재생성 가능한 후보는 본문을 내려받지 않고 ID만 조회해 삭제한다. 기존 백업은 보존하고 최신 분석 변경분은 검증 백업 후 차트를 축소한다.

- strategy_candidates 10,123개 삭제 완료 후 count=0 확인. stock_analysis 4,315개 유지, 그중 3,264개 차트 축소 완료. 완료 마커 기록 및 cron 재실행 시 추가 정리 요청 없이 종료 확인.
- 공개 manifest 존재, 공개 첫 페이지 30개, 표본 차트 122행 확인. 사용자·계좌·거래 컬렉션 보존.
- 19:27 KST Spark 전환 완료: Cloud Billing API로 이 프로젝트만 결제 연결 해제하고 billingEnabled=false, billingAccountLinked=false 재조회 확인. 이후 Firestore 피드 조회와 Hosting /analysis HTTP 200 확인.
- 서버 비용 제어 테스트 5개 통과.
- 공식 단가: https://cloud.google.com/firestore/pricing

## 아직 미완료

- 최초 무료 한도 내 정리는 읽기 78,844건/최근 24시간으로 사전 차단되었다. 이후 위 일회성 비용 조건 승인에 따라 별도 실행을 시작했다.
- 19:26 KST 저장량 지표는 여전히 약 5.90 GiB를 표시한다. 집계 반영 지연 가능성이 있으나 무료 한도 이하로 반영됐다고 단정할 수 없다. Spark 전환은 완료됐고 새 분석 저장 차단은 유지한다.
- 매일 cron은 요청량 여유가 생기면 정리를 재시도한다. 모니터링 지연과 외부 요청 때문에 무과금을 보장하는 장치는 아니다.
- 백업 총량 2 GiB 또는 서버 여유 1 GiB 미만이면 정리가 중단되므로 후속 점검 필요.
- 사용자·계좌·거래 기록은 이번 재생성 가능 데이터 삭제 범위에 포함하지 않는다.
- 후속 자동화는 저장량 반영과 다음 정상 분석을 확인한 뒤 종료하도록 갱신했다. 실제 일회성 청구액은 결제 보고서 반영 전이므로 미확정이다.

서버 기준 위치: /home/YOUR_SCHOOL_ID/mesugak/repo/Mesugak_V2

관측 파일: runtime/cost/maintenance.log, runtime/cost/status.json, runtime/cost/candidates-drained, runtime/cost/analysis-compacted. 백업 위치: runtime/cloud-archives. 실제 장 마감 분석의 재개는 저장·요청량 차단 조건을 통과해야 한다.
