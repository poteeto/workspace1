// 执行锁定 rc2 的真实 ModelSelect / UsagePill，不以预览模型代替生产保存协议。
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {browserFixture} from './rc1-browser-fixture.mjs';
const runtime=process.env.DSHA_TEST_RUNTIME||JSON.parse(fs.readFileSync('app/build/test-runtimes/current.json','utf8')).raw;
const fixture=await browserFixture(runtime), {page}=fixture;
const recipe=name=>JSON.parse(fs.readFileSync('app/src/main/assets/'+name,'utf8'));
try {
  const frontend=path.join(runtime,'node_modules/@deepseek-ai/dsh-web-frontend/dist');
  // Production loads both its index and vendor styles; omitting vendor loses menu/ring colors.
  for(const file of fs.readdirSync(path.join(frontend,'assets')).filter(name=>name.endsWith('.css')).sort((a,b)=>Number(!a.startsWith('vendor-'))-Number(!b.startsWith('vendor-'))))
    await page.addStyleTag({content:fs.readFileSync(path.join(frontend,'assets',file),'utf8')});
  await fixture.load('dsh-client-ui-model-selection',[recipe('workspace-model-ui-patch.json')],'module.exports.audit={ModelSelect};');
  await fixture.load('dsh-client-ui-chat',[recipe('workspace-stats-ui-patch.json')],'module.exports.audit={UsagePill,ActivityPill};');
  await fixture.load('dsh-client-ui-conversation',[recipe('workspace-composer-ui-patch.json')],'module.exports.audit={ContextMeter};');
  await fixture.load('dsh-client-ui-permission-presets',[recipe('workspace-permission-ui-patch.json')],'module.exports.audit={PermissionSelect,displayPermissionPreset,optionDescription,accessZh,accessEn};');
  await page.evaluate(()=>{
    window.__ModuleLoader__={load({factory}){factory(()=>({}));}};
  });
  await page.addScriptTag({content:fs.readFileSync('app/src/main/assets/builtin-plugins/dsh-web-mobile/lib/client.js','utf8').replace('var __cache = {};','window.mobileRequire=__localRequire; var __cache = {};')});
  await page.evaluate(()=>{
    for(const name of ['base','layout','compat','misc']) {
      const style=document.createElement('style');style.textContent=Object.values(mobileRequire(`./styles/${name}.css.js`)).filter(x=>typeof x==='string').join('\n');document.head.append(style);
    }
    const R=auditModules.react.default||auditModules.react, D=auditModules['react-dom'].default||auditModules['react-dom'];
    const {ModelSelect}=auditExports['@deepseek-ai/dsh-client-ui-model-selection'].audit;
    const {UsagePill,ActivityPill}=auditExports['@deepseek-ai/dsh-client-ui-chat'].audit;
    const {ContextMeter}=auditExports['@deepseek-ai/dsh-client-ui-conversation'].audit;
    const {PermissionSelect,displayPermissionPreset,optionDescription,accessZh,accessEn}=auditExports['@deepseek-ai/dsh-client-ui-permission-presets'].audit;
    window.permissionLocale='zh';window.permissionValue='guarded-full-access';window.permissionCalls=[];
    const permissionT=(key,values={})=>((permissionLocale==='zh'?accessZh:accessEn)[key]??key).replace(/\{(\w+)\}/g,(_match,name)=>values[name]??'');
    const guarded={value:'guarded-full-access',name:'guarded-full-access',description:'Full file access; destructive or opaque agent commands and existing-file overwrites ask once.'};
    const catalog={options:[{value:'read-only',name:'read-only'},{value:'workspace-write',name:'workspace-write'},{value:'danger-full-access',name:'danger-full-access'},guarded]};
    if(displayPermissionPreset(guarded.value,guarded.name,permissionT)!=='保护式完全权限')throw Error('GUARDED_LABEL_NOT_CHINESE');
    if(displayPermissionPreset('custom','Custom',permissionT)!=='自定义')throw Error('CUSTOM_LABEL_NOT_CHINESE');
    if(displayPermissionPreset(guarded.value,'My own policy',permissionT)!=='My own policy')throw Error('HOST_LABEL_OVERWRITTEN');
    if(optionDescription({...guarded,description:'custom policy description'},permissionT)!=='custom policy description')throw Error('HOST_DESCRIPTION_OVERWRITTEN');
    if(!optionDescription(guarded,permissionT).startsWith('允许访问全部文件'))throw Error('GUARDED_DESCRIPTION_NOT_CHINESE');
    window.calls=[]; window.listeners=new Set(); window.locked=false; window.rejectSave=false;
    const levels=ids=>ids.map(id=>({id,name:id[0].toUpperCase()+id.slice(1)}));
    window.snapshot={status:'ready',error:null,failures:[],pending:null,retainedEffort:undefined,current:{provider:'fixture',model:'short',reasoningEffort:'high'},groups:[{id:'fixture',name:'Fixture provider',models:[
      {id:'short',name:'Short',reasoning:{efforts:levels(['off','low','high','max']),defaultEffort:'high'}},
      {id:'long',name:'一个非常长的模型名称用于验证模型切换时整体高度和滑条位置不会发生变化',reasoning:{efforts:levels(['low','high','max']),defaultEffort:'high'}},
      {id:'plain',name:'No reasoning'}, {id:'one',name:'Single choice',reasoning:{efforts:levels(['high']),defaultEffort:'high'}},
      {id:'default',name:'Provider default',reasoning:{efforts:levels(['low','high'])}}
    ]}]};
    window.publish=changes=>{snapshot={...snapshot,...changes};listeners.forEach(fn=>fn());};
    const directory={getSnapshot:()=>snapshot,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);}};
    window.t=(key,v={})=>({'menu.model':'模型','menu.aria':'Model settings','retry':'重试','stats.counts':`${v.turns} 轮 ${v.steps} 步`,'stats.cacheHit':`缓存命中 ${v.percent}%`,'number.thousand':`${v.value}K`,'number.million':`${v.value}M`,'message.turnUsage.cacheHit':'缓存命中','message.turnUsage.count':`${v.count} tok`,'message.tokensPerSecond':`${v.tps} tok/s`}[key]??key);
    const select=async selection=>{calls.push(selection);if(rejectSave)return {ok:false,error:{code:'session/writer-held',message:'fixture'}};publish({current:selection});return {ok:true};};
    const usage={uncachedInputTokens:2000,cacheReadTokens:8000,cacheWriteTokens:0,outputTokens:120};
    const stats={turns:12,steps:34,llmMs:4000,toolMs:500,ttftMs:800,ttftSteps:2,decodeMs:3000,decodeTokens:120};
    const projection=key=>key==='tokenUsage'?usage:key==='sessionStats'?stats:key==='contextPressure'?{projectedTokens:8600,contextWindow:1000000}:key==='contextBreakdown'?{systemTokens:1400,toolsTokens:6871,messageTokens:329}:key==='permissions'?{currentValue:permissionValue}:undefined;
    window.root=D.createRoot(document.getElementById('root'));
    window.render=()=>root.render(R.createElement('div',{'data-mobile-nav':'frame'},R.createElement('aside',{'data-pane':'sidebar','aria-hidden':true,hidden:true,inert:''}),R.createElement('main',{'data-phase':'active',style:{padding:16}},
      R.createElement(PermissionSelect,{locked,select:async value=>{permissionCalls.push(value);permissionValue=value;render();return true;},usePermissionCatalog:pick=>pick({value:catalog}),useProjection:projection,t:permissionT}),
      R.createElement(ModelSelect,{locked,available:true,directory,load:()=>{},select,t,renderSlot:(_name,_props,{fallback})=>fallback}),
      R.createElement('div',{'data-composer-dock':true,style:{marginTop:20}},R.createElement(ActivityPill,{useChat:pick=>pick({legacy:{nodes:[]}}),useProjection:projection,usePerformanceUsage:pick=>pick('full'),t}),R.createElement(UsagePill,{useProjection:projection,usePerformanceUsage:pick=>pick('full'),t}),R.createElement(ContextMeter,{useProjection:projection,t:(key,values={})=>key==='context.aria'?`上下文已用 ${values.percent}`:key==='context.used'?'上下文':key==='number.thousand'?`${values.value}K`:key==='number.million'?`${values.value}M`:key}))
    )));
    render();
  });
  const trigger=page.locator('[data-dsha-model-trigger]'), menu=page.locator('[data-dsha-model-menu]'), slider=page.getByRole('slider');
  const permission=page.locator('[data-dsha-permission-trigger]');
  assert.match(await permission.innerText(),/保护式完全权限/);
  await permission.click();await page.getByText('完全权限',{exact:true}).click();
  await page.getByRole('button',{name:'取消',exact:true}).waitFor();
  assert.deepEqual(await page.evaluate(()=>permissionCalls),[],'权限中文化不能绕过原完全权限确认');
  await page.getByRole('button',{name:'取消',exact:true}).click();
  await page.evaluate(()=>{permissionLocale='en';render();});await page.getByRole('button',{name:'Access mode, current: Guarded Full Access'}).waitFor();
  await page.evaluate(()=>{permissionLocale='zh';render();});await permission.getByText('保护式完全权限',{exact:true}).waitFor();
  const geometry=()=>page.evaluate(()=>Object.fromEntries(['menu','range','footer'].map((name,i)=>{const e=document.querySelector(['[data-dsha-model-menu]','.dsha-ws-range','.dsha-ws-model-footer'][i]);const b=e.getBoundingClientRect();return[name,{x:b.x,y:b.y,w:b.width,h:b.height}];})));
  await trigger.click(); await slider.waitFor();
  const before=await geometry();
  await slider.focus();await page.keyboard.press('End');
  assert.equal(await slider.getAttribute('aria-valuetext'),'Max');
  assert.deepEqual(await page.evaluate(()=>calls),[],'滑动草稿不得提前提交');
  assert.deepEqual(await geometry(),before,'强度说明变化不得移动外框/滑条/底部');
  for(const colorScheme of ['light','dark']) {
    await page.emulateMedia({colorScheme});
    await page.waitForFunction(()=>{const c=document.querySelector('.dsha-ws-pixels');if(!c?.width)return false;const pixels=c.getContext('2d').getImageData(0,0,c.width,c.height).data;for(let i=0;i<pixels.length;i+=4)if(pixels[i+3]>80&&pixels[i+2]>pixels[i]+15&&pixels[i]>pixels[i+1]+10)return true;return false;});
    assert.deepEqual(await geometry(),before,'主题变化不得移动菜单和滑条');
  }
  await page.emulateMedia({colorScheme:'light',reducedMotion:'reduce'});
  const pixels=()=>page.locator('.dsha-ws-pixels').evaluate(canvas=>canvas.toDataURL());
  await page.waitForTimeout(80);const still=await pixels();await page.waitForTimeout(120);assert.equal(await pixels(),still,'减少动态效果时不继续刷新像素场');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.getByRole('button',{name:'关闭',exact:true}).click();
  assert.deepEqual(await page.evaluate(()=>calls),[],'关闭取消强度草稿');
  await trigger.click();await slider.focus();await page.keyboard.press('End');await page.getByRole('button',{name:'完成',exact:true}).click();await menu.waitFor({state:'detached'});
  assert.deepEqual(await page.evaluate(()=>calls.at(-1)),{provider:'fixture',model:'short',reasoningEffort:'max'},'必须提交原 select 的实际档位');
  await trigger.click();const stable=await geometry();
  await page.locator('.dsha-ws-model-choice').click();await page.getByRole('searchbox').fill('一个非常长');
  assert.equal(await page.getByRole('menuitemradio').count(),1,'保留原模型目录过滤');
  await page.getByRole('menuitemradio').click();await slider.waitFor();
  assert.deepEqual(await geometry(),stable,'长短模型切换不得改变菜单/强度条位置');
  assert.equal(await slider.getAttribute('max'),'2','只用模型声明的三个档位');
  await page.locator('.dsha-ws-model-choice').click();await page.getByRole('searchbox').fill('No reasoning');await page.getByRole('menuitemradio').click();
  await menu.locator('.dsha-ws-description').waitFor();assert.equal(await slider.count(),0,'不支持推理强度的模型不显示虚构档位');
  assert.equal((await menu.boundingBox()).height,stable.menu.h);
  await page.locator('.dsha-ws-model-choice').click();await page.getByRole('searchbox').fill('Single choice');await page.getByRole('menuitemradio').click();await slider.waitFor();assert.equal(await slider.isDisabled(),true);
  await page.locator('.dsha-ws-model-choice').click();await page.getByRole('searchbox').fill('Provider default');await page.getByRole('menuitemradio').click();await slider.waitFor();assert.equal(await slider.getAttribute('max'),'2');
  await page.evaluate(()=>{rejectSave=true;});await slider.focus();await page.keyboard.press('End');await page.getByRole('button',{name:'完成',exact:true}).click();
  await page.getByText('error.sessionInUse',{exact:true}).waitFor();assert.equal(await menu.isVisible(),true,'写锁保存失败保留原错误和面板');
  await page.evaluate(()=>{rejectSave=false;publish({error:'fixture-load-failure'});});
  await page.getByRole('button',{name:'关闭',exact:true}).click();await trigger.click();await menu.getByRole('alert').waitFor();assert.equal(await menu.getByRole('button',{name:'重试',exact:true}).isVisible(),true);
  await page.evaluate(()=>publish({error:null}));
  for(const [width,height] of [[320,320],[390,844],[600,360]]) {
    await page.setViewportSize({width,height});await page.waitForTimeout(100);
    const box=await menu.boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width+1&&box.y>=0&&box.y+box.height<=height+1,JSON.stringify(box));
    await page.getByRole('button',{name:'完成',exact:true}).scrollIntoViewIfNeeded();
    assert.ok((await page.getByRole('button',{name:'完成',exact:true}).boundingBox()).y<height);
  }
  await page.setViewportSize({width:320,height:320});
  const large=await page.addStyleTag({content:'.dsha-ws-model-root *{font-size:18.2px!important;line-height:1.3!important;}'});
  await page.getByRole('button',{name:'完成',exact:true}).scrollIntoViewIfNeeded();
  assert.ok((await page.getByRole('button',{name:'完成',exact:true}).boundingBox()).y<320,'大字体下底部操作保持可见');
  await large.evaluate(node=>node.remove());
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'关闭',exact:true}).click();
  await page.evaluate(()=>{locked=true;render();});await page.waitForFunction(()=>document.querySelector('[data-dsha-model-trigger]')?.disabled===true);assert.equal(await trigger.isDisabled(),true,'保留锁定状态');await page.evaluate(()=>{locked=false;render();});await page.waitForFunction(()=>document.querySelector('[data-dsha-model-trigger]')?.disabled===false);
  const cache=page.locator('[data-composer-stat="cache"] button'), usage=page.locator('[data-composer-stat="usage"] button');
  assert.match(await cache.innerText(),/80%/);await cache.click();await page.locator('[data-dsha-cache-detail]').waitFor();await page.keyboard.press('Escape');
  await usage.click();await page.locator('[data-session-stats-usage]').waitFor();await page.keyboard.press('Escape');
  await page.locator('[data-dsha-context-stat]>button').click();
  await page.getByRole('dialog').waitFor();
  assert.match(await page.getByRole('dialog').innerText(),/8\.6K/,'上下文入口仍打开原用量与构成详情');
  await page.keyboard.press('Escape');
  await page.locator('[data-composer-stat="activity"] button').click();await page.locator('[data-session-stats-details]').waitFor();await page.keyboard.press('Escape');
  const boxes=await page.locator('[data-composer-stat]').evaluateAll(es=>es.map(e=>({kind:e.dataset.composerStat,...e.getBoundingClientRect().toJSON()})));
  const u=boxes.find(b=>b.kind==='usage'),c=boxes.find(b=>b.kind==='cache');assert.ok(u.right<=c.left,'缓存和累计用量不能重叠');
  for(const width of [320,390,430]){
    await page.setViewportSize({width,height:844});
    const columns=await page.locator('[data-composer-stat="usage"]>button,[data-composer-stat="cache"]>button,[data-dsha-context-stat]>button').evaluateAll(es=>es.map(e=>e.getBoundingClientRect().toJSON()));
    assert.equal(columns.length,3,'必须检查真实的用量、缓存与上下文三个入口');
    const [used,cache,context]=columns;
    assert.ok(Math.max(...columns.map(b=>b.width))-Math.min(...columns.map(b=>b.width))<1,'三个入口必须等宽');
    assert.ok(Math.max(...columns.map(b=>b.y))-Math.min(...columns.map(b=>b.y))<1,'三个入口必须同一水平线');
    assert.ok(Math.abs((cache.x+cache.width/2-used.x-used.width/2)-(context.x+context.width/2-cache.x-cache.width/2))<1,'三个入口的中心距必须相等');
    assert.equal(await page.locator('[data-dsha-context-stat] svg circle').count(),2,'保留原上下文圆环');
    const ink=await page.evaluate(()=>{
      const box=selector=>document.querySelector(selector).getBoundingClientRect();
      return {activityLeft:box('[data-composer-stat="activity"] svg').left,usageLeft:box('[data-composer-stat="usage"] svg').left,speedRight:box('[data-dsha-activity-label]>span:last-child').right,contextRight:box('[data-dsha-context-stat]>button>span:last-child').right};
    });
    assert.ok(Math.abs(ink.activityLeft-ink.usageLeft)<1,'必须对齐用户看到的轮次图标和累计用量图标，而非只对齐点击区域');
    assert.ok(Math.abs(ink.speedRight-ink.contextRight)<1,'速度与上下文读数必须贴齐同一右边线');
  }
  if(process.env.DSHA_UI_SCREENSHOTS){
    const folder=path.resolve(process.env.DSHA_UI_SCREENSHOTS);fs.mkdirSync(folder,{recursive:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(folder,'real-controls-and-equal-stats.png')});
    await trigger.click();await slider.focus();await page.keyboard.press('End');await page.waitForTimeout(400);
    await menu.screenshot({path:path.join(folder,'real-model-panel.png')});
    await page.getByRole('button',{name:'关闭',exact:true}).click();
    await permission.click();await page.screenshot({path:path.join(folder,'real-permission-menu.png')});
    await page.keyboard.press('Escape');
  }
  await page.setViewportSize({width:1000,height:800});await trigger.waitFor({state:'detached'});assert.equal(await page.locator('[data-dsha-model-trigger]').count(),0,'桌面保留原模型组件');assert.equal(await page.locator('[data-composer-stat="cache"]').count(),0,'桌面保留原合并用量组件');
  await page.setViewportSize({width:390,height:844});
  await page.evaluate(()=>{
    const R=auditModules.react.default||auditModules.react;
    const {ContextMeter}=auditExports['@deepseek-ai/dsh-client-ui-conversation'].audit;
    root.render(R.createElement('div',{'data-composer-dock':true},R.createElement(ContextMeter,{useProjection:()=>undefined,t})));
  });
  await trigger.waitFor({state:'detached'});
  const empty=await page.locator('[data-composer-dock]').evaluate(e=>({height:e.getBoundingClientRect().height,background:getComputedStyle(e,'::after').content}));
  assert.ok(empty.height<=4 && empty.background==='none','尚无上下文或用量时，不能显示空白色块或预留整行高度');
  assert.deepEqual(fixture.errors,[]);
  console.log('PASS real rc2 workspace UI: draft/cancel/save, catalog/search, supported levels/default, write lock/error/retry, stable geometry, short screens, stats/details, desktop fallback');
} finally {await fixture.close();}
