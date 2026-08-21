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

export function AdSenseSlot({ title = '광고', compact = false, className = '' }) {
  const elementRef = useRef(null);
  const requestedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    if (!gate.adsensePlacementApproved || requestedRef.current) return undefined;

    void loadAdSenseScript().then(() => {
      if (cancelled || requestedRef.current || !elementRef.current) return;
      requestedRef.current = true;
      try {
        window.adsbygoogle = window.adsbygoogle || [];
        window.adsbygoogle.push({});
      } catch {
        // Google can reject a request for account, fill, or policy reasons.
        // Keep the page usable and rely on the AdSense console for diagnostics.
      }
    }).catch(() => {
      // Network/CSP failures must not expose a substitute or encourage clicks.
    });

    return () => { cancelled = true; };
  }, []);

  if (!gate.adsensePlacementApproved) return null;

  return (
    <aside className={`ad-slot adsense-slot ${compact ? 'compact' : ''} ${className}`.trim()} aria-label={title}>
      <span>광고</span>
      <ins
        ref={elementRef}
        className="adsbygoogle skeleton-glow"
        style={{ display: 'block', minHeight: '90px', borderRadius: '12px' }}
        data-ad-client={gate.clientId}
        data-ad-slot={gate.slotId}
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </aside>
  );
}