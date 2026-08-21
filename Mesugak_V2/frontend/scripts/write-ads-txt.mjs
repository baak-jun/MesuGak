import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';
import { monetizationGate } from '../src/monetizationGate.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const mode = process.env.MODE || 'production';
const gate = monetizationGate({ ...loadEnv(mode, root, ''), ...process.env });

if (!gate.adsensePlacementApproved) {
  console.error('[ads.txt] Refusing to create ads.txt until every public-data and AdSense gate is explicitly approved.');
  process.exit(1);
}

const publisherId = gate.clientId.replace(/^ca-/, '');
const path = resolve(root, 'public', 'ads.txt');
mkdirSync(dirname(path), { recursive: true });
writeFileSync(path, `google.com, ${publisherId}, DIRECT, f08c47fec0942fa0\n`, 'utf8');
console.log(`[ads.txt] Wrote ${path}`);