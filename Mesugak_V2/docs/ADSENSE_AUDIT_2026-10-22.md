# AdSense 최종 점검과 계산 실습 보완 — 2026-10-22 KST

## 판단

사용자가 확인한 심사 주소는 https://mesu-gak.web.app 이다. 제공한 화면은 ‘가치가 별로 없는 콘텐츠’ 반려이며 문제 URL이나 반려 날짜는 없다. 현재 사이트를 확인했지만 Google의 내부 거절 원인은 확정할 수 없다. 긴 글 6편과 기존 교육 자료는 실제 배포되어 있으므로 단순 미배포나 글 개수 부족으로 설명하지 않는다.

기술적인 기본 점검은 통과했다. 이번에는 수업을 실제로 활용할 수 있는 계산 실습, 대표 콘텐츠 접근 동선, 끊어진 출처 링크를 보완했다. 이것이 승인 보증이나 실제 독자 관심의 증거는 아니다. **후속 사용자 승인으로 Hosting 게시와 라이브 검증을 완료했다. 재심사 제출·광고 활성화는 하지 않았다.**

## 확인한 사실

- 기존 라이브 `npm run test:live`: 25개 경로 HTTP 200, 임의 경로 404, 고유 metadata/canonical, sitemap/robots 경계, 게시자 메타와 ads.txt의 문자열 일치, 광고·Analytics 비활성, 실패 0건. 계정의 실제 게시자 ID 대조나 Search Console 소유권 확인을 뜻하지 않는다.
- 기존 긴 글 6편은 초기 HTML에도 본문이 있었다. 홈은 학습 경로·운영 설명 중심이며 개별 질문에서 깊이 있는 글로 바로 들어가는 연결을 강화할 여지가 있었다.
- 기존 실험실은 조건별 해석을 보여 주지만 사용자가 숫자를 바꾸어 계산 결과를 검증하는 기능은 없었다. 이는 사용 가치 개선 기회이지 입증된 반려 원인이 아니다.
- 학습 콘텐츠의 외부 참고 URL 21개를 GET으로 점검: 20개 HTTP 200, pandas의 이전 `pandas.core.window.rolling.Rolling.std.html` 주소만 404. 새 `pandas.api.typing.Rolling.std.html` 공식 문서로 교체했다.
- 공개 분석은 브라우저에서 30 / 200 종목, 기준일 2026-10-20으로 표시됐다. 이 관찰만으로 제공기관의 최신 자료나 서버 장애를 판정하지 않았다. 서버 변경·전체 데이터 조회를 실행하지 않았다.

## 이번 보완

1. `/learn/lab#band-calculator`: 가상 종가 2~120개를 입력해 평균·표본/모집단 표준편차·상하단·밴드 폭·%b를 비교한다. 초기 5개 값의 계산 결과와 해설도 정적 HTML에 포함한다. 실제 V2의 20봉 설정과 교육용 짧은 창을 구분한다.
2. 상승/하락 역순 비교로 ‘폭은 같지만 마지막 위치는 다르다’를 직접 확인한다. 동일 가격에서는 폭 0과 %b 계산 불가를 표시한다. 그림은 마지막 창의 경계이며 과거 이동 밴드가 아니라는 설명을 붙였다.
3. 입력 오류, 개수 상한, 소수, 비정상 값, 0으로 나누는 경우를 처리한다. 입력은 브라우저 메모리에만 있고 서버 호출·저장·추적 기능을 추가하지 않았다.
4. 홈에 구체적인 질문 3개와 계산 실습·볼린저 글·거래량 글의 직접 링크를 추가했다. 볼린저 긴 글에서도 실습으로 이어진다. 새 URL을 대량 생성하거나 기존 수업을 삭제하지 않았다.
5. 끊어진 pandas 링크를 교체하고 해당 글 수정일과 실제 변경 기록을 갱신했다. 이번 구현의 AI 도구 활용과 자동 수치 대조를 밝혔으며 전문 금융 검토나 운영자 전수 검토를 주장하지 않았다.

## 검증

- `npm run build`: 25개 정적 경로 생성, 콘텐츠 11개 테스트와 AdSense 산출물 사전검사 통과.
- `npm run test:lab`: 6개 통과. 손계산 5값, 역순 불변성, 20값의 표본/모집단 비율, 동일 소수 가격, 잘못된 입력, 최대 개수 포함.
- `npm run test:static`: 3개 통과. JS 실행 전 기본 계산 결과·0÷0 해설 존재도 검사한다.
- `npm run test:policy`: 4개 통과. `npm run lint` 통과.
- 실제 로컬 브라우저: 상승 %b 0.8162, 하락 0.1838, 동일 가격 계산 불가, 음수 입력 오류, 모집단 표준편차 2.8284, 계산 과정 펼치기 확인. 경고·오류 로그 없음.
- 모바일 브라우저 뷰포트 320px / 390px에서 문서 폭 305px / 375px로 가로 넘침 없음. 실기기·200% 확대·스크린리더 검증을 대신하지 않는다.
- 기존 라이브 결과와 새 로컬 산출물을 구분한다. 새 계산 실습의 라이브 확인은 Hosting 게시 이후에 해야 한다.

## 재심사 전 남은 확인

