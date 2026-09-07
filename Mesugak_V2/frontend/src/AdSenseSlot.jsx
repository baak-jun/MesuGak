import { useEffect, useRef } from 'react';
import { monetizationGate } from './monetizationGate';

const gate = monetizationGate(import.meta.env);
const scriptSelector = 'script[data-mesugak-adsense="loader"]';

function loadAdSenseScript() {
  const existing = document.querySelector(scriptSelector);
  if (existing?.dataset.loaded === 'true') return Promise.resolve();
  if (existing?.dataset.loading === 'true') {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', reject, { once: true });
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.dataset.mesugakAdsense = 'loader';
    script.dataset.loading = 'true';
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(gate.clientId)}`;
    script.addEventListener('load', () => {
      script.dataset.loaded = 'true';
      delete script.dataset.loading;
      resolve();
    }, { once: true });
    script.addEventListener('error', reject, { once: true });
    document.head.appendChild(script);
  });
}

function waitForConsentData() {
  if (typeof window === 'undefined') return Promise.resolve(false);
  window.googlefc = window.googlefc || {};
  window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];
  if (typeof window.googlefc.getGoogleConsentModeValues === 'function') return Promise.resolve(true);

  return new Promise((resolve) => {
    let settled = false;
    let timeoutId;
    const settle = (ready) => {
      if (settled) return;
      settled = true;
      if (timeoutId) window.clearTimeout(timeoutId);
      resolve(ready);
    };
    window.googlefc.callbackQueue.push({
      CONSENT_MODE_DATA_READY: () => settle(true),
    });
    timeoutId = window.setTimeout(() => settle(false), 5000);
  });
}

export function AdSenseSlot({ title = '광고', placement = 'body', compact = false, className = '' }) {
  const elementRef = useRef(null);
  const requestedRef = useRef(false);
  const supportedPlacement = placement === 'learning' || placement === 'analysis';
  const placementEnabled = placement === 'learning' || gate.analysisAdsRequested;
  const slotId = supportedPlacement ? gate.slotIds[placement] : '';

  useEffect(() => {
    let cancelled = false;
    if (!supportedPlacement || !placementEnabled || !gate.adsensePlacementApproved || requestedRef.current) return undefined;

    void waitForConsentData().then((consentReady) => {
      if (!consentReady) return null;
      return loadAdSenseScript().then(() => {
        if (cancelled || requestedRef.current || !elementRef.current) return;
        requestedRef.current = true;
        try {
          window.adsbygoogle = window.adsbygoogle || [];
          window.adsbygoogle.push({});
        } catch {
          // Google can reject a request for account, fill, or policy reasons.
          // Keep the page usable and rely on the AdSense console for diagnostics.
        }
        return null;
      });
    }).catch(() => {
      // Network/CSP failures must not expose a substitute or encourage clicks.
    });

    return () => { cancelled = true; };
  }, [placementEnabled, supportedPlacement]);

  if (!supportedPlacement || !placementEnabled) return null;

  if (!gate.adsensePlacementApproved) {
    if (!gate.adsensePreviewEnabled) return null;
    return (
      <aside className={`ad-slot adsense-slot ad-slot-preview ${compact ? 'compact' : ''} ${className}`.trim()} aria-label={`${title} 미리보기`}>
        <span>광고 공간</span>
        <strong>{title}</strong>
        <small>AdSense 승인 후 실제 광고가 표시됩니다.</small>
      </aside>
    );
  }

  return (
    <aside className={`ad-slot adsense-slot adsense-slot-${placement} ${compact ? 'compact' : ''} ${className}`.trim()} aria-label={title}>
      <span>광고</span>
      <ins
        ref={elementRef}
        className="adsbygoogle skeleton-glow"
        style={{ display: 'block', minHeight: '90px', borderRadius: '12px' }}
        data-ad-client={gate.clientId}
        data-ad-slot={slotId}
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </aside>
  );
}
