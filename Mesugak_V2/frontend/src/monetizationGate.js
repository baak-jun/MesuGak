const truthy = (value) => String(value || '').trim().toLowerCase() === 'true';
const text = (value) => String(value || '').trim();

const missing = (env, key, message, errors) => {
  if (!text(env[key])) errors.push(message || `${key} is required.`);
};

export function monetizationGate(env = {}) {
  const publicRequested = truthy(env.VITE_ENABLE_PUBLIC_LIVE_DATA);
  const adsRequested = truthy(env.VITE_ENABLE_ADSENSE);
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
  const slotId = text(env.VITE_ADSENSE_PUBLIC_SLOT_ID);
  const adsRequirementsMet = publicRequested
    && publicRequirementsMet
    && truthy(env.VITE_ADSENSE_LEGAL_REVIEW_CONFIRMED)
    && Boolean(text(env.VITE_ADSENSE_LEGAL_REVIEW_REFERENCE))
    && truthy(env.VITE_ADSENSE_ACCOUNT_APPROVED)
    && truthy(env.VITE_ADSENSE_ADS_TXT_VERIFIED)
    && text(env.VITE_ADSENSE_CMP_STATUS) === 'certified_cmp_live'
    && /^ca-pub-\d{16}$/.test(clientId)
    && /^\d+$/.test(slotId);

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
    }
    if (!/^\d+$/.test(slotId)) {
      errors.push('VITE_ADSENSE_PUBLIC_SLOT_ID must be a real numeric AdSense ad-unit ID.');
    }
  }

  return Object.freeze({
    publicRequested,
    adsRequested,
    publicLiveDataApproved: publicRequested && publicRequirementsMet,
    adsensePlacementApproved: adsRequested && adsRequirementsMet,
    clientId,
    slotId,
    errors: Object.freeze(errors),
  });
}