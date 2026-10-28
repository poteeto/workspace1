/** Mandatory Agent tool approval. Same-UID plugins and native terminals remain outside this policy. */
import { classifyCommand } from './destructive.js';
import { resolveEffectiveWorkdir } from './workdir.js';
import { statSync, readFileSync } from 'node:fs';
import { posix } from 'node:path';
import { createHash } from 'node:crypto';
// Java 已按签名 APK 的 native lock 核验。仅识别同一个已加载的引擎库；
// 不将任意 LD_PRELOAD、额外库或工作区里的同名文件视为可信启动项。
export function verifiedEnginePreload(env, { platform=process.platform, arch=process.arch, read=readFileSync, stat=statSync }={}) {
  const library=env.BXROOT_LIB_PATH, digest=env.DSHA_BXROOT_RUNTIME_SHA256;
  if (platform!=='linux' || arch!=='arm64' || env.DSHA_ANDROID_RUNTIME!=='1' || env.DSHA_BXROOT_STRICT_EXEC!=='1'
      || typeof library!=='string' || !/^\/data\/app\/(?:[^/\s]+\/)*com\.dsh\.client-[^/\s]+\/lib\/arm64\/libbxroot-runtime\.so$/.test(library)
      || library.split('/').some(part=>part==='.'||part==='..') || !/^[a-f0-9]{64}$/.test(digest||'') || env.LD_PRELOAD!==library) return null;
  try {
    if (!stat(library).isFile() || createHash('sha256').update(read(library)).digest('hex')!==digest) return null;
    const mapped=String(read('/proc/self/maps','utf8')).split('\n').some(line=>line.trim().split(/\s+/).slice(5).join(' ')===library);
    return mapped ? library : null;
  } catch { return null; }
}
const enginePreload=verifiedEnginePreload(process.env);
const runtimes = new WeakMap(), executions = new WeakMap();
const encoded = value => JSON.stringify(value);
const envFacts = value => Object.entries(value).sort(([a],[b]) => a.localeCompare(b));
// Locked Cordis proxies expose their providing object through this symbol.
// Each get() creates a fresh context proxy; comparing proxies would reject valid approvals.
const serviceIdentity = value => value?.[Symbol.for('cordis.original')] ?? value;
const fail = message => { throw new Error('DSHA_DESTRUCTIVE_BLOCKED: ' + message); };
export function attachPolicy(runtime, ctx) { runtime=serviceIdentity(runtime); runtimes.set(runtime, { ctx }); ctx.effect(() => () => runtimes.delete(runtime)); }
export function captureExecution(runtime, exec, tool) {
  const actualRuntime=serviceIdentity(runtime), owner=runtimes.get(actualRuntime); if (!owner) fail('Mandatory host policy is missing.');
  executions.set(exec, { ...owner, ctx:runtime.ctx, runtime:actualRuntime, exec, name:exec.name, arguments:exec.arguments, token:exec.token, callId:exec.callId, agent:exec.agent, agentCtx:exec.agent?.ctx, session:exec.agent?.session, header:exec.agent?.session?.header, cwd:exec.agent?.session?.header?.cwd, tool, toolExecute:tool?.execute, dispatched:false });
}
function check(record, exec) {
  if (!record || record.exec !== exec || exec.name !== record.name || exec.arguments !== record.arguments || exec.token !== record.token || exec.callId !== record.callId || exec.agent !== record.agent || exec.agent?.session !== record.session || exec.signal?.aborted) fail('Execution identity changed or cancellation arrived.');
  if (record.session?.header?.cwd !== record.cwd) fail('Session workdir changed.');
  if (exec.agent?.ctx !== record.agentCtx || record.session?.header !== record.header) fail('Agent scope or session header identity changed.');
  if (!runtimes.has(record.runtime) || serviceIdentity(record.ctx.get('tools')) !== record.runtime) fail('Mandatory tools service identity changed.');
  if (record.environment && encoded(envFacts(process.env)) !== record.processEnvironment) fail('Process environment changed.');
  if (record.bashServices && ['shell','shellEnv','sandboxPolicy'].some(name => serviceIdentity(record.ctx.get(name)) !== record.bashServices[name])) fail('Bash execution services changed.');
}
// 完全权限只由当前会话的实际沙箱与审批策略共同决定，不借用进程默认值。
function fullAccess(record, approval) {
  return approval?.effectivePolicy(record.session) === 'never'
    && record.ctx.get('sandboxPolicy')?.resolve({ session: record.session }).mode === 'danger-full-access';
}
function consumeLease(record, facts) {
  const approval = record.ctx.get('approval');
  if (!record.lease || record.lease.facts !== facts || record.lease.consumed || serviceIdentity(approval) !== record.lease.approval) fail('Matching approval is missing.');
  if (record.lease.fullAccess) {
    if (serviceIdentity(record.ctx.get('sandboxPolicy')) !== record.lease.sandboxPolicy || !fullAccess(record, approval)) fail('Full access was revoked before dispatch.');
  } else if (approval?.effectivePolicy(record.session) === 'never') fail('Matching one-time approval is missing.');
  record.lease.consumed=true;
}
async function approve(record, exec, reason, facts) {
  check(record, exec);
  const approval = record.ctx.get('approval');
  if (fullAccess(record, approval)) {
    record.lease = { facts, consumed: false, approval: serviceIdentity(approval), fullAccess: true, sandboxPolicy: serviceIdentity(record.ctx.get('sandboxPolicy')) };
    return;
  }
  if (!approval || !record.agent || typeof approval.request !== 'function' || approval.effectivePolicy(record.session) === 'never') fail('No usable one-time approval channel.');
  const response = await approval.request({ agent: record.agent, toolName: record.name, callId: record.callId, reason, displayReason: { en: reason, zh: '此调用可能删除或覆盖已有数据。' + reason }, signal: exec.signal });
  check(record, exec);
  if (response !== 'allowed-once') fail('This call was not approved once.');
  record.lease = { facts, consumed: false, approval: serviceIdentity(approval) };
}
export async function prepareOperation(runtime, exec) {
  const owner = runtimes.get(serviceIdentity(runtime));
  if (!owner) fail('Mandatory host policy is missing.');
  const record = executions.get(exec); check(record,exec);
  if (exec.name !== 'bash') return;
  record.bashServices = Object.fromEntries(['shell','shellEnv','sandboxPolicy'].map(name=>[name,serviceIdentity(record.ctx.get(name))]));
  const collected = record.ctx.get('shellEnv')?.collect(exec) || {};
  record.environment = Object.freeze({ ...collected });
  record.processEnvironment = encoded(envFacts(process.env));
  const policy = record.ctx.get('shell')?.sandboxMode === undefined ? undefined : record.ctx.get('sandboxPolicy')?.resolve(exec.agent ? { session: exec.agent.session } : {});
  record.workdir = resolveEffectiveWorkdir({ workdir: exec.arguments?.workdir, workspaceRoot: policy?.workspaceRoot, sessionCwd: record.cwd, execCwd: exec.cwd });
  const base=policy?.workspaceRoot ?? record.cwd, explicit=exec.arguments?.workdir;
  // Matches the locked rc2 Bash resolveWorkdir(), including executor-default undefined.
  record.actualWorkdir=explicit===undefined?base:base!==undefined&&!posix.isAbsolute(explicit)?base+'/'+explicit:explicit;
  const analysis = classifyCommand(exec.arguments?.command, { cwd: record.workdir.dir, cwdKnown: record.workdir.exact, env: { ...process.env, ...record.environment }, trustedEnginePreload:enginePreload, probe: path => { try { const s=statSync(path); return s.isDirectory()?'dir':s.isFile()?'file':'other'; } catch(error) { return ['ENOENT','ENOTDIR'].includes(error.code)?'missing':'unknown'; } }, sizeProbe: path => statSync(path).size, readFile: path => { const s=statSync(path); return s.isFile()&&s.size<=65536?readFileSync(path,'utf8'):null; } });
  record.analysis = analysis;
  const facts = encoded([record.name, exec.arguments, record.workdir, record.actualWorkdir, envFacts(record.environment)]);
  record.facts = facts;
  if (analysis.requiresApproval) await approve(record, exec, 'DSHA ' + analysis.classification + ': ' + (analysis.opaqueReason || analysis.findings.map(row=>row.kind).join(', ')) + '; workdir=' + record.workdir.dir + '; targets=' + (analysis.unknownTargets ? 'unknown; count unknown' : analysis.targets.join(', ')) + '. Verify the original command; allow this call once.', facts);
}
export function verifyDispatch(runtime, exec, tool) {
  const record=executions.get(exec); check(record,exec);
  if (record.runtime !== serviceIdentity(runtime) || !runtimes.has(record.runtime) || record.tool !== tool || record.toolExecute !== tool.execute || record.dispatched) fail('Tool identity changed, policy missing, or execution was reused.');
  if (record.analysis?.requiresApproval) {
    consumeLease(record, record.facts);
  }
  record.dispatched=true;
}
export function preparedEnvironment(exec) { const record=executions.get(exec); check(record,exec); if (!record.dispatched || !record.environment) fail('No approved actual Bash environment.'); return record.environment; }
export function verifyBashRequest(exec, workdir) { const record=executions.get(exec); check(record,exec); const normalize=value=>typeof value==='string'?posix.normalize(value):value; if (!record.dispatched || normalize(workdir)!==normalize(record.actualWorkdir)) fail('Actual Bash workdir differs from approved facts.'); }
/** Runs after actual FS resolution/observation intent, preserving the backend CAS contract. */
export async function guardIntent(ctx, exec, target, intent, operation) {
  const record=executions.get(exec); check(record,exec);
  if (!record.dispatched || !['write','edit','str_replace_editor'].includes(record.name)) fail('Unprepared file mutation.');
  const fs=ctx.fs, info=await fs.stat(target,exec.signal); check(record,exec);
  if (operation==='write' && info===undefined) {
    if (intent && intent.kind !== 'createIfAbsent') fail('Creation intent conflicts with the actual absent target.');
    return { kind:'createIfAbsent' };
  }
  if (!info || info.type!=='file' || info.version===undefined) fail('Mutation target/version cannot be verified.');
  if (intent?.kind==='createIfAbsent') fail('Create cannot overwrite an existing file.');
  const version=intent?.version ?? info.version;
  if (encoded(version)!==encoded(info.version)) fail('Target changed after the observed intent.');
  const facts=encoded([target.targetKey,target.displayPath,version,operation,record.arguments]);
  await approve(record,exec,'DSHA overwrite: '+target.displayPath+'; one existing file. Verify the proposed edit; allow this call once.',facts);
  if (serviceIdentity(ctx.fs)!==serviceIdentity(fs) || encoded((await fs.stat(target,exec.signal))?.version)!==encoded(version)) fail('Filesystem service or target changed during approval.');
  check(record,exec);
  consumeLease(record, facts);
  return operation==='edit'?{version}:{kind:'replaceIfVersion',version};
}
