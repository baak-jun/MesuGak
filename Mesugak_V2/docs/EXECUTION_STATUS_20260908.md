# MesuGak 실행 상태 — 2026-09-08

이 문서는 1~4번 작업을 재개한 뒤의 실측 상태를 기록한다. 기존 계획 문서의
“계획만” 표기는 작업 재개 전 기록이며, 이 문서의 검증 결과가 최신 상태다.

## 비용·저장

- Firebase 프로젝트 `studio-5459225470-8cee2`의 Firestore 데이터베이스는
  Spark/freeTier 상태이며 Billing API와 Monitoring 시계열은 결제가 꺼져 있어
  403을 반환한다. 결제를 다시 켜지 않는다.
- 읽기 전용 컬렉션 개수 확인 결과 `strategy_candidates=0`,
  `stock_analysis=4315`, `strategy_runs=27`, `meta_data=14`,
  `public_analysis_meta=21`이었다.
- 새 분석은 `stock_analysis` 문서당 최대 130행·64KiB로 저장하고,
  `strategy_candidates` 중복 기록을 만들지 않는다. 로컬 아카이브는 별도
  경로·용량 제한을 사용한다.
- Spark에서는 Cloud Monitoring 시계열을 조회할 수 없으므로 비용 가드는
  결제 비활성 응답을 안전하게 인식하고, 로컬 일일 실행 예약·분석 수·문서
  크기 한계를 계속 적용한다. 다른 Monitoring 오류는 계속 fail-closed다.

## AdSense·콘텐츠

- 실제 게시자 ID·광고 단위·CMP가 확인되기 전까지 광고 요청과 광고 미리보기는
  프로덕션에서 모두 꺼 둔다. 예시 게시자 ID 메타 태그를 제거했다.
- 학습·법적 페이지 14개를 빌드 시 정적 HTML로 사전 출력하고 페이지별
  title·description·canonical·Open Graph 메타를 추가했다.
- 지표별 학습 글에 이해 점검·반례·예시 답안을 추가하고 콘텐츠 검토일과
  정정 문의 주소를 표시했다. 정적 페이지 테스트로 본문과 광고 미리보기 누출을 확인했다.
- 학습/법적 고지/방법론 화면은 정적 Hosting에서 제공하며, 분석·로딩·오류·관리
  화면에는 광고를 요청하지 않는다.
- `robots.txt`, `sitemap.xml`을 추가하고, 알려진 앱 경로만 Hosting rewrite로
  연결한다. 존재하지 않는 경로는 Hosting의 실제 404로 남긴다.
- AdSense 재심사 신청이나 계정 승인 상태 변경은 하지 않았다. 실제 계정 ID,
  ads.txt, Google 인증 CMP, 수동 콘텐츠 검토가 끝난 뒤 별도로 결정한다.

## 학교 서버

- 실제 체크아웃: `/home/2023112374/mesugak/repo/Mesugak_V2`
- 실행 Python: `/home/2023112374/micromamba-root/envs/py312/bin/python`
- 등록된 cron: KR 장 마감 분석, 30분 헬스 모니터, 평일 모의계좌 refresh,
  매일 17:05 저장 유지보수.
- `run_v2_kr_close.sh`는 오류 시 Gmail 알림을 호출하고, 헬스 모니터는
  체크포인트 중단·비용 가드 중단·마지막 공개 게시 지연을 감시한다.
- 변경된 Python 가드와 프런트 산출물은 기존 파일을 백업한 뒤 서버에 반영했고,
  `bash -n`, 단위 테스트, Gmail 테스트 메시지, 실제 cron 경로를 확인했다.

### 후속 확인 완료

- 비용 가드·메일 감시 코드와 테스트를 기존 파일 백업 후 서버에 반영했다.
- 로컬과 서버의 Python 단위 테스트 83개가 모두 통과했다.
- Gmail 테스트 메시지는 `test_email_sent`로 확인했다. 실제 cron은 평일 16:10에
  실행되며, 오늘 수동 사전 점검으로 분석 일일 예약 토큰이 소모되어 보호 중단된
  것은 테스트 과정의 상태이며 다음 실행일에는 새 토큰으로 시작한다.
- 1종목 공공데이터 dry-run, 헬스 감시 healthy, cron 경로와 셸 문법을 확인했다.
- 비용 preflight는 기본 read-only이고, 실제 cron만 `--reserve`로 로컬 일일
  실행 토큰을 소비하도록 분리했다. Linux cron에서 줄바꿈 정규화 후 문법도 통과했다.

## 배포 경계

- 2026-09-08 추가 Hosting 배포에서 정적 학습 페이지를 포함한 23개 파일이 반영됐다.
Firebase Functions, Firestore 규칙/인덱스, Cloud Scheduler는 배포하지 않는다.
로컬 검사와 서버 확인을 통과한 뒤 Firebase Hosting만 배포한다. 2026-09-08
최종 Hosting 배포는 `mesu-gak.web.app`에 완료했다.
