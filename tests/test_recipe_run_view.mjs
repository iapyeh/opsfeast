import test from 'node:test';
import assert from 'node:assert/strict';
import {renderRun,renderTaskBody,sharedProgress,taskIssues,taskResultId,mountRecipeRunHistory,mountRecipeRun} from '../web/assets/recipe-run-view.mjs';
const e=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const task=(extra={})=>({host_id:'node',reference:'hardware',state:'success',kind:'operation',progress:'',result:{status:'success',retention:{status:'stored'},content_update:{status:'updated'}},...extra});
const run=tasks=>({id:'run',profile:'main',state:'completed_with_gaps',remote_cleanup:'not_applicable',tasks});
test('task cards start closed, retain a host link in the summary and share one progress river',()=>{
 const html=renderRun(run([task({state:'running',progress:'<unsafe>'}),task({host_id:'other'})]),e);
 assert.equal((html.match(/id="recipe-shared-progress"/g)||[]).length,1);
 assert.equal((html.match(/class="recipe-progress"/g)||[]).length,1);
 assert.match(html,/target="_blank" rel="noopener" href="\/hosts\?profile=main&amp;host=node/);
 assert.match(html,/recipe-task-spinner/);assert.match(html,/執行完成<\/span>/);
 assert.doesNotMatch(html,/<details[^>]*\sopen|<unsafe>|查看主機系統全貌|活動與紀錄 →|保存資料 →/);
 assert.match(html,/&lt;unsafe&gt;/);
 assert.match(html,/href="\/logs\?profile=main">← 活動與紀錄/);
 assert.match(html,/href="\/recipe-plate\?profile=main">執行餐盤/);
 assert.doesNotMatch(html,/history=1|← Recipes/);
});
test('unfinished tasks name collection, retention and downstream failures separately',()=>{
 const partial=task({state:'partial',result:{status:'partial',reason_code:'value_not_reported',collection_gaps:[{properties:['hardware.serial'],reason_code:'value_not_reported'}]}});
 const stored=task({host_id:'storage',result:{status:'success',retention:{status:'failed'},content_update:{status:'failed'}}});
 const html=renderRun(run([partial,stored,task()]),e);
 assert.doesNotMatch(html,/recipe-run-problems|data-open-task|未完成項目 · 2 個任務/);assert.match(html,/有未完成項目/);assert.match(html,/結果處理有問題/);assert.match(html,/hardware.serial/);assert.match(html,/來源未提供數值/);assert.match(html,/保存：失敗/);assert.match(html,/後續呈現／通知：失敗/);
 assert.equal(taskIssues(task()).length,0);
 assert.equal(taskIssues(task({result:{status:'success',content_update:{status:'skipped'}}})).length,0);
});
test('saved diagnosis supplies exact missing fields without changing stored outcomes',()=>{
 const partial=task({state:'partial',result:{status:'partial',result_path:'/private/profile/observations/result.json'}});
 assert.equal(taskResultId(partial),'observations/result.json');
 const html=renderRun(run([partial]),e,{diagnoses:{'observations/result.json':{data:{coverage_gaps:[{properties:['hardware.uuid','hardware.serial'],reason_code:'permission_denied'}],issues:[]}}}});
 assert.match(html,/hardware.uuid、hardware.serial/);assert.match(html,/權限不足/);assert.match(html,/有未完成項目/);
});
test('shared worker progress is not repeated for every child',()=>{
 const progress=sharedProgress([task({reference:'a',progress:'one log'}),task({reference:'b',progress:'one log'})]);
 assert.equal((progress.text.match(/one log/g)||[]).length,1);assert.match(progress.text,/a、b/);
 assert.equal(sharedProgress([task({progress:'x'.repeat(140000)})]).truncated,true);
});
test('history uses read-only saved runs with exact profile and stable run links',async()=>{
 const root={innerHTML:''},calls=[];
 await mountRecipeRunHistory(root,{profile:'qa&profile',e,api:async path=>{calls.push(path);return {items:[{id:'saved-id',state:'running',created_at:'2026-11-11T00:00:00Z'}],total:1};}});
 assert.deepEqual(calls,['/api/v1/recipe-runs?profile=qa%26profile']);
 assert.match(root.innerHTML,/run=saved-id/);assert.match(root.innerHTML,/關閉瀏覽器/);assert.match(root.innerHTML,/qa%26profile/);
});
class Element {
 constructor(dataset={}){this.dataset=dataset;this.events={};this.open=false;this.scrollTop=0;this.scrollHeight=100;this.clientHeight=40;this.textContent='';}
 addEventListener(name,fn){this.events[name]=fn;}
 querySelector(selector){if(selector==='.recipe-task-body')return this.body??={innerHTML:''};return null;}
 scrollIntoView(){}
}
test('polling preserves expanded task cards and does not follow progress when scrolled up',async()=>{
 let nodes={},timer;
 const root={isConnected:true,querySelector:s=>nodes[s]||null,querySelectorAll:s=>s==='details[data-task-index][open]'?Object.values(nodes).filter(n=>n.dataset.taskIndex!==undefined&&n.open):s==='details[data-task-index]'?[nodes['#recipe-task-0']]:[],set innerHTML(value){nodes={'#recipe-shared-progress':new Element(),'#recipe-task-0':new Element({taskIndex:'0'})};},get innerHTML(){return '';}};
 const data={...run([task({state:'running'})]),state:'running'};
 await mountRecipeRun(root,{profile:'main',id:'run',e,api:async()=>data,setTimer:fn=>{timer=fn;return 1;}});
 nodes['#recipe-task-0'].open=true;nodes['#recipe-shared-progress'].scrollTop=10;
 await timer();await new Promise(done=>setImmediate(done));
 assert.equal(nodes['#recipe-task-0'].open,true);assert.equal(nodes['#recipe-shared-progress'].scrollTop,10);
 root.isConnected=false;
});

test('operation workflows link their generated saved reports without exposing paths or HTML',()=>{
 const result={status:'partial',reports:[{result_id:'reports/11111111111111111111111111111111/result.json',status:'partial'}],retention:{status:'success'}};
 const html=renderRun({profile:'main',state:'completed_with_gaps',tasks:[{host_id:'node',reference:'system/software/check/package-security',state:'partial',result}]},e);
 assert.match(html,/開啟產生的報告/);assert.match(html,/report=reports%2F11111111111111111111111111111111%2Fresult.json/);
 assert.match(html,/target="_blank" rel="noopener"/);
});

test('incomplete summaries load on expansion only and isolate each host',async()=>{
 const partial=task({state:'partial',result:{status:'partial',observation_run_id:'obs',result_id:'result'}});
 const other=task({host_id:'other',state:'partial',result:{status:'partial',observation_run_id:'obs',result_id:'other-result'}});
 const saved={id:'obs',title:'Meal',summary:{total_hosts:2,completed_hosts:0,incomplete_hosts:2,issues:[{host_id:'node',status:'partial',reason_code:'node-only'},{host_id:'other',status:'partial',reason_code:'other-only'}]}};
 let nodes={},html='',calls=[];
 const root={isConnected:true,querySelector:s=>nodes[s]||null,querySelectorAll:s=>s==='details[data-task-index][open]'?Object.values(nodes).filter(n=>n.open):s==='details[data-task-index]'?Object.values(nodes):[],set innerHTML(v){html=v;nodes={'#recipe-task-0':new Element({taskIndex:'0'}),'#recipe-task-1':new Element({taskIndex:'1'})};},get innerHTML(){return html;}};
 await mountRecipeRun(root,{profile:'main',id:'run',e,api:async path=>{
  calls.push(path);
  return path.includes('/workspace/logs?')?{items:[saved]}:path.includes('/results/diagnosis?')?{host_id:'node',coverage_gaps:[],issues:[]}:run([partial,other]);
 }});
 assert.equal(calls.length,1);assert.doesNotMatch(html,/node-only|other-only/);
 const firstNode=nodes['#recipe-task-0'],otherNode=nodes['#recipe-task-1'];
 nodes['#recipe-task-0'].open=true;nodes['#recipe-task-0'].events.toggle();
 await new Promise(done=>setImmediate(done));
 assert.equal(calls.length,3);assert.match(calls.find(p=>p.includes('/workspace/logs?')),/host_id=node/);
 assert.equal(nodes['#recipe-task-0'].open,true);assert.equal(nodes['#recipe-task-1'].open,false);
 assert.equal(nodes['#recipe-task-0'],firstNode);assert.equal(nodes['#recipe-task-1'],otherNode);
 const first=firstNode.body.innerHTML;
 assert.match(first,/node-only/);assert.doesNotMatch(first,/other-only/);
 assert.match(first,/未完成原因/);
});

test('host result explains advisory waiting once and omits redundant totals and raw JSON',()=>{
 const partial=task({host_id:'synthetic-host',state:'partial',result:{status:'partial',observation_run_id:'obs',result_id:'saved',retention:{status:'stored'},content_update:{status:'success'},internal_evidence:'DO_NOT_RENDER_RAW'}});
 const item={summary:{total_hosts:1,completed_hosts:0,incomplete_hosts:1,issues:[{host_id:'synthetic-host',status:'partial',stages:[{stage:'collection',status:'success'},{stage:'advisories',status:'failed',reason_code:'advisory_cache_wait_deadline'},{stage:'report',status:'partial',reason_code:'package_security_report_incomplete'}],packages:{collected_count:42,complete:true},gaps:['advisory_cache_wait_deadline']},{host_id:'other',reason_code:'OTHER_HOST'}]}};
 const html=renderTaskBody(partial,run([partial]),e,{activities:{'["obs","synthetic-host"]':item},diagnoses:{saved:{data:{coverage_gaps:[],issues:[],notes:['No specific failure evidence']}}}});
 assert.equal((html.match(/等待其他工作釋放公告快取逾時/g)||[]).length,1);
 assert.match(html,/公告資料不足，弱點報告未能完成判讀/);
 assert.match(html,/42 筆已安裝套件紀錄/);assert.match(html,/不是弱點數/);assert.match(html,/不代表全部已完成比對/);
 assert.doesNotMatch(html,/操作結果：|保存：已保存|後續呈現／通知：成功/);
 assert.doesNotMatch(html,/主機：完成|本主機未完成項目摘要|詳細回執與來源證據|DO_NOT_RENDER_RAW|OTHER_HOST|No specific failure evidence|advisory_cache_wait_deadline/);
 const unknown=renderTaskBody(partial,run([partial]),e,{activities:{'["obs","synthetic-host"]':{summary:{issues:[{host_id:'synthetic-host',reason_code:'<unknown>'}]}}}});
 assert.match(unknown,/&lt;unknown&gt;/);assert.doesNotMatch(unknown,/<unknown>/);
});

test('host links open separately and cards distinguish action completion from receipt problems',()=>{
 const html=renderRun(run([task({host_id:'synthetic-host',state:'partial'}),task({result:{status:'success',retention:{status:'failed'},content_update:{status:'unknown'}}})]),e);
 assert.match(html,/target="_blank" rel="noopener" href="\/hosts\?profile=main&amp;host=synthetic-host"/);
 assert.match(html,/有未完成項目/);assert.match(html,/結果處理有問題/);
 assert.match(html,/資料保存：失敗/);assert.match(html,/後續呈現／通知：未能確認/);
 assert.doesNotMatch(html,/完成 · 部分完成|操作結果：|recipe-run-problems|data-open-task/);
});
