import { useEffect, useRef } from 'react';
import { monetizationGate } from './monetizationGate';
import { loadAdSenseScript } from './adsenseClient.js';

const gate = monetizationGate(import.meta.env);

export function AdSenseSlot({ title = '광고', placement = 'body', compact = false, className = '' }) {
  const elementRef = useRef(null);
  const requestedRef = useRef(false);
  const supportedPlacement = placement === 'learning' || placement === 'analysis';
  const placementEnabled = placement === 'learning' || gate.analysisAdsRequested;
  const slotId = supportedPlacement ? gate.slotIds[placement] : '';

  useEffect(() => {
    let cancelled = false;
    if (!supportedPlacement || !placementEnabled || !gate.adsensePlacementApproved || requestedRef.current) return undefined;

    void loadAdSenseScript(gate.clientId).then(() => {
      if (cancelled || requestedRef.current || !elementRef.current) return;
      requestedRef.current = true;
      try {
        // Google CMP is loaded by the publisher tag and applies the visitor's
        // regional consent to ad serving. Waiting for the separate Consent
        // Mode API here can suppress every ad in regions without that API.
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
  }, [placementEnabled, supportedPlacement]);

  if (!supportedPlacement || !placementEnabled) return null;

  if (!gate.adsensePlacementApproved) {
    // Preview cards are useful during local UI work, but a production build
    // must not look like an unfinished ad-bearing screen while approval is
    // pending. The real ad request remains gated separately below.
    if (!gate.adsensePreviewEnabled || !import.meta.env.DEV) return null;
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
