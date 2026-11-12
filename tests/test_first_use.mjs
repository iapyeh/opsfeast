import test from 'node:test';
import assert from 'node:assert/strict';
import {setupPhase,setupProgress,takeSetupToken} from '../web/assets/first-use.mjs';
import {getMessages} from '../web/assets/i18n.mjs';
const state={schema_version:'0.1.0',admin_configured:false,authenticated:false,edit_unlocked:false,agent_control_available:true};
test('first-use steps come from server evidence and preserve account authorization',()=>{
  assert.equal(setupPhase(state),'verify');
  assert.equal(setupPhase({...state,edit_unlocked:true}),'verify');
  assert.equal(setupPhase({...state,admin_configured:true,edit_unlocked:true}),'login');
  assert.equal(setupPhase({...state,admin_configured:true}),'login');
  assert.equal(setupPhase({...state,admin_configured:true,authenticated:true}),'appearance');
  assert.equal(setupPhase({...state,agent_control_available:false}),'unavailable');
  assert.equal(setupPhase(null),'unavailable');
  assert.equal(setupPhase({...state,admin_configured:'false'}),'unavailable');
});
test('progress and token instructions are localized and do not embed secret values',()=>{
  const l=getMessages('zh-TW').firstUse;
  const html=setupProgress(l,'account',String);
  assert.equal((html.match(/aria-current="step"/g)||[]).length,1);
  assert.match(html,/建立管理帳號/);
  assert.match(html,/可稍後設定/);
  assert.match(l.agentPrompt,/最高權限/);
  assert.doesNotMatch(l.agentPrompt,/\.token/);
});

test('browser-only first use offers a copyable recovery and rechecks into account setup',async(t)=>{
  const {mountFirstUse}=await import('../web/assets/first-use.mjs');
  const previousFetch=globalThis.fetch;
  const previousNavigator=Object.getOwnPropertyDescriptor(globalThis,'navigator');
  t.after(()=>{globalThis.fetch=previousFetch;if(previousNavigator)Object.defineProperty(globalThis,'navigator',previousNavigator);else delete globalThis.navigator;});
  let current={...state,agent_control_available:false};
  globalThis.fetch=async()=>({ok:true,json:async()=>current});
  let copied='';
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:{writeText:async text=>{copied=text;}}}});
  let nodes=new Map(),html='';
  const root={set innerHTML(value){html=value;nodes=new Map();},querySelector(selector){
    if(!nodes.has(selector))nodes.set(selector,{textContent:'',selected:false,focus(){},select(){this.selected=true;},listeners:{},addEventListener(event,handler){this.listeners[event]=handler;}});
    return nodes.get(selector);
  }};
  const m=getMessages('zh-TW'),origin='http://localhost:18741';
  await mountFirstUse(root,{m,e:String,origin});
  assert.match(html,/原對話貼上並送出/);
  assert.match(html,/id="setup-agent-prompt"/);
  assert.match(html,/--agent-control/);
  assert.match(html,/http:\/\/localhost:18741/);
  assert.doesNotMatch(html,/\{origin\}/);
  await root.querySelector('#setup-copy').listeners.click();
  assert.match(copied,/沿用既有 port、資料與帳號/);
  assert.match(copied,/controller/);
  assert.match(copied,/不要連線主機或執行 recipe/);
  navigator.clipboard.writeText=async()=>{throw new Error('denied');};
  await root.querySelector('#setup-copy').listeners.click();
  assert.equal(root.querySelector('#setup-agent-prompt').selected,true);
  assert.equal(root.querySelector('#setup-copy-status').textContent,m.firstUse.copyFailed);
  current=state;
  await root.querySelector('#setup-recheck').listeners.click();
  assert.match(html,/請開啟 AI 助理提供的管理帳號設定連結/);
  assert.doesNotMatch(html,/--agent-control/);
  current={...state,admin_configured:true};
  await root.querySelector('#setup-recheck').listeners.click();
  assert.match(html,/登入並繼續設定/);
  assert.doesNotMatch(html,/setup-agent-prompt/);
});

test('a failed status read offers retry without claiming agent control is disabled',async(t)=>{
  const {mountFirstUse}=await import('../web/assets/first-use.mjs');
  const previousFetch=globalThis.fetch;t.after(()=>{globalThis.fetch=previousFetch;});
  globalThis.fetch=async()=>{throw new Error('offline');};
  let html='';const root={set innerHTML(value){html=value;},querySelector(){return {focus(){},addEventListener(){}};}};
  await mountFirstUse(root,{m:getMessages('zh-TW'),e:String,origin:'http://localhost:18741'});
  assert.match(html,/目前無法確認設定狀態/);
  assert.match(html,/setup-retry/);
  assert.doesNotMatch(html,/setup-agent-prompt|--agent-control/);
});

test('setup fragment is removed from history and browser credentials go only to the setup endpoint',async(t)=>{
  const {mountFirstUse}=await import('../web/assets/first-use.mjs');
  const originals=new Map(['location','history','fetch'].map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]));
  t.after(()=>{for(const [key,value] of originals)if(value)Object.defineProperty(globalThis,key,value);else delete globalThis[key];});
  let replaced='',configured=false,reset=false,requests=[];
  Object.defineProperty(globalThis,'location',{configurable:true,value:{hash:'#setup-token=synthetic-form-token',pathname:'/setup',search:''}});
  Object.defineProperty(globalThis,'history',{configurable:true,value:{replaceState(_a,_b,url){replaced=url;}}});
  globalThis.fetch=async(path,options={})=>{
    requests.push({path,body:options.body?JSON.parse(options.body):null});
    if(path==='/api/v1/setup')return {ok:true,json:async()=>({...state,admin_configured:configured})};
    if(path==='/api/v1/setup/claim')return {ok:true,json:async()=>({csrf:'synthetic-csrf'})};
    if(path==='/api/v1/setup/administrator'){configured=true;return {ok:true,json:async()=>({configured:true})};}
    throw new Error('unexpected endpoint');
  };
  let nodes=new Map(),html='';
  const root={set innerHTML(value){html=value;nodes=new Map();},querySelector(selector){
    if(!nodes.has(selector))nodes.set(selector,{value:'',focus(){},reset(){reset=true;},querySelector:s=>root.querySelector(selector+' '+s),listeners:{},addEventListener(event,handler){this.listeners[event]=handler;}});
    return nodes.get(selector);
  }};
  await mountFirstUse(root,{m:getMessages('zh-TW'),e:String,origin:'http://localhost:18741'});
  assert.equal(replaced,'/setup');
  assert.match(html,/type="password"/);assert.match(html,/不會送到 AI 助理對話/);
  assert.doesNotMatch(html,/synthetic-form-token|synthetic-csrf/);
  root.querySelector('#setup-username').value='owner';
  root.querySelector('#setup-password').value='synthetic-private-secret';
  root.querySelector('#setup-confirm').value='different';
  const submit=root.querySelector('#setup-account').listeners.submit;
  await submit({preventDefault(){}});
  assert.equal(requests.length,2);
  root.querySelector('#setup-confirm').value='synthetic-private-secret';
  await submit({preventDefault(){}});
  assert.equal(reset,true);assert.match(html,/登入並繼續設定/);
  assert.deepEqual(requests[2],{path:'/api/v1/setup/administrator',body:{username:'owner',password:'synthetic-private-secret',csrf:'synthetic-csrf'}});
  assert.equal(requests.filter(r=>r.body?.password).length,1);
});
