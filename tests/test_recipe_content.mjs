import test from 'node:test';
import assert from 'node:assert/strict';
import {renderContent,mountContent} from '../web/assets/recipe-content.mjs';
import {renderDetail} from '../web/assets/locales/recipe-detail-zh-TW.mjs';
const e=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const content={profile:'synthetic',reference:':finance/rate',title:'Monthly <rate>',description:'Business purpose',version:'',change_number:1,summary:'Metadata change note',runner:{},resources:{'flow.plan.md':'<script>alert(1)</script>'},missing_fields:['runner.entrypoint'],runnable:false,view_revision:'first',
 components:[{id:'plan',state:'provided',required_for_execution:false,resources:[{path:'flow.plan.md',title:'Monthly rate plan'}],fields:[]},{id:'execution',state:'missing',required_for_execution:true,resources:[],fields:[]}],execution_blockers:[{code:'entrypoint_missing',field:'runner.entrypoint'}]};
test('all definitions use one content view and only validated entrypoints expose execution',()=>{
 const html=renderContent(content,e);
 assert.match(html,/不可執行/);assert.match(html,/尚未提供執行入口/);assert.match(html,/&lt;script>/);
 assert.doesNotMatch(html,/<script>|草稿|加入執行餐盤/);
 assert.match(renderContent({...content,runnable:true,runner:{entrypoint:'main.py'}},e),/加入執行餐盤/);
});
test('purpose, definition metadata, composition and execution gaps have separate boundaries',()=>{
 const html=renderContent(content,e);
 const purpose=html.slice(html.indexOf('recipe-purpose'),html.indexOf('</header>'));
 assert.match(purpose,/Business purpose/);assert.doesNotMatch(purpose,/Metadata change note|不可執行|修改次數/);
 const metadataStart=html.indexOf('recipe-definition-meta');
 const metadata=html.slice(metadataStart,html.indexOf('</section>',metadataStart));
 assert.match(metadata,/最近修改說明/);assert.match(metadata,/Metadata change note/);assert.doesNotMatch(metadata,/Business purpose/);
 assert.match(html,/Recipe 構成/);assert.match(html,/執行必要/);assert.match(html,/選用/);
 assert.match(html,/<summary>Monthly rate plan<\/summary>/);assert.doesNotMatch(html,/<summary>flow.plan.md/);
 assert.match(html,/來源：<code>flow.plan.md/);
});
test('user workflows precede technical composition, contracts and raw saved data',()=>{
 const data={profile:'synthetic',recipe:{reference:content.reference,title:content.title,source:'repository'},content,
  defaults:{variables:[]},declarations:{output:{schema_version:'MACHINE_PROTOCOL'}},preferences:{},
  saved:{status:'success',hosts:[],items:[{record_id:'row',host_id:'node',status:'success',data_preview:'MACHINE_RESULT'}]},
  reports:{items:[{result_id:'report',status:'success'}]},attempts:{status:'success',items:[]}};
 const html=renderDetail(data,[],e),technical=html.indexOf('id="recipe-technical"');
 for(const label of ['這道 Recipe 蒐集什麼？','共用選項與儲存','執行條件','近期採集／執行狀態','已產生的報告成果'])assert.ok(html.indexOf(label)<technical,label);
 for(const label of ['定義資訊','Recipe 構成','完整的資料與保存契約','MACHINE_PROTOCOL','MACHINE_RESULT'])assert.ok(html.indexOf(label)>technical,label);
 assert.equal((html.match(/完整的資料與保存契約/g)||[]).length,1);
 const readiness=renderContent(content,e,{section:'readiness'});
 assert.match(readiness,/尚未提供執行入口/);assert.doesNotMatch(readiness,/runner.entrypoint|<pre|execution-protocol/);
});
test('shared content poll updates readiness/resources without replacing the surrounding form',async()=>{
 const callbacks=[],original=globalThis.setTimeout,oldWindow=globalThis.window;
 globalThis.setTimeout=fn=>callbacks.push(fn);globalThis.window={scrollX:0,scrollY:120,scrollTo:(x,y)=>assert.equal(y,120)};
 const status={},section={dataset:{recipeResource:'flow.plan.md'},open:true};let present=true,calls=0,writes=0,html='';
 const root={isConnected:true,set innerHTML(value){html=value;writes++;},querySelector:()=>present?status:null,querySelectorAll:()=>[section]};
 try{
  mountContent(root,content,{profile:'synthetic',reference:':finance/rate',e,api:async path=>{assert.match(path,/recipe-content/);calls++;return {...content,runnable:true,view_revision:'second'};}});
  await callbacks.shift()();assert.match(html,/加入執行餐盤/);assert.equal(section.open,true);
  await callbacks.shift()();assert.equal(writes,1);
  present=false;await callbacks.shift()();assert.equal(calls,2);assert.equal(callbacks.length,0);
 }finally{globalThis.setTimeout=original;globalThis.window=oldWindow;}
});
test('polling refreshes separate content slots and preserves the surrounding user form',async()=>{
 const callbacks=[],original=globalThis.setTimeout,oldWindow=globalThis.window;
 globalThis.setTimeout=fn=>callbacks.push(fn);globalThis.window={scrollX:0,scrollY:0,scrollTo(){}};
 const status={},form={value:'unsaved user option'};
 const root={isConnected:true,set innerHTML(_){throw new Error('must not replace the user form');},querySelector:()=>status,querySelectorAll:()=>[]};
 const targets={purpose:{innerHTML:''},readiness:{innerHTML:''},technical:{innerHTML:''}};
 try{
  mountContent(root,content,{profile:'synthetic',reference:content.reference,e,targets,api:async()=>({...content,runnable:true,view_revision:'next'})});
  await callbacks.shift()();assert.match(targets.readiness.innerHTML,/加入執行餐盤/);
  assert.match(targets.technical.innerHTML,/Recipe 構成/);assert.doesNotMatch(targets.purpose.innerHTML,/Recipe 構成/);
  assert.equal(form.value,'unsaved user option');root.isConnected=false;await callbacks.shift()();
 }finally{globalThis.setTimeout=original;globalThis.window=oldWindow;}
});

