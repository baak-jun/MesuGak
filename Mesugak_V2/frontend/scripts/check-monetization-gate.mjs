import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';
import { monetizationGate } from '../src/monetizationGate.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const mode = process.env.MODE || 'production';
const env = { ...loadEnv(mode, root, ''), ...process.env };
const gate = monetizationGate(env);
const fail = (message) => {
  console.error(`[monetization gate] ${message}`);
  process.exitCode = 1;
};

for (const error of gate.errors) fail(error);

if (gate.adsRequested && gate.adsensePlacementApproved) {
  const adsTxtPath = resolve(root, 'public', 'ads.txt');
  const publisherId = gate.clientId.replace(/^ca-/, '');
  const expected = `google.com, ${publisherId}, DIRECT, f08c47fec0942fa0`;
  if (!existsSync(adsTxtPath)) {
    fail('AdSense is enabled but frontend/public/ads.txt does not exist. Run npm run ads:txt after the account is approved.');
  } else if (!readFileSync(adsTxtPath, 'utf8').split(/\r?\n/).includes(expected)) {
    fail('ads.txt does not contain the exact approved Google publisher line.');
  }
}

if (!process.exitCode) {
  const state = gate.adsensePlacementApproved ? 'enabled after all explicit gates' : gate.publicLiveDataApproved ? 'public data enabled; ads disabled' : 'public data and ads disabled';
  console.log(`[monetization gate] ${state}`);
}