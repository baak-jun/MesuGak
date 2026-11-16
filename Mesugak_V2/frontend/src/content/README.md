# 공개 글 편집 지도

사이트에 보이는 글을 고칠 때 이 문서부터 보세요. 아래의 **경로는 `Mesugak_V2/frontend/` 기준**입니다. `dist/`는 빌드 결과이므로 직접 고치지 않습니다.

## 페이지별 수정 위치

| 사이트 주소 | 화면 제목·내용 | 고칠 파일과 항목 |
| --- | --- | --- |
| `/` | 첫 화면, 서비스 소개, 학습 순서 | `src/content/pageCopy.js` → `home` |
| `/learn/` | 지표를 읽는 법 | `src/content/pageCopy.js` → `learning`; 지표 카드 설명은 `learningCopy.js` → `indicatorPages` |
| `/learn/articles/` | 숫자 뒤에 있는 이야기, 글 목록 | `pageCopy.js` → `articles`; 카드 제목·소개는 각 글의 Markdown 원고 |
| `/learn/cases/` | 엇갈리는 신호 읽기, 사례 수업 8편 | `pageCopy.js` → `cases`; 각 사례의 질문·해석·반례·확인 목록은 `learningCopy.js` → `caseStudies` |
| `/learn/lab/` | 조건을 조합해 보기 | `pageCopy.js` → `lab`; 각 조건의 설명은 `learningCopy.js` → `labConditions` |
| `/learn/glossary/` | 기술지표 용어집 | `pageCopy.js` → `glossary`; 용어의 뜻·읽는 법은 `learningCopy.js` → `glossaryTerms` |
| `/methodology/` | 점수 계산 방법 | `pageCopy.js` → `methodology`; 본문은 `learningCopy.js` → `methodologySections`, `methodologySupplementSections`; 변경 기록은 `editorialChangelog` |
| `/about/` | MesuGak 소개, 운영 안내 | `pageCopy.js` → `about`; 본문의 운영·갱신 안내 문장은 `LearningPages.jsx` → `AboutPage` |
| `/analysis/` | 공개 분석 읽기, 실제 분석 결과 | 도입 글은 `pageCopy.js` → `analysis`; 결과 설명·지표별 그림 문구는 `analysisEducationContent.jsx`, 상태별 인터페이스 문구는 `ResearchApp.jsx` |
| `/privacy/`, `/terms/`, `/data/`, `/disclaimer/` | 개인정보·이용약관·데이터·면책 안내 | `src/content/legalCopy.js` → `legalPages`에서 해당 페이지의 `title`, `sections` |

`pageCopy.js`, `learningCopy.js`, `legalCopy.js`는 모두 이 폴더에 있습니다. 버튼·메뉴 이름처럼 화면 동작과 붙어 있는 짧은 문구는 해당 화면의 JSX 파일에 남아 있습니다. 위 표의 파일명을 검색하면 바로 찾을 수 있습니다.

## 긴 글 6편

각 원고는 **한 파일이 한 페이지**입니다. 본문 문장을 고칠 때는 다음 Markdown 파일만 열면 됩니다.

| 사이트 주소 | 글 제목 | 원고 파일 |
| --- | --- | --- |
| `/learn/articles/ichimoku/` | 일목균형표, 다섯 선은 왜 함께 볼까 | `src/content/articles/ichimoku.md` |
| `/learn/articles/bollinger/` | 볼린저 밴드의 폭은 무엇을 말할까 | `src/content/articles/bollinger.md` |
| `/learn/articles/moving-average/` | 이동평균은 왜 늦게 움직일까 | `src/content/articles/moving-average.md` |
| `/learn/articles/rsi/` | RSI 70은 부정적 신호로 볼까? | `src/content/articles/rsi.md` |
| `/learn/articles/volume/` | 거래량이 늘면 누가 사고 있을까 | `src/content/articles/volume.md` |
| `/learn/articles/valuation/` | PER과 PBR, 싸다는 말의 조건 | `src/content/articles/valuation.md` |