test('agent recipes expose an escaped copyable prompt instead of a plate execution action',()=>{
 const html=renderContent({...content,runnable:true,launch:{mode:'agent',prompt:'Review </textarea><script>bad</script> & then ask about effects.'}},e,{section:'readiness'});
 assert.match(html,/透過 Agent 執行/);assert.match(html,/data-agent-prompt readonly/);assert.match(html,/data-copy-agent-prompt/);
 assert.match(html,/&lt;\/textarea>/);assert.doesNotMatch(html,/<script>|href=|加入執行餐盤/);
 assert.match(html,/複製不會啟動執行或通知 agent/);
});

test('copying an agent prompt copies literal text only and offers manual fallback',async()=>{
 const oldTimer=globalThis.setTimeout,oldNavigator=Object.getOwnPropertyDescriptor(globalThis,'navigator');
 let click,copied='',focused=false,selected=false;const prompt={value:'Synthetic <literal> prompt',focus(){focused=true;},select(){selected=true;}},status={};
 const root={isConnected:true,addEventListener:(name,fn)=>{click=fn;},querySelector:selector=>selector==='[data-agent-prompt]'?prompt:status};
 globalThis.setTimeout=()=>{};
 try{
  Object.defineProperty(globalThis,'navigator',{value:{clipboard:{writeText:async value=>{copied=value;}}},configurable:true});
  mountContent(root,content,{profile:'synthetic',reference:content.reference,e,api:()=>{throw new Error('copy must not execute or notify');}});
  const event={target:{closest:()=>({})}};await click(event);
  assert.equal(copied,prompt.value);assert.match(status.textContent,/已複製/);
  globalThis.navigator.clipboard.writeText=async()=>{throw new Error('clipboard denied');};await click(event);
  assert.ok(focused&&selected);assert.match(status.textContent,/無法自動複製/);
 }finally{globalThis.setTimeout=oldTimer;if(oldNavigator)Object.defineProperty(globalThis,'navigator',oldNavigator);else delete globalThis.navigator;}
});
