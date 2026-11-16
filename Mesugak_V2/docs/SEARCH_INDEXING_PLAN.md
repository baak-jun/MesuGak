# Google 검색 노출 계획

이 문서는 Firebase Hosting으로 제공하는 `mesu-gak.web.app`의 검색 노출을 위한 운영 계획이다. 검색 노출이나 AdSense 승인을 보장하는 문서가 아니며, Search Console에서 확인할 수 있는 증거를 기준으로 판단한다.

## 핵심 결론

- Firebase Hosting 도메인도 일반 웹사이트처럼 Google 크롤링·색인 대상이 될 수 있다.
- Instagram 등 외부 홍보는 방문자와 발견 경로를 늘릴 수 있지만, 방문자 수가 일정 수준에 도달해야 색인되는 구조는 아니다.
- 외부 링크만 기다리지 않고 Search Console에 사이트맵을 제출하고, 중요한 URL을 URL 검사로 요청하는 것이 기본 절차다.
- Firebase 기본 `web.app` 주소는 사용자가 DNS 사업자에서 관리하는 도메인이 아니므로, Search Console의 도메인 속성(DNS TXT 인증) 대신 `https://mesu-gak.web.app/` URL 접두어 속성을 사용한다. DNS 인증은 별도 사용자 도메인을 연결했을 때만 선택한다.
- `robots.txt`는 전체 공개 경로를 허용하고 `sitemap.xml`을 가리킨다. 종목별 동적 분석 URL은 유사하거나 빠르게 변하는 결과 페이지의 대량 색인을 피하기 위해 `noindex,follow`와 사이트맵 제외를 유지한다. 이는 색인 범위 선택이며 분석 방법이나 사용자 가치를 낮게 평가한 결과가 아니다.
- 검색 유입을 늘리기 위해 종목별 분석 URL을 대량 생성하거나 광고를 먼저 켜지 않는다. 사람이 읽고 배울 수 있는 정적 학습 콘텐츠를 검색 대상의 중심으로 둔다.

## 현재 구현 상태

- `/`는 서비스 목적과 학습 경로를 설명하는 고유 랜딩 페이지다.
- `/learn`은 지표 커리큘럼 허브다. 두 경로를 같은 본문으로 렌더링하지 않는다.
- `/learn/ichimoku`, `/learn/bollinger`, `/learn/moving-average`, `/learn/rsi`, `/learn/volume`, `/learn/valuation`, `/learn/cases`, `/learn/lab`, `/learn/glossary`, `/methodology`, `/about`에는 경로별 학습·운영 콘텐츠가 공개되어 있다. 정적 HTML과 코드 검사는 해당 콘텐츠의 존재와 내부 일관성만 보여 주며, 운영자의 최종 편집 검토나 작성자 경력은 아직 확인되지 않았다.
- `/terms`, `/privacy`, `/data`, `/disclaimer`는 서비스 이용에 필요한 보조 안내 페이지이며 현재 정적 경로·사이트맵에 포함되어 있다. 학습 본문과 별도의 목적을 유지하고, 운영자가 실제 문구와 서비스 동작의 일치를 확인한다.
- `/analysis`는 운영자가 실제 분석에 사용하는 규칙을 공개 데이터에 적용하는 동적 분석 도구다. 초기 교육 안내와 방법론 링크를 제공하지만 `noindex,follow`이며 `sitemap.xml`에는 넣지 않는다. 이 색인 경계는 종목별 URL의 중복·변동을 줄이기 위한 것이며 분석 도구가 저가치라는 판정은 아니다.
- 정적 공개 페이지에는 한국어 Open Graph 로케일·사이트명과 Twitter `summary` 카드 메타데이터를 넣어 외부 공유 시 페이지 목적이 일관되게 보이도록 한다. 공유용 메타데이터는 검색 색인이나 순위를 보장하지 않는다.
- 광고 요청, Analytics 로더, Firestore·Functions 설정은 이 검색 노출 작업에서 활성화하지 않는다.
- 2026-09-29 Hosting-only 배포를 완료했고, Firestore·Functions·결제·광고 설정은 함께 배포하지 않았다.
- 배포 후 `npm run test:live`가 18개 경로 모두 HTTP 200, `robots.txt`·`sitemap.xml`·canonical·`/analysis`의 `noindex`, 광고·Analytics 비활성 경계를 통과했다.
- 2026-10-01 실습실 설명을 수정해 Hosting-only로 재배포했다. 라이브 18개 경로 검사가 실패 0건으로 통과했고, 브라우저에서 밴드 폭 확장 선택 시 가능한 해석과 방향의 한계가 함께 표시되는 것을 확인했다.
- 2026-10-01 17개 사이트맵 URL의 초기 HTML을 다시 가져와 모두 HTTP 200임을 확인했다. 보이는 전체 문구의 단어 집합 비교는 최대 Jaccard 0.337이었지만 공통 내비게이션·반복 문구도 포함하는 단순 내부 선별치다. Google의 독창성 평가나 사람의 편집 검토를 대신하지 않는다.

## 운영자 절차

