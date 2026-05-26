# MesuGak

MesuGak은 주식 종목의 기술적 지표를 분석해 매수 신호를 탐색하고, 사용자가 조건에 맞는 종목을 빠르게 확인할 수 있도록 만든 주식 분석 웹 서비스입니다.

현재 저장소는 두 버전으로 나누어 관리하고 있습니다.

- `Mesugak_V1/` : 포트폴리오용 완성 버전
- `Mesugak_V2/` : V1의 UI와 구조를 개선하기 위해 개발 중인 차기 버전

> 본 프로젝트는 투자 판단을 보조하기 위한 개인 개발 프로젝트입니다.  
> 특정 종목의 매수, 매도, 보유를 권유하지 않습니다.

---

## 프로젝트 배경

처음 MesuGak은 볼린저밴드 기반으로 종목의 매수 신호를 탐색하는 서비스로 시작했습니다.

V1에서는 기능 구현과 데이터 흐름 검증을 우선했습니다. 실제 종목 데이터를 분석하고, 볼린저밴드 보조지표를 기준으로 상태를 분류한 뒤, 분석 결과를 Firestore에 저장하고 웹 화면에서 확인하는 전체 흐름을 구현했습니다.

다만 V1은 빠르게 기능을 붙여 가며 개발한 버전이기 때문에 UI와 옵션이 다소 복잡해졌습니다. 그래서 현재는 V1의 난잡했던 UI와 옵션 구조를 정리하고, 단일 지표 중심 분석에서 다중 지표 기반 전략 엔진으로 확장하는 V2를 개발 중입니다.

현재 포트폴리오에서는 V1을 중심으로 소개하고, V2는 개선 중인 차기 버전으로 정리합니다.

---

## Version Overview

| Version | Status | Description |
| --- | --- | --- |
| V1 | Portfolio / Stable | 볼린저밴드 기반 매수 신호 분석 서비스 |
| V2 | In Progress | 다중 지표 기반 전략 엔진, 모의매매, 리밸런싱 구조로 개선 중인 버전 |

---

## MesuGak V1

`Mesugak_V1`은 현재 포트폴리오에서 주로 소개하는 버전입니다.

V1은 볼린저밴드 기반 매수 신호를 분석하고, 종목별 상태를 웹 화면에서 확인할 수 있도록 만든 주식 분석 서비스입니다.

### V1 핵심 기능

- 볼린저밴드 기반 매수 신호 분석
- `%b`, 밴드폭 등 볼린저밴드 보조지표 기반 정렬
- 종목 상태 분류
  - Buy Signal
  - Normal
  - Squeeze
- 분석 결과를 Firestore `stock_analysis` 컬렉션에 저장
- 장마감 이후 매수 신호 종목을 `pending_orders`로 갱신
- Firebase Cloud Functions 기반 스케줄 처리
- Cloud Functions 실패 시 Python 로컬 fallback 스크립트로 수동 갱신 가능
- Firebase Hosting 기반 웹 배포

### V1 데이터 흐름

```text
종목 데이터 분석
  ↓
볼린저밴드 보조지표 계산
  ↓
Buy Signal / Normal / Squeeze 상태 분류
  ↓
Firestore stock_analysis 컬렉션에 저장
  ↓
스케줄 함수가 buy_signal 문서 조회
  ↓
pending_orders/{MARKET}_{CODE} 문서로 upsert
  ↓
후속 트레이딩 / 모의매매 / 주문 처리 시스템에서 활용
```

### V1 화면 예시

#### Buy Signal

![Buy Signal](./Mesugak_V1/src/assets/buy_signal.png)

#### Normal

![Normal](./Mesugak_V1/src/assets/normal.png)

#### Squeeze

![Squeeze](./Mesugak_V1/src/assets/squeeze.png)

### V1 프로젝트 구조

```text
Mesugak_V1/
├── src/                                # 프론트엔드
├── functions/
│   ├── index.js                        # Firebase Functions 엔트리
│   ├── end_of_day_buy_signals.js       # 장마감 스케줄 함수
│   ├── local_refresh_pending_orders.py # 로컬 비상 갱신 스크립트
│   └── legacy/                         # 구버전 보관
├── firebase.json
├── firestore.rules
├── firestore.indexes.json
└── README.md
```

### V1을 포트폴리오로 소개하는 이유

V1은 MesuGak의 첫 번째 완성형 구현입니다.

UI와 옵션은 다소 복잡하지만, 다음과 같은 실제 서비스 흐름을 직접 구현했다는 점에서 포트폴리오로 의미가 있습니다.

- 기술적 지표 기반 종목 분석
- 분석 결과 저장
- 웹 화면에서 분석 결과 조회
- 장마감 이후 자동 갱신
- Firebase 기반 서버리스 배포
- 장애 상황을 대비한 로컬 수동 갱신 스크립트 구성

자세한 내용은 [`Mesugak_V1/README.md`](./Mesugak_V1/README.md)를 참고하세요.

---

## MesuGak V2

`Mesugak_V2`는 현재 개발 중인 차기 버전입니다.

V1이 볼린저밴드 기반 매수 신호 스캐너에 가까웠다면, V2는 여러 기술적 지표를 조합해 점수화하고, 모의매매와 리밸런싱까지 연결하는 구조를 목표로 합니다.

### V2 개선 방향

