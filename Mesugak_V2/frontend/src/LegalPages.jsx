/* eslint-disable react-refresh/only-export-components */
import { Shield, AlertTriangle, ExternalLink } from 'lucide-react';
import { BRAND_FULL, BRAND_SHORT } from './brand';

export const LAST_LEGAL_REVIEWED = '2026-07-13';

export const legalPages = {
  privacy: {
    slug: 'privacy',
    navLabel: '개인정보처리방침',
    title: '개인정보처리방침',
    kicker: `${BRAND_SHORT} · Privacy`,
    summary:
      `${BRAND_FULL}(이하 "${BRAND_SHORT}")은 기술지표 학습과 모의투자 실험을 위한 서비스입니다. 로그인, Firestore 동기화, 향후 광고 도입 가능성을 기준으로 개인정보 처리 범위를 투명하게 고지합니다.`,
    sections: [
      {
        title: '1. 수집하는 정보',
        body: [
          'Google 로그인 사용 시 Firebase Authentication을 통해 표시 이름, 이메일 주소, 프로필 이미지, 사용자 식별자(uid)가 처리될 수 있습니다.',
          'Firestore에는 사용자가 직접 만든 설정, 모의투자 스냅샷, 가상 체결 로그, 분석 조회에 필요한 서비스 데이터가 저장될 수 있습니다.',
          '현재 앱에는 실제 AdSense 광고 스크립트를 연결하지 않았습니다. 향후 광고를 활성화하면 Google 및 제3자 광고 사업자가 쿠키 또는 유사 기술을 사용할 수 있습니다.',
        ],
      },
      {
        title: '2. 이용 목적',
        body: [
          '로그인 유지, 사용자별 화면 설정, 모의투자 성과 확인, 오류 대응, 서비스 품질 개선을 위해 정보를 사용합니다.',
          '투자 성향을 추정하거나 특정 종목 매매를 유도하기 위한 맞춤형 투자자문 목적으로 개인정보를 사용하지 않습니다.',
        ],
      },
      {
        title: '3. 제3자 서비스',
        body: [
          'Firebase Authentication과 Firestore는 Google Firebase 인프라를 사용합니다.',
          '향후 Google AdSense를 도입하는 경우, Google 광고 쿠키와 개인 맞춤 광고 선택 해제 방법을 이 방침에 추가로 반영해야 합니다.',
          '한국투자증권 OpenAPI는 운영자의 모의투자 계좌 실험에만 사용하며, 일반 이용자의 증권계좌 연결 기능으로 제공하지 않습니다.',
        ],
      },
      {
        title: '4. 보관 및 삭제',
        body: [
          '서비스 운영에 필요한 기간 동안 데이터를 보관하며, 테스트·모의투자 데이터는 운영상 필요가 없어지면 삭제할 수 있습니다.',
          '사용자는 로그인 정보와 관련 데이터 삭제를 요청할 수 있습니다. 실제 운영 전에는 연락처와 처리 절차를 별도로 고지해야 합니다.',
        ],
      },
      {
        title: '5. 광고 쿠키 고지',
        body: [
          'Google AdSense 정책상 개인정보처리방침에는 Google 및 제3자 공급업체가 쿠키를 사용해 이전 방문 정보를 바탕으로 광고를 게재할 수 있다는 사실과 개인 맞춤 광고 선택 해제 방법이 포함되어야 합니다.',
          '현재는 실제 광고 코드와 공개 광고 자리를 모두 비활성화합니다. 데이터 사용 권리, 개인정보·쿠키 고지, 동의 요건, AdSense 승인 절차를 모두 확인한 뒤에만 별도 배포로 연결합니다.',
        ],
      },
    ],
  },
  terms: {
    slug: 'terms',
    navLabel: '이용약관',
    title: '이용약관',
    kicker: `${BRAND_SHORT} · Terms`,
    summary:
      `이 약관은 ${BRAND_FULL}(이하 "${BRAND_SHORT}")을 기술지표 연구·교육·모의투자 실험 도구로 사용할 때의 기본 조건을 설명합니다.`,
    sections: [
      {
        title: '1. 서비스 성격',
        body: [
          `${BRAND_SHORT}은 차트와 기술지표를 학습하고 전략 아이디어를 검토하기 위한 연구용 도구입니다.`,
          '서비스 내 점수, 라벨, 모의 주문, 모의 체결 기록은 실제 매수·매도·보유 권유가 아닙니다.',
          '사용자는 모든 투자 판단을 스스로 해야 하며, 필요한 경우 등록된 전문가의 자문을 받아야 합니다.',
        ],
      },
      {
        title: '2. 금지되는 사용',
        body: [
          '서비스 화면이나 데이터를 무단 복제·재배포하거나, 데이터 제공자의 약관을 우회하는 방식으로 사용할 수 없습니다.',
          `${BRAND_SHORT}의 분석 결과를 확정 수익, 추천 종목, 보장형 신호처럼 홍보하거나 제3자에게 투자 권유 자료로 판매해서는 안 됩니다.`,
          '광고가 활성화된 경우 광고 클릭을 유도하거나 인위적인 노출·클릭을 발생시키는 행위는 금지됩니다.',
        ],
      },
      {
        title: '3. 데이터와 지연',
        body: [
          '시장 데이터는 출처별 지연, 오류, 누락, 정정, 이용 제한이 있을 수 있습니다.',
          '공개·상업 서비스에서는 KRX, 해외거래소, 데이터 공급자, 증권사 API의 정보이용계약 또는 허가가 별도로 필요할 수 있습니다.',
        ],
      },
      {
        title: '4. 모의투자',
        body: [
          '모의투자 결과는 실제 체결, 세금, 수수료, 슬리피지, 호가 공백, 거래 제한을 완전히 반영하지 못할 수 있습니다.',
          '실험 수익률은 과거 또는 모의 환경의 결과이며 미래 수익을 보장하지 않습니다.',
        ],
      },
      {
        title: '5. 변경',
        body: [
          '서비스 구조, 데이터 소스, 표시 항목, 약관과 정책은 운영 필요와 법적 검토 결과에 따라 변경될 수 있습니다.',
        ],
      },
    ],
  },
  disclaimer: {
    slug: 'disclaimer',
    navLabel: '면책고지',
    title: '면책고지',
    kicker: `${BRAND_SHORT} · Disclaimer`,
    summary:
      `${BRAND_SHORT}의 모든 분석은 기술지표 연구와 교육용 참고 정보입니다. 실제 투자 결과를 보장하지 않고, 특정 종목 거래를 권유하지 않습니다.`,
    sections: [
      {
        title: '투자자문이 아닙니다',
        body: [
          `${BRAND_SHORT}은 투자자문업, 투자일임업, 금융상품 중개, 주문대행 서비스를 제공하지 않습니다.`,
          '화면의 라벨은 내부 기술지표 조건을 설명하는 표현이며, 특정 종목의 매수·매도·보유 권유로 해석되어서는 안 됩니다.',
          '유료 구독, 개인별 포트폴리오 진단, 종목 추천, 주문 연동 기능을 제공하려면 별도의 법률 검토와 인허가·신고 요건 확인이 필요합니다.',
        ],
      },
      {
        title: '성과 보장 없음',
        body: [
          '점수, 백테스트, 모의투자, 가상 계좌 스냅샷은 연구용 실험 결과입니다.',
          '과거 데이터나 모의 환경에서의 성과는 미래 수익 또는 손실 회피를 보장하지 않습니다.',
        ],
      },
      {
        title: '데이터 책임 제한',
        body: [
          '시장 데이터와 분석 결과에는 오류, 지연, 누락, 계산 기준 차이가 있을 수 있습니다.',
          '이 정보를 사용해 발생하는 투자 판단과 결과에 대한 책임은 이용자 본인에게 있습니다.',
        ],
      },
      {
        title: '광고와 후원',
        body: [
          `광고가 표시되더라도 광고주는 ${BRAND_SHORT}의 분석 결과를 보증하거나 특정 종목 판단에 관여하지 않습니다.`,
          '광고 클릭을 요구하거나 유도하지 않으며, 광고와 본문 콘텐츠는 명확히 구분되어야 합니다.',
        ],
      },
    ],
  },
  data: {
    slug: 'data',
    navLabel: '데이터 사용 고지',
    title: '데이터 사용 고지',
    kicker: `${BRAND_SHORT} · Data Use`,
    summary:
      '현재 코드에서 확인되는 데이터 경로와 공식 정책을 기준으로, 공개·광고형 서비스에서 안전하게 사용할 수 있는 범위를 보수적으로 정리했습니다.',
    sections: [
      {
        title: '현재 코드의 데이터 경로',
        body: [
          '국내/해외 종목 목록과 OHLCV는 FinanceDataReader를 통해 불러오며, 국내 재무 참고값은 NAVER/FINSTATE 경로를 사용합니다.',
          '미국 S&P 500·Nasdaq-100 구성 종목 필터는 Wikipedia 표를 읽어 구성합니다.',
          '모의투자 잔고와 가상 체결 기록은 Firestore와 운영자의 한국투자증권 모의투자 API 연동 결과를 표시합니다.',
        ],
      },
      {
        title: '공개·상업 이용 판단',
        body: [
          'KRX 공식 법적고지는 시장정보와 서비스의 무단 복제·전송·출판·배포·방송 및 제3자 배포를 제한합니다.',
          'KIS Developers 제휴 안내는 시세 API를 제3자 서비스 화면에 제공하려면 KRX 또는 해외거래소와의 정보이용계약 확인이 필요하다고 안내합니다.',
          '따라서 현재 확인된 범위만으로는 KRX/KIS/거래소 시세 데이터를 공개 광고형 서비스에 재배포해도 된다고 단정할 수 없습니다.',
        ],
      },
      {
        title: '현재 운영 결정',
        body: [
          '실제 AdSense 광고 코드와 공개 광고 자리를 모두 비활성화합니다. 권리와 광고 정책 검토가 끝난 별도 배포에서만 활성화를 검토합니다.',
          '프로덕션 공개 화면은 실데이터를 불러오지 않는 교육 안내 상태이며, Firestore 규칙도 가격 없는 공개 분석 피드를 관리자 전용으로 잠급니다. 공개 전환에는 서면 이용권 확인, 승인 근거 보관, 명시적 환경 설정, 규칙 배포가 모두 필요합니다.',
          '공개 배포 전에는 데이터 공급자별 이용계약, 출처 표시, 지연 데이터 여부, 재배포 허용 범위를 문서로 확보해야 합니다.',
          '권리가 확인되지 않은 원시 시세·차트 데이터는 공개 상업 화면에서 노출하지 않는 것을 기본값으로 둡니다.',
        ],
      },
      {
        title: '공개 전 체크리스트',
        body: [
          'KRX/Koscom 또는 해당 데이터 공급자와 정보이용계약 필요 여부 확인',
          '해외 시세 데이터 공급자의 상업적 재표시·재배포 허용 범위 확인',
          'Wikipedia 데이터 재사용 시 라이선스와 출처 표시 방식 확인',
          'AdSense 승인, ads.txt, 개인정보처리방침의 광고 쿠키 문구 반영',
          '유료 구독 또는 개인별 종목 후보 제공 시 유사투자자문업·투자자문업 관련 법률 검토',
        ],
      },
    ],
    sources: [
      { label: 'KRX 법적고지', href: 'https://info.krx.co.kr/contents/KRX/06/06070200/KRX06070200.jsp' },
      { label: 'KIS Developers 제휴안내', href: 'https://apiportal.koreainvestment.com/provider-info' },
      { label: 'Google AdSense Program policies', href: 'https://support.google.com/adsense/answer/48182' },
      { label: 'Google AdSense Required content', href: 'https://support.google.com/adsense/answer/1348695' },
      { label: 'Wikimedia Foundation Terms of Use', href: 'https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use' },
    ],
  },
};

