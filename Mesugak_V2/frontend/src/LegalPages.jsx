/* eslint-disable react-refresh/only-export-components */
import { useState } from 'react';
import { Shield, ExternalLink } from 'lucide-react';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { openConsentSettings } from './analytics.js';

export const LAST_LEGAL_REVIEWED = '2026-08-31';
export const CONTACT_EMAIL = 'or_not_official@naver.com';

export const legalPages = {
  privacy: {
    slug: 'privacy',
    navLabel: '개인정보처리방침',
    title: '개인정보처리방침',
    kicker: `${BRAND_SHORT} · Privacy`,
    summary:
      `${BRAND_FULL}(이하 "${BRAND_SHORT}")에서 어떤 개인정보를 처리하고, 이용자가 어떻게 권리를 행사할 수 있는지 안내합니다.`,
    notice:
      '공개 분석은 로그인 없이 이용할 수 있습니다. Google Analytics와 광고 기능은 운영 설정과 이용자의 동의 상태에 따라 작동합니다.',
    sections: [
      {
        title: '1. 처리하는 개인정보',
        body: [
          'Google 로그인 사용 시 Firebase Authentication을 통해 표시 이름, 이메일 주소, 프로필 이미지, 사용자 식별자(uid)가 처리될 수 있습니다.',
          '관리자 권한 확인과 사용자별 화면 설정을 위해 Firebase Authentication 및 Firestore를 사용할 수 있습니다.',
          'Google Analytics가 활성화되면 방문 페이지, 접속 기기와 브라우저, 대략적인 지역, 서비스 이용 이벤트가 통계 목적으로 처리될 수 있습니다. Analytics Measurement ID가 설정되지 않았거나 필요한 동의가 없으면 Analytics 태그를 로드하지 않습니다.',
          'Google AdSense가 활성화되면 Google 및 광고 기술 제공업체가 광고 제공·측정에 쿠키 또는 유사 기술을 사용할 수 있습니다. 실제 광고와 Analytics는 관련 설정과 동의 상태가 갖춰진 경우에만 로드합니다.',
        ],
      },
      {
        title: '2. 이용 목적',
        body: [
          '로그인 유지, 관리자 권한 확인, 사용자별 화면 설정, 오류 대응과 서비스 품질 개선을 위해 정보를 사용합니다.',
          '투자 성향을 추정하거나 특정 종목 매매를 유도하기 위한 맞춤형 투자자문 목적으로 개인정보를 사용하지 않습니다.',
        ],
      },
      {
        title: '3. 제3자 제공',
        body: [
          '서비스는 이용자의 개인정보를 판매하지 않으며, 이용자의 별도 동의가 있거나 법령에 근거가 있는 경우를 제외하고 제3자에게 제공하지 않습니다.',
          '서비스 운영을 맡긴 업체가 지시에 따라 정보를 처리하는 경우는 아래의 처리위탁 항목에서 설명합니다.',
        ],
      },
      {
        title: '4. 보유 기간과 파기',
        body: [
          '로그인 정보와 사용자별 설정은 계정 및 서비스 운영에 필요한 기간 동안 보관합니다. 삭제 요청을 처리하거나 목적이 끝나면 관계 법령상 보관 의무가 있는 경우를 제외하고 지체 없이 삭제합니다.',
          'Analytics 및 광고 관련 정보의 보관 기간은 실제로 활성화한 Google 서비스의 설정과 정책을 따릅니다.',
          '전자적 정보는 복구하기 어려운 방법으로 삭제하고, 별도 법령에 따라 보관해야 하는 정보가 생기면 다른 정보와 분리해 보관합니다.',
        ],
      },
      {
        title: '5. 처리위탁 및 외부 서비스',
        body: [
          'Google LLC의 Firebase Authentication, Firestore 및 Hosting을 이용해 로그인 인증, 데이터 저장과 웹 호스팅 업무를 처리합니다. 관련 정보는 서비스 제공 목적이 끝나거나 위탁 관계가 종료될 때까지 처리될 수 있습니다.',
          'Google Analytics는 이용 통계 측정에, Google AdSense와 Google CMP는 광고 제공 및 동의 관리에 사용할 수 있습니다. 두 기능은 실제 운영 설정과 동의 상태에 따라 작동합니다.',
          '한국투자증권 KIS 모의투자 API는 운영자의 관리자 전용 모의계좌를 확인하는 데만 사용합니다. 일반 이용자의 증권계좌를 연결하거나 금융정보를 수집하지 않습니다.',
          'Analytics 또는 광고를 실제로 활성화하면서 개인정보의 국외 이전이 발생하는 경우에는 이전 항목·국가·시기와 방법·수령자·목적·보유기간·거부 방법을 관련 법령에 따라 추가로 알리고 필요한 동의를 받습니다.',
        ],
      },
      {
        title: '6. 이용자의 권리와 문의',
        body: [
          `이용자는 자신의 개인정보 열람, 정정, 삭제와 처리 정지를 요청할 수 있습니다. 개인정보 관련 문의와 요청은 ${CONTACT_EMAIL}으로 보내 주세요.`,
          '요청자의 본인 여부를 확인한 뒤 관련 법령에서 정한 범위와 절차에 따라 처리합니다.',
          '만 14세 미만 이용자에 관한 요청은 법정대리인이 행사할 수 있습니다. 공개 분석은 로그인 없이 이용할 수 있습니다.',
          `개인정보 보호 업무 담당: ${BRAND_FULL} 운영자 · ${CONTACT_EMAIL}`,
        ],
      },
      {
        title: '7. 쿠키와 동의 변경',
        body: [
          'Google Analytics와 AdSense가 활성화되면 Google 및 제3자 광고 제공업체가 쿠키 또는 유사 기술을 이용해 방문·광고 정보를 처리할 수 있습니다. Google 광고는 이전의 이 사이트 또는 다른 사이트 방문 정보를 바탕으로 표시될 수 있습니다.',
          '사용자는 아래의 개인정보·쿠키 설정에서 광고 및 분석 목적의 선택을 다시 확인하거나 변경할 수 있으며, Google 광고 설정에서도 개인 맞춤 광고를 관리할 수 있습니다. 동의하지 않아도 공개 분석 화면은 이용할 수 있습니다.',
        ],
      },
    ],
    sources: [
      { label: '개인정보 보호법 제30조', href: 'https://law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1020398435' },
      { label: 'Google 개인정보처리방침', href: 'https://policies.google.com/privacy?hl=ko' },
      { label: 'Google AdSense 개인정보 보호 필수 콘텐츠', href: 'https://support.google.com/adsense/answer/1348695?hl=ko' },
      { label: 'Google 광고 설정', href: 'https://adssettings.google.com/' },
    ],
  },
  terms: {
    slug: 'terms',
    navLabel: '이용약관',
    title: '이용약관',
    kicker: `${BRAND_SHORT} · Terms`,
    summary:
      `이 약관은 ${BRAND_FULL}(이하 "${BRAND_SHORT}")의 공개 분석 정보를 이용할 때 알아야 할 기본 조건을 설명합니다.`,
    notice:
      '이 서비스는 최근 거래일의 확정 일봉을 바탕으로 기술지표를 설명하는 비실시간 학습 서비스입니다. 개인별 종목 추천이나 주문 대행은 제공하지 않습니다.',
    sections: [
      {
        title: '1. 서비스 성격',
        body: [
          `${BRAND_SHORT}은 종목별 기술지표가 어떤 상태를 나타내는지 점수와 해설로 알려주는 학습 서비스입니다.`,
          '공개 분석은 누구나 무료로 볼 수 있으며, 개인별 투자 상담·포트폴리오 진단·주문 대행은 제공하지 않습니다.',
          '공개 화면의 점수, 등급과 상태 해설은 실제 매수·매도·보유 권유가 아닙니다.',
          '실제 투자 여부는 이용자가 스스로 판단해야 하며, 필요한 경우 등록된 전문가에게 상담할 수 있습니다.',
        ],
      },
      {
        title: '2. 분석 기준과 갱신',
        body: [
          '공개 분석은 계산 시점에 수집이 끝난 가장 최근 거래일의 확정 일봉을 기준으로 합니다. 장중 시세나 실시간 현재가를 반영하지 않습니다.',
          '화면에는 종목명·종목코드와 자체 계산한 종합점수·등급·문장형 상태를 표시하며, 각 종목의 분석 기준일을 함께 안내합니다.',
          '휴장일, 데이터 수집 시점 또는 공급자의 사후 정정에 따라 갱신 시점과 분석 결과가 달라질 수 있습니다.',
        ],
      },
      {
        title: '3. 올바른 이용',
        body: [
          '서비스 화면이나 분석 결과를 무단으로 대량 수집·복제·재배포하거나, 서비스 및 데이터 제공자의 이용 조건을 우회하는 방식으로 사용할 수 없습니다.',
          `${BRAND_SHORT}의 분석 결과를 확정 수익, 추천 종목, 보장형 신호처럼 바꾸어 홍보하거나 판매해서는 안 됩니다.`,
          '광고가 활성화된 경우 광고 클릭을 유도하거나 인위적인 노출·클릭을 발생시키는 행위는 금지됩니다.',
        ],
      },
      {
        title: '4. 서비스 이용과 책임',
        body: [
          '기술지표는 과거 가격 흐름을 계산해 현재 상태를 살펴보는 도구입니다. 자체 점수와 해설은 미래 가격이나 수익을 보장하지 않습니다.',
          '점검, 장애, 데이터 수집 실패 또는 정정이 발생하면 일부 분석의 공개가 늦어지거나 결과가 다시 계산될 수 있습니다.',
          '이 정보를 실제 투자에 활용할지는 이용자가 스스로 판단해야 합니다.',
        ],
      },
      {
        title: '5. 변경과 문의',
        body: [
          '서비스 구조, 표시 항목과 약관은 운영상 필요에 따라 변경될 수 있으며 중요한 변경은 이 페이지에 반영합니다.',
          `서비스 이용과 약관에 관한 문의는 ${CONTACT_EMAIL}으로 보내 주세요.`,
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
      '화면의 점수와 해설은 기술지표를 공부하기 위한 참고자료입니다. 특정 종목의 거래를 권유하거나 투자 결과를 보장하지 않습니다.',
    notice:
      '공개 점수와 상태 해설은 최근 거래일의 확정 일봉에서 나타난 기술적 조건을 이해하기 위한 학습 자료입니다.',
    sections: [
      {
        title: '투자자문이 아닙니다',
        body: [
          `${BRAND_SHORT}은 투자자문업, 투자일임업, 금융상품 중개, 주문대행 서비스를 제공하지 않습니다.`,
          '화면의 라벨은 내부 기술지표 조건을 설명하는 표현이며, 특정 종목의 매수·매도·보유 권유로 해석되어서는 안 됩니다.',
          '이 서비스는 유료 구독, 개인별 포트폴리오 진단, 종목 추천이나 주문 연동 기능을 제공하지 않습니다.',
        ],
      },
      {
        title: '성과 보장 없음',
        body: [
          '관리자 전용 화면에서 확인하는 백테스트와 모의투자 기록은 실제 계좌 성과가 아닙니다.',
          '과거 데이터나 모의 환경에서의 성과는 미래 수익 또는 손실 회피를 보장하지 않습니다.',
        ],
      },
      {
        title: '데이터 책임 제한',
        body: [
          '공공데이터의 정정, 수집 오류나 계산 방식 변경에 따라 분석 결과가 달라질 수 있습니다.',
          '이 정보를 사용해 발생하는 투자 판단과 결과에 대한 책임은 이용자 본인에게 있습니다.',
        ],
      },
      {
        title: '광고와 후원',
        body: [
          `광고가 표시되더라도 광고주는 ${BRAND_SHORT}의 분석 결과를 보증하거나 특정 종목 판단에 관여하지 않습니다.`,
          '광고 클릭을 요구하거나 유도하지 않으며, 광고와 본문 콘텐츠는 명확히 구분되어야 합니다.',
          '후원은 사이트 운영을 응원하기 위한 자발적 지원이며, 후원 여부와 관계없이 모든 이용자에게 동일한 공개 정보를 제공합니다. 후원자에게 개별 투자상담, 추가 분석 또는 우선 열람을 제공하지 않습니다.',
        ],
      },
    ],
  },
  data: {
    slug: 'data',
    navLabel: '분석 데이터 안내',
    title: '분석 데이터 안내',
    kicker: `${BRAND_SHORT} · Data Use`,
    summary:
      '공개 화면의 분석이 어떤 자료를 기준으로 계산되고, 무엇을 보여주는지 쉽게 설명합니다.',
    notice:
      '공개 결과는 실시간 시세가 아니라 최근 거래일의 확정 일봉으로 계산합니다. 종목별 분석 기준일도 함께 확인해 주세요.',
    sections: [
      {
        title: '1. 무엇을 보여주나요?',
        body: [
          '공개 화면에는 종목명과 종목코드, 자체 계산한 종합점수와 등급, 기술적 조건을 풀어 쓴 해설을 표시합니다.',
          '점수와 문장은 여러 기술지표 조건을 종합해 만든 교육용 분석 결과이며, 원시 API 응답을 그대로 보여주는 값이 아닙니다.',
        ],
      },
      {
        title: '2. 어떤 시점을 기준으로 하나요?',
        body: [
          '서버가 금융위원회 주식시세정보 API에서 제공받은 가장 최근 거래일의 확정 일봉을 분석합니다.',
          '당일 장중 가격이나 실시간 현재가는 반영하지 않습니다. 주말과 휴장일에는 직전 거래일 자료가 기준이 됩니다.',
          '종목별 화면에 표시되는 분석 기준일이 실제 계산에 사용된 시점입니다.',
        ],
      },
      {
        title: '3. 무엇을 공개하지 않나요?',
        body: [
          '현재가, 시가·고가·저가·종가·거래량, 가격 차트, 원시 API 응답은 공개하지 않습니다.',
          'RSI, 이동평균, 볼린저 밴드 같은 개별 지표의 원시 수치도 일반 공개 화면에 표시하지 않습니다.',
        ],
      },
      {
        title: '4. 결과가 바뀔 수 있나요?',
        body: [
          '데이터 공급자의 정정, 수집 실패 복구 또는 분석 로직 개선이 있으면 같은 기준일의 결과도 다시 계산될 수 있습니다.',
          '분석 결과는 기술적 조건을 학습하기 위한 참고 정보이며, 실제 투자 판단을 대신하지 않습니다.',
        ],
      },
    ],
    sources: [
      { label: '금융위원회 주식시세정보', href: 'https://www.data.go.kr/data/15094808/openapi.do' },
      { label: '금융위원회 지수시세정보', href: 'https://www.data.go.kr/data/15094807/openapi.do' },
    ],
  },
};

const pageOrder = ['terms', 'privacy', 'data'];

export function normalizeLegalRoute(hash) {
  const value = String(hash || '').replace(/^#\/?/, '').replace(/^\/+|\/+$/g, '').replace(/^legal\//, '');
  if (value === 'data-policy' || value === 'data-use') return 'data';
  return legalPages[value] ? value : '';
}

function legalHref(slug) {
  return `/${slug}`;
}

export function ConsentSettingsButton({ children = '개인정보·쿠키 설정', className = '' }) {
  const [status, setStatus] = useState('');
  const handleClick = async () => {
    setStatus('동의 설정을 여는 중…');
    const opened = await openConsentSettings();
    if (!opened) setStatus('동의 설정을 아직 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
    else setStatus('');
  };

  return (
    <button type="button" className={className} onClick={handleClick} aria-live="polite">
      {status || children}
    </button>
  );
}

export function ComplianceDock() {
  return (
    <aside className="compliance-dock" aria-label="법적 고지">
      <div>
        <strong>기술지표 학습 정보</strong>
        <span>최근 거래일 확정 일봉 기준 · 비실시간 · 투자 권유 아님</span>
      </div>
      <nav aria-label="법적 문서">
        {pageOrder.map((key) => (
          <a key={key} href={legalHref(legalPages[key].slug)}>
            {legalPages[key].navLabel}
          </a>
        ))}
        <ConsentSettingsButton className="compliance-settings" />
      </nav>
    </aside>
  );
}

export function LegalPage({ pageKey = 'disclaimer' }) {
  const page = legalPages[pageKey] || legalPages.disclaimer;

  return (
    <main className="legal-page theme-light">
      <section className="legal-hero">
        <a href="/" className="legal-home">← 분석 화면으로 돌아가기</a>
        <p>{page.kicker}</p>
        <h1>{page.title}</h1>
        <strong>{page.summary}</strong>
        <span>마지막 검토일: {LAST_LEGAL_REVIEWED}</span>
      </section>

      <nav className="legal-tabs" aria-label="법적 문서 이동">
        {pageOrder.map((key) => (
          <a key={key} href={legalHref(legalPages[key].slug)} className={key === pageKey ? 'active' : ''}>
            {legalPages[key].navLabel}
          </a>
        ))}
      </nav>

      <section className="legal-notice">
        <Shield size={18} />
        <p>{page.notice}</p>
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

      <section className="legal-actions" aria-label="개인정보 설정 및 문의">
        <ConsentSettingsButton>개인정보·쿠키 설정 열기</ConsentSettingsButton>
        <a href={`mailto:${CONTACT_EMAIL}`}>개인정보 문의: {CONTACT_EMAIL}</a>
      </section>
    </main>
  );
}


