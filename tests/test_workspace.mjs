import test from 'node:test';
import assert from 'node:assert/strict';
import {mountVersions} from '../web/assets/updates.mjs';
import {readFileSync, existsSync} from 'node:fs';
import {renderData, mountWorkspace, workspaceUrl, renderDiagnosis} from '../web/assets/workspace.mjs';
const e=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const options={e,profile:'fixture&profile'};
class Element {
  innerHTML='';textContent='';value='';events={};nodes={};
  querySelector(selector){
    if(selector==='#workspace-more'&&!this.innerHTML.includes('id="workspace-more"'))return null;
    return this.nodes[selector]??=new Element();
  }
  querySelectorAll(){return [];}
  addEventListener(name,handler){this.events[name]=handler;}
  insertAdjacentHTML(_,html){this.innerHTML+=html;}
}
test('all live lists preserve saved states, escape untrusted content and identify empty data',()=>{
  const recipe={reference:':<fixture>',title:'<script>title</script>',description:'<img src=x>',version:'1',source:'profile',status:'failed'};
  const html=renderData('/recipes',{status:'failed',items:[recipe],sources:[]},options);
  assert.doesNotMatch(html,/<script>|<img src=x>/);
  assert.match(html,/&lt;script&gt;/);assert.match(html,/失敗/);
  assert.match(html,/profile=fixture%26profile/);
  for(const path of ['/recipes','/work','/logs','/retention','/recipes/data']){
    const empty=renderData(path,{status:'success',items:[],sources:[]},options);
    assert.match(empty,/目前沒有資料/);
    assert.doesNotMatch(empty,/demo-|DEMO-|2026-10-31|my-backup-check/);
  }
});
test('overview distinguishes unavailable services from empty lists and reports saved counts',()=>{
  const html=renderData('/workspace',{status:'partial',host_count:7,components:{notifications:{status:'unavailable'},todos:{status:'success',items:[],total:0}}},options);
  assert.match(html,/設定主機數/);assert.match(html,/>7</);
  assert.match(html,/資料讀取失敗/);assert.match(html,/目前沒有資料/);
  assert.doesNotMatch(html,/通知\s*\(0\)/);
});
test('saved log links use read-only history and preserve original source times and outcomes',()=>{
  const html=renderData('/logs',{status:'success',items:[{id:'a',source:'console',time:'2026-11-01T00:00:00Z',title:'<host>',status:{failed:1},url:'/console/a/history',details:{original:'saved'}}]},options);
  assert.match(html,/\/console\/a\/history/);assert.match(html,/failed/);assert.match(html,/saved/);
  assert.match(html,/&lt;host&gt;/);
});
test('unauthorized and failed reads never become an empty or successful workspace',async()=>{
  for(const status of [401,503]){
    const root=new Element();
    await mountWorkspace(root,{path:'/workspace',e,siteName:'owner',fetchImpl:async()=>({ok:false,status})});
    const html=root.querySelector('#workspace-content').innerHTML;
    assert.match(html,status===401?/請先登入/:/資料讀取失敗/);
    assert.doesNotMatch(html,/目前沒有資料/);
  }
});
test('workspace selection and pagination retain exact Profile scope',async()=>{
  assert.equal(workspaceUrl('/recipes','p&x',{recipe:':nested/check'}),'/recipes?recipe=%3Anested%2Fcheck&profile=p%26x');
  const root=new Element(),urls=[];
  await mountWorkspace(root,{path:'/recipes',e,siteName:'owner',search:'?profile=other&recipe=%3Acheck',profiles:{default_profile:'main',profiles:[{name:'main'},{name:'other'}]},fetchImpl:async url=>{
    urls.push(url);return {ok:true,json:async()=>({profile:'other',status:'success',items:[],sources:[],next_offset:null})};
  }});
  assert.match(urls[0],/profile=other/);assert.match(urls[0],/item_id=%3Acheck/);
});
test('document source is inert and only listed documents can be opened',async()=>{
  const root=new Element(),urls=[];
  await mountWorkspace(root,{path:'/docs',e,siteName:'owner',search:'?doc=docs/guide.md',fetchImpl:async url=>{
    urls.push(url);return {ok:true,json:async()=>url.includes('/content?')?{content:'<script>bad()</script>'}:{items:[{path:'docs/guide.md'}]}};
  }});
  assert.match(root.querySelector('#workspace-content').innerHTML,/&lt;script&gt;/);
  assert.doesNotMatch(root.querySelector('#workspace-content').innerHTML,/<script>/);
  assert.equal(urls.length,2);
  const missing=new Element();let calls=0;
  await mountWorkspace(missing,{path:'/docs',e,siteName:'owner',search:'?doc=../private',fetchImpl:async()=>{calls++;return {ok:true,json:async()=>({items:[]})};}});
  assert.equal(calls,1);assert.match(missing.querySelector('#workspace-content').textContent,/找不到/);
});
test('version panel reports actual values and has no simulated upgrade controls',async()=>{
  const root=new Element();
  await mountVersions(root,{e,fetchImpl:async()=>({ok:true,json:async()=>({opsfeast:{version:'0.fixture'},sshscript:{version:null}})})});
  const html=root.querySelector('#version-products').innerHTML;
  assert.match(html,/0.fixture/);assert.match(html,/未安裝/);
  assert.match(html,/data-check-version/);
  assert.doesNotMatch(html,/data-request-update/);
});
test('production no longer imports or serves the synthetic roadmap and playback',()=>{
  const source=readFileSync(new URL('../web/assets/workbench.js',import.meta.url),'utf8');
  assert.doesNotMatch(source,/mountRoadmap|mountDemo|roadmap\.mjs|versionPreview/);
  for(const file of ['roadmap.mjs','host-model.mjs','host-draft.mjs','locales/roadmap-zh-TW.mjs','locales/host-draft-zh-TW.mjs'])assert.equal(existsSync(new URL('../web/assets/'+file,import.meta.url)),false);
});

test('partial diagnosis explains unsupported fields and escapes saved command evidence',()=>{
  const html=renderDiagnosis({host_id:'fixture',status:'partial',issue_count:1,coverage_gap_count:1,coverage_gaps:[{job:'network',properties:['network.ipv6.address'],reason_code:'ipv6_not_collected'}],issues:[{stage:'probe',reason_code:'command_failed',command:'<script>bad</script>',stderr:{text:'permission denied'}}],notes:[]},{e,profile:'qa'});
  assert.match(html,/未採集 IPv6/);assert.match(html,/network.ipv6.address/);
  assert.match(html,/permission denied/);assert.match(html,/&lt;script&gt;/);
  assert.doesNotMatch(html,/<script>/);
});