const pageOrder = ['privacy', 'terms', 'disclaimer', 'data'];

export function normalizeLegalRoute(hash) {
  const value = String(hash || '').replace(/^#\/?/, '').replace(/^legal\//, '');
  if (value === 'data-policy' || value === 'data-use') return 'data';
  return legalPages[value] ? value : '';
}

export function ComplianceDock() {
  return (
    <aside className="compliance-dock" aria-label="법적 고지">
      <div>
        <strong>교육·연구용</strong>
        <span>매수·매도 권유 아님 · 실제 수익 보장 없음 · 광고는 권리 확인 후 활성화</span>
      </div>
      <nav aria-label="법적 문서">
        {pageOrder.map((key) => (
          <a key={key} href={`#/${legalPages[key].slug}`}>
            {legalPages[key].navLabel}
          </a>
        ))}
      </nav>
    </aside>
  );
}

export function LegalPage({ pageKey = 'disclaimer' }) {
  const page = legalPages[pageKey] || legalPages.disclaimer;

  return (
    <main className="legal-page theme-light">
      <section className="legal-hero">
        <a href="#/" className="legal-home">← 연구실로 돌아가기</a>
        <p>{page.kicker}</p>
        <h1>{page.title}</h1>
        <strong>{page.summary}</strong>
        <span>마지막 검토일: {LAST_LEGAL_REVIEWED}</span>
      </section>

      <nav className="legal-tabs" aria-label="법적 문서 이동">
        {pageOrder.map((key) => (
          <a key={key} href={`#/${legalPages[key].slug}`} className={key === pageKey ? 'active' : ''}>
            {legalPages[key].navLabel}
          </a>
        ))}
      </nav>

      <section className="legal-warning">
        <AlertTriangle size={18} />
        <p>
          이 문서는 서비스 운영을 위한 기본 고지 초안입니다. 공개 유료 서비스, 광고 수익화, 종목 후보 제공,
          주문 연동을 시작하기 전에는 실제 사업 형태에 맞춘 법률 검토가 필요합니다.
        </p>
      </section>

      <div className="legal-sections">
        {page.sections.map((section) => (
          <article key={section.title} className="legal-card">
            <div className="legal-card-title">
              <Shield size={17} />
              <h2>{section.title}</h2>
            </div>
            {section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </article>
        ))}
      </div>

      {page.sources && (
        <section className="legal-card legal-sources">
          <div className="legal-card-title">
            <ExternalLink size={17} />
            <h2>확인한 공식 자료</h2>
          </div>
          <ul>
            {page.sources.map((source) => (
              <li key={source.href}>
                <a href={source.href} target="_blank" rel="noreferrer">{source.label}</a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}


