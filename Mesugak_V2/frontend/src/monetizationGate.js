const truthy = (value) => String(value || '').trim().toLowerCase() === 'true';
const text = (value) => String(value || '').trim();
// Keep the allowlist explicit. Ads may appear only in authored learning pages
// and, when separately enabled, at the end of a complete public analysis.
const adPlacements = ['learning', 'analysis'];
const slotEnvKey = (placement) => `VITE_ADSENSE_${placement.toUpperCase()}_SLOT_ID`;

const missing = (env, key, message, errors) => {
  if (!text(env[key])) errors.push(message || `${key} is required.`);
};

export function monetizationGate(env = {}) {
  const publicRequested = truthy(env.VITE_ENABLE_PUBLIC_LIVE_DATA);
  const adsRequested = truthy(env.VITE_ENABLE_ADSENSE);
  const analysisAdsRequested = truthy(env.VITE_ENABLE_ANALYSIS_ADS);
  const adsensePreviewEnabled = truthy(env.VITE_SHOW_AD_PLACEHOLDERS);
  const errors = [];

  const publicRequirementsMet = truthy(env.VITE_PUBLIC_DATA_RIGHTS_CONFIRMED)
    && Boolean(text(env.VITE_PUBLIC_DATA_RIGHTS_APPROVAL_REFERENCE))
    && Boolean(text(env.VITE_PUBLIC_DATA_RULES_RELEASE_REFERENCE));

  if (publicRequested && !truthy(env.VITE_PUBLIC_DATA_RIGHTS_CONFIRMED)) {
    errors.push('Public data is enabled without written data-rights confirmation.');
  }
  if (publicRequested) {
    missing(env, 'VITE_PUBLIC_DATA_RIGHTS_APPROVAL_REFERENCE', 'Public data requires a retained rights-approval reference.', errors);
    missing(env, 'VITE_PUBLIC_DATA_RULES_RELEASE_REFERENCE', 'Public data requires a reviewed Firestore-rules release reference.', errors);
  }

  const clientId = text(env.VITE_ADSENSE_CLIENT_ID);
  const slotIds = Object.freeze(Object.fromEntries(adPlacements.map((placement) => [placement, text(env[slotEnvKey(placement)])])));
  const placeholderPublisher = clientId === 'ca-pub-1234567890123456';
  const slotIsValid = (slotId) => /^\d+$/.test(slotId) && slotId !== '12345678';
  const requestedPlacements = adPlacements.filter((placement) => placement === 'learning' || (placement === 'analysis' && analysisAdsRequested));
  const adsRequirementsMet = publicRequested
    && publicRequirementsMet
    && truthy(env.VITE_ADSENSE_LEGAL_REVIEW_CONFIRMED)
    && Boolean(text(env.VITE_ADSENSE_LEGAL_REVIEW_REFERENCE))
    && truthy(env.VITE_ADSENSE_ACCOUNT_APPROVED)
    && truthy(env.VITE_ADSENSE_ADS_TXT_VERIFIED)
    && text(env.VITE_ADSENSE_CMP_STATUS) === 'certified_cmp_live'
    && /^ca-pub-\d{16}$/.test(clientId)
    && requestedPlacements.every((placement) => slotIsValid(slotIds[placement]))
    && !placeholderPublisher;

  if (adsRequested) {
    if (!publicRequested || !publicRequirementsMet) {
      errors.push('AdSense requires the separately approved public-data release gate.');
    }
    if (!truthy(env.VITE_ADSENSE_LEGAL_REVIEW_CONFIRMED)) {
      errors.push('AdSense requires a completed legal/policy review acknowledgement.');
    }
    missing(env, 'VITE_ADSENSE_LEGAL_REVIEW_REFERENCE', 'AdSense requires a retained legal/policy review reference.', errors);
    if (!truthy(env.VITE_ADSENSE_ACCOUNT_APPROVED)) {
      errors.push('AdSense account/site approval is not confirmed.');
    }
    if (!truthy(env.VITE_ADSENSE_ADS_TXT_VERIFIED)) {
      errors.push('ads.txt publication has not been confirmed.');
    }
    if (text(env.VITE_ADSENSE_CMP_STATUS) !== 'certified_cmp_live') {
      errors.push('A live Google-certified CMP is required before global ad serving is enabled.');
    }
    if (!/^ca-pub-\d{16}$/.test(clientId)) {
      errors.push('VITE_ADSENSE_CLIENT_ID must be a real ca-pub- publisher identifier.');
    } else if (placeholderPublisher) {
      errors.push('The example AdSense publisher identifier cannot be deployed. Set the identifier issued to this site.');
    }
    requestedPlacements.forEach((placement) => {
      const slotId = slotIds[placement];
      const key = slotEnvKey(placement);
      if (!/^\d+$/.test(slotId)) {
        errors.push(`${key} must be a real numeric AdSense ad-unit ID.`);
      } else if (slotId === '12345678') {
        errors.push(`The example ${key} cannot be deployed. Set the ad-unit ID issued to this site.`);
      }
    });
  }

  return Object.freeze({
    publicRequested,
    adsRequested,
    analysisAdsRequested,
    requestedPlacements: Object.freeze(requestedPlacements),
    publicLiveDataApproved: publicRequested && publicRequirementsMet,
    adsensePlacementApproved: adsRequested && adsRequirementsMet,
    adsensePreviewEnabled,
    clientId,
    slotIds,
    errors: Object.freeze(errors),
  });
}
