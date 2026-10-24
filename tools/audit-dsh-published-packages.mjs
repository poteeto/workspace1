#!/usr/bin/env node
// Explicitly audit that each pinned DSH package exists for the requested release.
// A removed upstream package must be reviewed, not silently forced to an old version.
import { readFileSync } from 'node:fs';

const pkg = JSON.parse(readFileSync('tools/dsh-runtime/package.json', 'utf8'));
const target = pkg.dependencies['@deepseek-ai/dsh'];
const entries = Object.entries(pkg.dependencies).filter(([name]) => name.startsWith('@deepseek-ai/'));
const results = [];
let index = 0;
const concurrency = 18;
await Promise.all(Array.from({ length: concurrency }, async () => {
  for (;;) {
    const i = index++;
    if (i >= entries.length) return;
    const [name, version] = entries[i];
    const url = 'https://registry.npmjs.org/' + encodeURIComponent(name) + '/' + encodeURIComponent(version);
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(30000) });
      results.push({ name, version, status: response.status });
    } catch (error) {
      results.push({ name, version, status: 'NETWORK_ERROR', error: String(error) });
    }
  }
}));
results.sort((a,b) => a.name.localeCompare(b.name));
for (const {name,version,status} of results) console.log(String(status).padStart(4), name + '@' + version);
const missing = results.filter(x => x.status !== 200);
console.log('Published:', results.length - missing.length, ' Missing/errors:', missing.length);
if (missing.length) {
  console.error('Package versions requiring migration:', missing.map(x=>x.name).join(', '));
  process.exitCode = 1;
}
