// 精确复现截图命令及已核验引擎预加载；使用真实 rc2 搜索和错误转换代码。
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {verifiedEnginePreload} from '../app/src/main/assets/destructive-policy/index.js';
import {classifyCommand} from '../app/src/main/assets/destructive-policy/destructive.js';
const library='/data/app/~~fixture/com.dsh.client-fixture/lib/arm64/libbxroot-runtime.so',bytes=Buffer.from('verified-engine-fixture');
const env={BXROOT_LIB_PATH:library,LD_PRELOAD:library,DSHA_ANDROID_RUNTIME:'1',DSHA_BXROOT_STRICT_EXEC:'1',DSHA_BXROOT_RUNTIME_SHA256:createHash('sha256').update(bytes).digest('hex')};
const facts={platform:'linux',arch:'arm64',stat:()=>({isFile:()=>true}),read:file=>file==='/proc/self/maps'?`1000-2000 r-xp 00000000 01:01 123 ${library}\n`:bytes};
const trusted=verifiedEnginePreload(env,facts);assert.equal(trusted,library);
const command="pwd && printf '\\nTop-level entries:\\n' && ls -la";
assert.equal(classifyCommand(command,{env,cwd:'/root/workspace1'}).requiresApproval,true,'未知预加载仍需审批');
assert.equal(classifyCommand(command,{env,cwd:'/root/workspace1',trustedEnginePreload:trusted}).requiresApproval,false,'已核验引擎不得使只读命令误报');
assert.equal(classifyCommand(command,{env:{ENVIRONMENT:'production'},cwd:'/root/workspace1'}).requiresApproval,false,'ENVIRONMENT 不是 shell ENV 钩子');
for(const patch of [{LD_PRELOAD:library+':/tmp/other.so'},{DSHA_BXROOT_RUNTIME_SHA256:'0'.repeat(64)},{BXROOT_LIB_PATH:'/tmp/libbxroot-runtime.so',LD_PRELOAD:'/tmp/libbxroot-runtime.so'},{DSHA_ANDROID_RUNTIME:'0'}]) assert.equal(verifiedEnginePreload({...env,...patch},facts),null);
assert.equal(verifiedEnginePreload(env,{...facts,read:()=>''}),null,'没有映射/字节证明时不得跳过');
for(const extra of [{BASH_ENV:'/tmp/hook'},{ENV:'/tmp/hook'},{'BASH_FUNC_pwd%%':'() { rm /tmp/a; }'},{LD_PRELOAD:library+':/tmp/other.so'}]) assert.equal(classifyCommand(command,{env:{...env,...extra},trustedEnginePreload:trusted}).requiresApproval,true);
for(const text of ['rm /tmp/a','python -c "print(1)"','printf x > /tmp/existing']) assert.equal(classifyCommand(text,{env,trustedEnginePreload:trusted}).requiresApproval,true);
const runtime=process.env.DSHA_TEST_RUNTIME||'tools/dsh-runtime';
const require=createRequire(path.resolve(runtime,'package.json'));
if(process.env.DSHA_TEST_BXROOT==='1') {
  const {spawnSync}=await import('node:child_process');
  const child=spawnSync('/usr/bin/true',[],{detached:true});
  assert.equal(child.status,0);assert.ok(child.pid>1);
  for(const target of [child.pid,-child.pid]) {
    assert.throws(()=>process.kill(target,0),error=>error.code==='ESRCH','已回收的已知进程和进程组必须返回内核的不存在结果');
    assert.throws(()=>process.kill(target,'SIGTERM'),error=>error.code==='EPERM','真实信号继续拒绝已回收编号');
  }
  console.log('PASS actual bxroot: reaped known IDs report ESRCH; real signals remain forbidden');
}
async function loadPatched(name,extra='') {
  const recipe=JSON.parse(fs.readFileSync('app/src/main/assets/'+name,'utf8'));
  let source=fs.readFileSync(path.join(runtime,'node_modules',recipe.module),'utf8');
  for(const {before,after} of recipe.patches){assert.equal(source.split(before).length-1,1);source=source.replace(before,after);}
  source=source.replace(/from "([^"\n]+)"/g,(all,name)=>name.startsWith('node:')?all:`from ${JSON.stringify(pathToFileURL(require.resolve(name)).href)}`)
    .replace('import("@vscode/ripgrep")',`import(${JSON.stringify(pathToFileURL(require.resolve('@vscode/ripgrep')).href)})`);
  return import('data:text/javascript;base64,'+Buffer.from(source+'\n'+extra).toString('base64'));
}
const search=await loadPatched('workspace-search-runtime-patch.json','export {dshaFailureCodes};');
const web=await loadPatched('workspace-web-errors-patch.json','export {translateAbortOrNetwork};');
const fail=Object.assign(new TypeError('fetch failed'),{cause:new AggregateError([Object.assign(new Error('https://user:secret@private/'),{code:'ECONNREFUSED'}),Object.assign(new Error('secret'),{code:'ENETUNREACH'})])});
const error=web.translateAbortOrNetwork(fail,new AbortController().signal);
assert.match(error.message,/ECONNREFUSED, ENETUNREACH/);assert.doesNotMatch(error.message,/private|secret/);assert.equal(error.code,'WEB_PROVIDER_ERROR');
const cancelled=new AbortController();cancelled.abort();assert.equal(web.translateAbortOrNetwork(fail,cancelled.signal).code,'WEB_ABORTED');
const ctx={workingDirectory:{ensure:async()=>process.cwd()},subprocess:{spawn(){throw Object.assign(new Error('private path'),{code:'ENOTSUP'});}}};
assert.equal(search.dshaFailureCodes(Object.assign(new Error('private path'),{code:'ENOTSUP'})),' [ENOTSUP]');
// 真正运行宿主架构的 packaged rg，保留 rc2 subprocess 的限额、取消和退出协议。
const {Context}=await import(pathToFileURL(require.resolve('@deepseek-ai/cordis')));
const {LocalSubprocessRuntime}=await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-subprocess-local')));
const context=new Context(),subprocess=new LocalSubprocessRuntime(context);
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'dsha-workspace-search-'));
try {
  if (process.argv.includes('--diagnostics-only')) {
    console.log('PASS policy and diagnostics; native search reserved for the matching-architecture job');
  } else {
  await assert.rejects(search.runRipgrep(ctx,{signal:new AbortController().signal},'glob',['--files'],10000,100,1000),error=>error.code==='SEARCH_FAILED'&&/ENOTSUP/.test(error.message)&&!error.message.includes('private path'));
  fs.writeFileSync(path.join(temp,'main.js'),'const marker = "DSHA_SEARCH_OK";\n');
  fs.writeFileSync(path.join(temp,'index.html'),'<div>fixture</div>');
  const scope={subprocess,workingDirectory:{ensure:async()=>temp}};
  const exec={agent:{},signal:new AbortController().signal};
  const found=await search.runRipgrep(scope,exec,'glob',['--files','--glob','*.js'],100000,1000,10000);
  assert.equal(found.stdout.trim(),'main.js');
  const matched=await search.runRipgrep(scope,exec,'grep',['--json','DSHA_SEARCH_OK','.'],100000,1000,10000);
  assert.match(matched.stdout,/DSHA_SEARCH_OK/);
  const none=await search.runRipgrep(scope,exec,'glob',['--files','--glob','*.not-present'],100000,1000,10000);assert.equal(none.noMatches,true);
  if(process.env.DSHA_TEST_BXROOT==='1') {
    assert.equal(await search.resolveRgPath(),'/usr/local/bin/rg');
    const original=(await import(pathToFileURL(require.resolve('@vscode/ripgrep')))).rgPath;
    const oldScope={...scope,subprocess:{spawn:spec=>subprocess.spawn({...spec,argv:[original,...spec.argv.slice(1)]})}};
    await assert.rejects(search.runRipgrep(oldScope,exec,'glob',['--files','--glob','*.js'],100000,1000,10000),error=>error.code==='SEARCH_FAILED','同一引擎中的旧静态程序应复现失败');
    console.log('PASS actual bxroot: old static rg fails; pinned glibc rg searches successfully');
  }
  }
} finally {await context.fiber.dispose();fs.rmSync(temp,{recursive:true,force:true});}
console.log('PASS workspace environment: screenshot command, verified preload, hostile hooks, original protections, bounded/redacted errors; '+(process.argv.includes('--diagnostics-only')?'native search DEFERRED to matching architecture':'actual rc2 rg subprocess passed'));
