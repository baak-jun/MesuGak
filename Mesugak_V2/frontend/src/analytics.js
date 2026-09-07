const measurementId = String(import.meta.env.VITE_GOOGLE_ANALYTICS_MEASUREMENT_ID || '').trim();

let analyticsLoaded = false;
let analyticsLoadPromise = null;
let analyticsConsentAllowed = false;
let pendingPagePath = '';

function ensureGoogleFcQueue() {
  if (typeof window === 'undefined') return null;
  window.googlefc = window.googlefc || {};
  window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];
  return window.googlefc;
}

function isConsentGrantedForAnalytics(googlefc) {
  if (typeof googlefc?.getGoogleConsentModeValues !== 'function') return false;
  const status = googlefc.getGoogleConsentModeValues();
  const enumValues = googlefc.ConsentModePurposeStatusEnum || {};
  const allowed = new Set([
    enumValues.CONSENT_MODE_PURPOSE_STATUS_GRANTED ?? enumValues.GRANTED ?? 1,
    enumValues.CONSENT_MODE_PURPOSE_STATUS_NOT_APPLICABLE ?? enumValues.NOT_APPLICABLE ?? 3,
  ]);
  return [
    status?.analyticsStoragePurposeConsentStatus,
  ].every((value) => allowed.has(value));
}

function installGtagStub() {
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() {
    window.dataLayer.push(arguments);
  };
}

function sendPendingPageView() {
  if (!pendingPagePath || !analyticsLoaded || !analyticsConsentAllowed || typeof window.gtag !== 'function') return;
  window.gtag('event', 'page_view', {
    page_path: pendingPagePath,
    page_location: window.location.href,
    page_title: document.title,
  });
  pendingPagePath = '';
}

function loadAnalyticsTag() {
  if (analyticsLoaded) return Promise.resolve();
  if (analyticsLoadPromise) return analyticsLoadPromise;

  installGtagStub();
  analyticsLoadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-mesugak-analytics="loader"]');
    if (existing) {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.async = true;
    script.dataset.mesugakAnalytics = 'loader';
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
    script.addEventListener('load', resolve, { once: true });
    script.addEventListener('error', reject, { once: true });
    document.head.appendChild(script);
  }).then(() => {
    window.gtag('js', new Date());
    window.gtag('config', measurementId, { send_page_view: false });
    analyticsLoaded = true;
    sendPendingPageView();
    window.dispatchEvent(new CustomEvent('mesugak-analytics-ready'));
  }).catch((error) => {
    analyticsLoadPromise = null;
    throw error;
  });

  return analyticsLoadPromise;
}

export function startAnalytics() {
  if (!measurementId || typeof window === 'undefined') return;
  const googlefc = ensureGoogleFcQueue();
  const handleConsent = () => {
    analyticsConsentAllowed = isConsentGrantedForAnalytics(googlefc);
    if (analyticsConsentAllowed && analyticsLoaded) {
      sendPendingPageView();
    } else if (analyticsConsentAllowed) {
      void loadAnalyticsTag();
    }
  };
  if (typeof googlefc.getGoogleConsentModeValues === 'function') {
    handleConsent();
    return;
  }
  googlefc.callbackQueue.push({
    CONSENT_MODE_DATA_READY: handleConsent,
  });
}

export function trackPageView(path = `${window.location.pathname}${window.location.hash}`) {
  if (!measurementId || typeof window === 'undefined') return;
  pendingPagePath = path;
  sendPendingPageView();
}

export function openConsentSettings() {
  if (typeof window === 'undefined') return Promise.resolve(false);
  const googlefc = ensureGoogleFcQueue();
  if (typeof googlefc.showRevocationMessage === 'function') {
    googlefc.showRevocationMessage();
    return Promise.resolve(true);
  }
  return new Promise((resolve) => {
    let settled = false;
    const finish = (opened) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      resolve(opened);
    };
    const timeoutId = window.setTimeout(() => finish(false), 4000);
    googlefc.callbackQueue.push({
      CONSENT_API_READY: () => {
        try {
          if (typeof googlefc.showRevocationMessage !== 'function') return finish(false);
          googlefc.showRevocationMessage();
          finish(true);
        } catch {
          finish(false);
        }
      },
    });
  });
}