1. Google Search Console에서 `https://mesu-gak.web.app/` 속성을 도메인 또는 URL 접두어 방식으로 확인한다.
2. HTML 태그 방식을 선택하는 경우 Search Console이 제공한 `content` 값만 `frontend/.env.local`의 `VITE_GOOGLE_SITE_VERIFICATION`에 넣고 빌드·Hosting-only 배포한다. 값이 없을 때는 빈 태그를 생성하지 않는다.
3. `https://mesu-gak.web.app/sitemap.xml`을 사이트맵으로 제출한다. 성공 여부와 발견된 URL 수를 기록한다.
4. `/`, `/learn`, 대표 지표 수업 2~3개, `/methodology`, `/about`을 URL 검사한다.
5. “색인 생성 요청”은 실제로 수정된 대표 URL에만 사용한다. 같은 URL을 반복 요청하거나 자동 분석 URL을 대량 요청하지 않는다.
6. 며칠 뒤 Search Console의 색인 생성 보고서와 페이지 색인 상태를 확인한다. “발견됨”과 “색인됨”을 같은 의미로 기록하지 않는다.
7. `robots.txt`, canonical, 초기 HTML의 title·H1·본문·내부 링크가 배포본에서도 일치하는지 `npm run test:live`로 확인한다.

### 기본 `web.app` 주소의 인증 선택

Search Console에서 `mesu-gak.web.app`만 입력해 DNS TXT 인증 화면이 나오면, `URL 접두어 속성을 대신 사용`을 선택한다. URL에는 프로토콜과 마지막 `/`를 포함해 `https://mesu-gak.web.app/`를 입력한다. 이후 HTML 태그 방식을 선택하고, 발급된 태그의 `content` 값만 `VITE_GOOGLE_SITE_VERIFICATION`에 넣는다. 화면에 보인 `google-site-verification=...` TXT 문자열은 DNS 방식 전용이므로 환경변수에 그대로 넣지 않는다.

## Instagram 홍보의 역할

Instagram 게시물·프로필에 홈, 학습 글 또는 분석 방법 안내 링크를 넣으면 사람을 유입시키고 Google이 URL을 발견할 가능성을 높이는 데 도움이 될 수 있다. 그러나 소셜 유입, 팔로워 수, 클릭 수는 색인의 조건이나 보증 수치가 아니다. 게시물은 실제 사용자의 질문, 분석 규칙을 적용한 근거, 해석의 한계를 설명하고 종목 점수만 반복해서 나열하지 않는다.

권장 링크 순서는 다음과 같다.

1. 프로필 링크: `https://mesu-gak.web.app/`
2. 교육 게시물: 해당 지표의 `/learn/...` 또는 `/learn/cases`
3. 서비스 사용 안내: `/methodology`

## 배포·재심사 게이트

- 로컬 `npm run lint`, `npm run build`, `npm run test:static`, `npm run test:content`, `npm run test:policy`, `npm run test:adsense`가 모두 통과할 것.
- 배포가 필요할 때는 `firebase deploy --only hosting --project studio-5459225470-8cee2`만 사용하고, Firestore·Functions·결제·광고 설정은 함께 배포하지 않을 것.
- 배포 후 `npm run test:live`에서 18개 공개 경로, `robots.txt`, `sitemap.xml`, HTTP 상태, canonical, `/analysis`의 noindex 경계를 확인할 것.
- Search Console에서 색인 상태가 확인되기 전까지는 “Google에 노출된다”고 표현하지 않고 “크롤링·색인을 요청했다”고 표현할 것.

## 2026-09-29 배포 검증 기록

- Hosting URL: `https://mesu-gak.web.app`
- Firebase project: `studio-5459225470-8cee2`
- 배포 범위: Hosting만
- 확인 결과: `npm run test:live` 실패 0건
- 라이브 루트와 학습 허브가 서로 다른 본문을 제공하며, `/analysis`는 계속 `noindex,follow`로 유지된다.
- 2026-09-29 후속 Hosting-only 배포에서 Open Graph·Twitter 공유 메타데이터를 추가했고, `npm run test:live`가 다시 실패 0건으로 통과했다.
- Search Console 등록·소유권 확인·사이트맵 제출은 운영자 Google 계정에서 수행해야 하며, 아직 그 계정 작업을 완료했다고 간주하지 않는다.
- 2026-09-29 배포 직후 공개 검색에서 `site:mesu-gak.web.app`와 서비스명 조합을 조회했지만 결과가 없었다. 이는 색인 대기 가능성을 보여 주는 관찰일 뿐이며, 색인 여부는 Search Console URL 검사로 확인한다.
- 2026-09-29 `VITE_GOOGLE_SITE_VERIFICATION`을 넣은 Hosting-only 배포 후 라이브 홈페이지에서 verification meta 마커 1개가 확인됐다. Search Console의 URL 접두어·HTML 태그 화면에서만 확인을 눌러야 하며, DNS 속성 화면의 TXT 레코드는 사용하지 않는다.

## 2026-10-01 라이브 사전검사 보강

- 후속 Hosting-only 배포 후 `npm run test:live`에서 18개 공개 경로 HTTP 200, `/analysis`의 `noindex`, robots·sitemap 경계와 함께 임의 경로의 HTTP 404를 확인했다. 잘못된 경로가 홈으로 되돌아오는 soft 404 동작은 관찰되지 않았다.
- 같은 검사에서 홈페이지의 Search Console 확인 메타 태그가 1개 존재하는 것을 확인했다. 태그 존재만으로 Search Console 속성 소유권, 사이트맵 제출, 색인을 확인할 수는 없다.
- Search Console 계정에 접속하지 않았고, 색인 보고서·URL 검사·사이트맵 처리 결과·유기적 방문 자료는 여전히 미확인이다. 계정 작업 전까지 이 상태를 완료로 표시하지 않는다.

## 근거

- Google은 고유하고 사람에게 유용한 콘텐츠와 명확한 탐색 구조를 우선하며, 자동 생성 결과를 대량으로 색인시키는 것을 목표로 삼지 않도록 안내한다.
- 사이트맵은 크롤러가 URL을 발견하는 데 도움을 주지만 색인이나 순위를 보장하지 않는다.