- V1에서 복잡했던 UI와 옵션 정리
- 분석 화면을 더 직관적으로 개선
- 볼린저밴드 단일 지표 중심 구조에서 다중 지표 기반 전략 엔진으로 확장
- Ichimoku Cloud, 이동평균선, Bollinger Bands, RSI 등 여러 지표 반영
- 리스크 관리와 현금 비중 제어 로직 추가
- Paper Trading 및 리밸런싱 시뮬레이션 구조 추가
- 프론트엔드와 백엔드 분석 로직의 책임 분리
- 테스트 가능한 전략 모듈 구조로 리팩터링

### V2 현재 상태

V2는 아직 개발 중입니다.

포트폴리오에서는 V1을 주 시연 버전으로 소개하고, V2는 V1의 한계를 개선하기 위한 리팩터링 및 확장 작업으로 남겨둡니다.

자세한 내용은 [`Mesugak_V2/README.md`](./Mesugak_V2/README.md)를 참고하세요.

---

## Repository Structure

```text
MesuGak/
├── Mesugak_V1/
│   ├── src/                  # React 기반 프론트엔드
│   ├── functions/            # Firebase Functions 및 분석 갱신 로직
│   ├── public/
│   ├── firebase.json
│   ├── firestore.rules
│   └── README.md
│
├── Mesugak_V2/
│   ├── frontend/             # 개선 중인 React/Vite 프론트엔드
│   ├── functions/            # 전략 엔진, 분석 작업, 리밸런싱 로직
│   ├── docs/                 # 구조 문서 및 작업 기록
│   └── README.md
│
└── README.md
```

---

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- CSS
- Tailwind CSS
- Recharts

### Backend / Infra

- Firebase Hosting
- Firestore
- Firebase Cloud Functions
- Firebase Scheduler
- Node.js
- Python

### Analysis

- Bollinger Bands
- `%b`
- Band Width
- Buy Signal Classification
- Ichimoku Cloud, V2
- Moving Average, V2
- RSI, V2
- Risk / Cash Ratio Control, V2
- Paper Trading / Rebalance Simulation, V2

---

## My Contribution

이 프로젝트에서 저는 MesuGak의 기획, 개발, 구조 개선을 진행했습니다.

V1에서는 볼린저밴드 기반 매수 신호 분석 서비스의 전체 흐름을 구현하고, 분석 결과를 웹 화면에서 확인할 수 있도록 구성했습니다.

주요 작업은 다음과 같습니다.

- 주식 분석 서비스 아이디어 기획
- 볼린저밴드 기반 매수 신호 분류 구조 설계
- 종목 상태를 Buy Signal / Normal / Squeeze로 구분하는 흐름 구현
- React 기반 웹 UI 구현
- Firestore에 분석 결과를 저장하고 조회하는 구조 구성
- 장마감 이후 매수 신호 종목을 `pending_orders`로 갱신하는 흐름 구현
- Firebase Hosting / Firestore / Cloud Functions 기반 배포 구조 구성
- V1에서 발생한 UI 복잡도와 옵션 난잡함을 바탕으로 V2 개선 방향 설계

---

## What I Learned

이 프로젝트를 통해 단순한 화면 구현을 넘어서, 데이터 분석 결과가 실제 서비스 화면과 운영 흐름으로 이어지는 구조를 경험했습니다.

특히 다음과 같은 내용을 학습했습니다.

- 기술적 지표 기반 분석 로직 설계
- Firestore를 활용한 분석 결과 저장 및 조회
- Firebase Cloud Functions를 이용한 자동화 작업 구성
- 서버리스 환경에서의 웹 서비스 배포
- 분석 로직과 프론트엔드 표시 로직의 역할 분리
- 초기 버전의 한계를 파악하고 차기 버전으로 개선하는 리팩터링 과정

---

## Getting Started

### V1 실행

```bash
cd Mesugak_V1
npm install
npm run dev
```

### V1 Firebase Functions 의존성 설치

```bash
cd Mesugak_V1/functions
npm install
```

### V1 배포 예시

Firestore 규칙/인덱스 배포:

```bash
firebase deploy --only firestore
```

Functions 배포:

```bash
firebase deploy --only functions:refreshPendingOrdersFromBuySignals
```

Hosting 배포:

```bash
npm run build
firebase deploy --only hosting
```

### V1 로컬 비상 갱신

Cloud Functions 스케줄이 실패한 경우, Python 스크립트로 동일한 갱신 로직을 수동 실행할 수 있습니다.

```bash
cd Mesugak_V1
python -m venv .venv
.venv\Scripts\pip install firebase-admin python-dotenv
.venv\Scripts\python functions/local_refresh_pending_orders.py --dry-run
```

실제 반영:

```bash
.venv\Scripts\python functions/local_refresh_pending_orders.py
```

마켓 지정:

```bash
.venv\Scripts\python functions/local_refresh_pending_orders.py --market US
```

---

## Development Status

- V1: 포트폴리오용 완성 버전
- V2: 개발 중

V2는 V1에서 발견한 UI 복잡도와 구조적 한계를 개선하기 위한 리팩터링 프로젝트입니다.

---

## Disclaimer

본 프로젝트는 개인 학습 및 포트폴리오 목적으로 제작한 주식 분석 서비스입니다.

제공되는 분석 결과는 투자 판단을 보조하기 위한 참고 정보이며, 실제 투자 결과를 보장하지 않습니다. 모든 투자 판단과 책임은 사용자 본인에게 있습니다.

---

## License

개인 포트폴리오 및 학습 목적의 프로젝트입니다.

필요 시 별도 라이선스 정책을 추가할 예정입니다.
