import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const runtime = path.resolve(process.env.DSHA_TEST_RUNTIME || path.join(root, 'app/build/locked-dsh-runtime-rc1'));
const recipe = JSON.parse(await readFile(path.join(root, 'app/src/main/assets/lexical-claim-patch.json'), 'utf8'));
const expectedVersion = JSON.parse(await readFile(path.join(root, 'tools/dsh-runtime/package.json'), 'utf8')).dependencies['@deepseek-ai/dsh'];
const source = await readFile(path.join(runtime, 'node_modules', '@deepseek-ai', 'dsh-client-ui-conversation', 'lib', 'client.js'), 'utf8');
assert.equal(recipe.dshVersion, expectedVersion);
const archive = path.resolve(process.env.DSHA_RUNTIME_ARCHIVE || path.join(root, 'app/src/main/assets/dsh-runtime.bin'));
const archiveEntry = 'usr/local/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-client-ui-conversation/lib/client.js';
const archiveSource = execFileSync('tar', ['-xOf', archive, archiveEntry], {
  encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, windowsHide: true
});

if (expectedVersion === '0.2.1-rc.2') {
  // This upstream release no longer contains the TOKEN_STYLE claim decoration.
  // Do not blindly insert the former patch into a different Lexical transform.
  assert.doesNotMatch(source, /TOKEN_STYLE/);
  assert.equal(source.includes(recipe.patches[0].before), false);
  assert.doesNotMatch(archiveSource, /TOKEN_STYLE/);
  assert.doesNotMatch(archiveSource, /DSHA_CLAIM_DECOR_OVERFLOW_STYLE_V1/);
  console.log('PASS: DSH rc2 omits the old claim transform and legacy patch');
} else {
  assert.equal(source.split(recipe.patches[0].before).length, 2);
  const patched = source.replace(recipe.patches[0].before, recipe.patches[0].after);
  assert.match(patched, /DSHA_CLAIM_DECOR_OVERFLOW_STYLE_V1/);
  assert.match(patched, /overflowNode\\.setStyle\\(""\\)/);
  assert.match(archiveSource, /DSHA_CLAIM_DECOR_OVERFLOW_STYLE_V1/);
  assert.doesNotMatch(archiveSource, /const \\[tokenNode\\] = node\\.splitText\\(token\\.length\\)/);
  console.log('PASS: Lexical claim overflow styling patch applied');
}