원고 맨 위의 `title`은 글 제목, `deck`은 제목 아래 소개, `category`는 목록의 분류, `minutes`는 읽는 시간, `updatedOn`은 글에 표시되는 수정일입니다. `## 시작하며` 아래 첫 문단은 도입 글입니다. 이어지는 `##`는 소제목이고, 그 아래 문단이 본문입니다. `:::formula`에는 계산식, `:::example`에는 숫자 예시, 마지막 `## 참고 자료`에는 출처 링크가 들어 있습니다. `slug`와 `guideKey`는 URL·그림 연결에 쓰이므로 일반적인 문장 수정에서는 그대로 두세요.

긴 글의 그림과 짧은 수업의 그림은 `analysisEducationContent.jsx`의 `educationalGuides`를 함께 씁니다. 그림 속 선·색·표시 문구를 바꾸려면 그 파일을 고쳐야 합니다.

계산 과정을 나란히 보여 주려면 아래처럼 표를 쓸 수 있습니다. 표 앞뒤에 빈 줄을 넣고 모든 행의 칸 수를 맞추세요. 모바일에서는 표 영역만 좌우로 움직입니다.

```markdown
| 항목 | 계산 | 결과 |
| --- | --- | --- |
| 상승 평균 | 5÷5 | 1 |
| 하락 평균 | 2÷5 | 0.4 |
```

현재 원고는 `##` 소제목, 빈 줄로 나눈 일반 문단, 위 형식의 표, 계산식·예시 블록, 마지막 출처 목록을 지원합니다. 일반 문단의 굵은 글씨·HTML·인라인 링크 같은 추가 Markdown 문법은 화면에 변환되지 않습니다.

## 짧은 지표 수업 6편

| 사이트 주소 | 수업 | `learningCopy.js`에서 찾을 이름 |
| --- | --- | --- |
| `/learn/ichimoku/` | 일목균형표 | `indicatorPages.ichimoku`, `workedExamples.ichimoku`, `learningChecks.ichimoku` |
| `/learn/bollinger/` | 볼린저 밴드 | `indicatorPages.bollinger`, `workedExamples.bollinger`, `learningChecks.bollinger` |
| `/learn/moving-average/` | 이동평균 | `indicatorPages.movingAverage`, `indicatorSupplementSections.movingAverage`; 예시·점검은 `['moving-average']` |
| `/learn/rsi/` | RSI | `indicatorPages.rsi`, `workedExamples.rsi`, `learningChecks.rsi` |
| `/learn/volume/` | 거래량 | `indicatorPages.volume`, `workedExamples.volume`, `learningChecks.volume` |
| `/learn/valuation/` | PER·PBR | `indicatorPages.valuation`, `workedExamples.valuation`, `learningChecks.valuation` |

`indicatorPages`는 수업 제목·소개·기본 문단, `indicatorSupplementSections`는 추가 문단, `workedExamples`는 계산 예시, `learningChecks`는 질문과 예시 답, `learningReferences`는 외부 참고 링크입니다. 긴 글 원고와 짧은 수업은 서로 다른 페이지이므로 둘 다 바꾸고 싶다면 각각 수정해야 합니다.

## 수정 후 확인

`Mesugak_V2/frontend/`에서 `npm run lint`, `npm run build`, `npm run test:static`을 실행하세요. 제목·소개·본문이 빌드된 페이지에 제대로 들어갔는지 해당 주소에서 확인합니다. 이 파일을 고쳤다고 공개 사이트가 바로 바뀌지는 않습니다. 공개하려면 검사를 마친 뒤 Firebase **Hosting만** 배포해야 합니다.

글의 계산식, 출처, 제공 범위, 개인정보·약관을 고칠 때는 실제 코드와 운영 상태도 확인하세요. 내용 수정일은 실제 내용 변경을 게시할 때 갱신합니다. 브라우저 탭 제목과 검색 결과용 설명은 `scripts/prerender.mjs`에서 따로 관리합니다.
