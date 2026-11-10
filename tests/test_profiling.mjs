import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {renderProfiling,profilingUrl,mountProfiling} from '../web/assets/profiling.mjs';

const e=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const base={retained_record_count:1,domains:[{id:'storage'}],capabilities:[{id:'storage.capacity',domain:'storage',title:'Storage',integration:'partial',scope_note:'<img src=x>',evidence_counts:{complete:1,partial:0,unavailable:0,not_collected:0}}],items:[{capability_id:'storage.capacity',property_id:'space',state:'complete',evidence:[{namespace:'fixture',recipe_reference:'<source>',state:'complete',samples:[{status:'success',keys:{mount:'<script>'},value_preview:'0',value_truncated:true}],reason_codes:[],record_id:'<record>',observed_at:'2026-11-01T00:00:00Z',definition:{unit:'percent'},samples_truncated:true}]}],next_offset:null};

test('values, original times, limitations, and untrusted evidence stay visible and inert',()=>{
  const html=renderProfiling(base,{e});
  assert.match(html,/\>0<\/pre>/);assert.match(html,/2026/);
  assert.match(html,/原始採樣時間/);assert.match(html,/不代表資料仍然新鮮/);
  assert.match(html,/截短預覽/);assert.match(html,/&lt;record&gt;/);
  assert.match(html,/單位: percent/);
  assert.doesNotMatch(html,/<script>|<img src=x>|<source>/);
  assert.match(html,/&lt;script&gt;/);
});

test('failed attempts, uncollected, successful empty enumeration and integration gaps differ',()=>{
  const data=structuredClone(base);
  data.items[0].evidence[0].state='unavailable';
  data.items[0].evidence[0].samples=[{status:'unavailable',keys:{},value_preview:'null',reason_code:'permission_denied'}];
  assert.match(renderProfiling(data,{e}),/未取得/);
  assert.match(renderProfiling(data,{e}),/permission_denied/);
  data.items[0].evidence[0].state='complete';data.items[0].evidence[0].samples=[];
  assert.match(renderProfiling(data,{e}),/成功列舉/);
  data.items[0].state='not_collected';data.items[0].evidence=[];
  data.capabilities.push({id:'storage.health',domain:'storage',integration:'not_integrated',scope_note:'specialized recipe exists'});
  const html=renderProfiling(data,{e});
  assert.match(html,/未採集/);assert.match(html,/尚未整合收集來源/);
  data.retained_record_count=0;
  assert.match(renderProfiling(data,{e}),/尚無已整合來源的保留觀測/);
});

class Element {
  innerHTML='';textContent='';nodes={};events={};
  querySelector(selector){return this.nodes[selector]??=new Element();}
  addEventListener(name,handler){this.events[name]=handler;}
}
test('mount retains Profile/Host scope through pagination and never posts or acquires',async()=>{
  const root=new Element(),calls=[];
  await mountProfiling(root,{profile:'p&x',host_id:'host & one',e,request:async url=>{
    calls.push(url);return {...structuredClone(base),items:[],next_offset:calls.length===1?1:null};
  }});
  assert.equal(profilingUrl('p&x','host & one'),'/api/v1/profiling/host?profile=p%26x&host_id=host+%26+one&offset=0&limit=250');
  root.querySelector('#profiling-more').events.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(calls[1],/offset=1/);assert.match(calls[1],/profile=p%26x/);
  assert.equal(root.querySelector('#profiling-more').hidden,true);
  const source=readFileSync(new URL('../web/assets/host-manager.mjs',import.meta.url),'utf8');
  assert.match(source,/view==='profiling'/);assert.match(source,/mountProfiling/);
});
test('failed reads do not become empty healthy data and can be retried',async()=>{
  for(const status of [401,503]){
    const root=new Element();let count=0;
    await mountProfiling(root,{profile:'main',host_id:'node',e,request:async()=>{
      count++;if(count===1)throw {status};return structuredClone(base);
    }});
    assert.match(root.querySelector('#profiling-status').textContent,status===401?/登入/:/讀取失敗/);
    assert.equal(root.querySelector('#profiling-retry').hidden,false);
    root.querySelector('#profiling-retry').events.click();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(count,2);assert.equal(root.querySelector('#profiling-status').textContent,'');
  }
});

test('policy basis and safe query/scope evidence remain distinct and inert',()=>{
  const data=structuredClone(base),source=data.items[0].evidence[0];
  source.source_scope='<untrusted scope>';
  source.commands=[{argv:['sshd','-T'],exitcode:0,termination_status:'confirmed'}];
  for(const [basis,label] of [['configured','設定來源（不代表已生效）'],['effective','指定範圍的有效政策查詢'],['runtime','執行狀態查詢'],['context','操作者指定的查詢情境']]){
    source.samples[0].basis=basis;
    const html=renderProfiling(data,{e});
    assert.ok(html.includes(label));assert.match(html,/收集範圍與查詢證據/);
    assert.match(html,/&lt;untrusted scope&gt;/);assert.doesNotMatch(html,/<untrusted scope>/);
    assert.match(html,/sshd/);assert.match(html,/confirmed/);
  }
});
