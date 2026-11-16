import { monetizationGate } from './monetizationGate.js';

const scriptSelector = 'script[src^="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"]';
let scriptPromise = null;

function initializeGoogleFc() {
  if (typeof window === 'undefined') return null;
  window.googlefc = window.googlefc || {};
  window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];
  window.adsbygoogle = window.adsbygoogle || [];
  return window.googlefc;
}

export function loadAdSenseScript(clientId) {
  if (typeof document === 'undefined' || !clientId) return Promise.resolve(false);
  initializeGoogleFc();

  if (scriptPromise) return scriptPromise;
  if (document.querySelector(scriptSelector)) return Promise.resolve(true);

  const script = document.createElement('script');
  scriptPromise = new Promise((resolve, reject) => {
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(clientId)}`;
    script.addEventListener('load', () => {
      resolve(true);
    }, { once: true });
    script.addEventListener('error', () => {
      script.remove();
      reject(new Error('AdSense script failed to load.'));
    }, { once: true });
    document.head.appendChild(script);
  }).catch((error) => {
    scriptPromise = null;
    throw error;
  });

  return scriptPromise;
}

export function startAdSense(env = import.meta.env) {
  const gate = monetizationGate(env);
  if (!gate.adsensePlacementApproved) return false;

  // The account's published Google CMP message is delivered with the AdSense
  // publisher tag. Load it before React so consent UI and settings are present
  // on every route; ad units are still requested only by approved placements.
  void loadAdSenseScript(gate.clientId).catch(() => {});
  return true;
}