- 운영자가 대표 글과 새 계산 실습을 읽고 실제 제공하는 서비스 설명과 일치하는지 확인한다. 허구의 경력·전문가 검토·사용자 후기·수익 성과를 추가하지 않는다.
- AdSense 계정의 현재 등록 URL·게시자 ID·최신 반려 상세를 대조한다. 첨부 화면 외 계정 상태는 확인하지 않았다.
- Search Console에서 대표 URL의 색인·크롤링 상태와 실제 이용 자료를 확인하면 원인을 좁히는 데 도움이 된다. 최소 트래픽·글 수·글자 수를 Google의 공식 승인 기준처럼 제시하지 않는다.
- 공개 분석의 다음 정상 기준일 갱신 여부를 확인한다. 갱신 주기나 서버 복구 능력은 이번 프런트엔드 검증 범위에 포함되지 않는다.
- Hosting 게시 후 새 실습·홈 링크·출처 링크와 라이브 검사를 재확인하고 재심사 여부를 결정한다.

## 백업과 복구

- 수정 전: 저장소 루트 `.cache/adsense-review-20261022/before-frontend-docs.zip`.
- 기존 수정·미추적 파일을 포함한 프런트엔드/문서와 firebase.json 93개, 457,262 bytes. node_modules·dist·실제 .env 등 비밀 환경 파일은 제외한 범위 백업이다. 전체 저장소나 서버 백업이 아니다.
- ZIP 무결성 및 각 파일 SHA-256을 `manifest.json`과 대조했다. `git-status-before.txt`에 시작 상태를 보존했다.
- 복구할 때 ZIP 전체를 덮어쓰지 말고 별도 폴더에 풀어 이번 수정 파일만 비교·복원한다. 기존 dirty 작업과 이후 작업을 보존해야 한다. 새 파일은 `src/bandLab.js`, `src/BandCalculationLab.jsx`, `scripts/band-lab.test.mjs`와 이 감사 문서다.
- `.cache/adsense-review-20261022/`에 출처 HTTP 검사와 모바일/데스크톱 스크린샷을 저장했다.

## 비용·배포 범위

추가 계산은 클라이언트 내부에서 수행한다. 새 Firestore 읽기/쓰기·Functions 호출·저장 문서·스케줄은 0이다. 게시하면 정적 JS/HTML/CSS 증가에 따른 Hosting 저장·전송량은 증가한다. 청구 상태나 누적 무료 한도를 이번에 조회하지 않았으므로 무조건 무료라고 단정하지 않는다. 배포 시 대상은 기존 `mesugak-target` Hosting으로 제한하고, 실제 누적 사용량은 게시 전에 확인한다.

## 기준 자료

- [AdSense 페이지 준비](https://support.google.com/adsense/answer/7299563?hl=ko): 고유 콘텐츠, 명확한 탐색, 독자에게 유용한 경험.
- [AdSense 콘텐츠 및 사용자 환경](https://support.google.com/adsense/answer/10015918?hl=ko): 충분한 고유 가치, 중복 최소화, 콘텐츠 유지관리와 탐색.
- [Google 사용자 우선 콘텐츠 자체 점검](https://developers.google.com/search/docs/fundamentals/creating-helpful-content?hl=ko): 출처·신뢰와 독자 문제 해결에 관한 검색 품질 안내이며 별도의 AdSense 승인 공식은 아니다.
- [John Bollinger 규칙](https://www.bollingerbands.com/bollinger-band-rules): 폭과 위치의 구분, 밴드 접촉만으로 매매 신호를 확정하지 않음.
- [pandas Rolling.std](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.typing.Rolling.std.html): 기본 ddof=1, 분모 N−ddof.


## 사용자 승인 후 Hosting 게시 결과

- 2026-10-22 사용자 요청에 따라 `firebase deploy --only hosting:mesugak-target --project studio-5459225470-8cee2 --non-interactive` 실행. 정적 산출물 36개, 1,415,151 bytes를 대상으로 새 버전 release complete 확인.
- CLI는 인증/MOTD·업데이트 설정 확인 오류와 함께 종료 코드 1을 반환했다. 업로드·finalize·release는 완료됐고 실제 공개 페이지에서 새 콘텐츠를 별도로 확인해 게시 성공을 판정했다. 재인증·권한 변경은 하지 않았다.
- 라이브 홈의 실습 링크, 실험실의 band-calculator/기본 계산/0÷0 해설, 볼린저 글의 새 출처·실습 링크, 방법론의 2026-10-22 변경 기록을 HTTP 200 본문으로 확인했다.
- 실제 공개 브라우저에서 역순 %b 0.1838, 동일 가격 계산 불가, 상승 순서 0.8162 동작 확인. 스크린샷: `.cache/adsense-review-20261022/deployed-lab.png`.
- 배포 산출물 ZIP과 SHA-256 목록: `.cache/adsense-review-20261022/release-hosting.zip`, `release-manifest.json`.
- Hosting만 배포했다. Firestore/Functions/서버 작업/결제/광고/Analytics 설정 변경 없음. 기존 요청량 경로는 그대로이며 추가 계산은 브라우저 내부에서 수행한다. Hosting의 프로젝트 누적 저장량·방문량은 미조회이며 산출물 바이트와 구분한다.
- 게시 후 npm run test:live: 공개 25개 경로, 임의 경로 404, metadata/색인/광고 비활성 검사 실패 0건, 종료 코드 0으로 통과.
