/* eslint-disable react-refresh/only-export-components */
import { useState } from 'react';
import { Shield, ExternalLink } from 'lucide-react';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { openConsentSettings } from './analytics.js';

import {
  LEGAL_PAGES_UPDATED_ON, CONTACT_EMAIL, legalPages, ANALYTICS_CONFIGURED, ADSENSE_REQUESTS_ENABLED, CERTIFIED_CMP_LIVE,
} from './content/legalCopy.js';
export { LEGAL_PAGES_UPDATED_ON, CONTACT_EMAIL, legalPages };

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
    if (!opened) setStatus('현재 광고·분석 기능이 비활성화되어 변경할 쿠키 설정이 없습니다.');
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
        <span>문서 수정일: {LEGAL_PAGES_UPDATED_ON}</span>
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

      {pageKey === 'privacy' && (
        <section className="legal-runtime-status" aria-label="현재 게시본의 기능 상태">
          <strong>현재 게시본의 기능 상태</strong>
          <p>{ANALYTICS_CONFIGURED ? 'Google Analytics 측정 ID가 설정되어 있습니다.' : 'Google Analytics 측정 ID가 설정되지 않아 Analytics 태그를 로드하지 않습니다.'}</p>
          <p>{ADSENSE_REQUESTS_ENABLED ? 'AdSense 요청 게이트가 켜져 있습니다.' : 'AdSense 요청은 현재 비활성화되어 광고 요청을 보내지 않습니다.'}</p>
          <p>{CERTIFIED_CMP_LIVE ? 'Google 인증 CMP가 게시된 상태입니다.' : 'Google 인증 CMP는 아직 게시 확인 전이며, 동의 설정 버튼은 현재 기능 상태를 안내합니다.'}</p>
        </section>
      )}

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
