import test from 'node:test';
import assert from 'node:assert/strict';
import {artifactUrl,renderReportList,renderReport,mountReportViewer} from '../web/assets/report-viewer.mjs';
import {renderReview,renderRun} from '../web/assets/recipe-menu.mjs';
import {loginDestination} from '../web/assets/login-navigation.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const report={result_id:'reports/id/result.json',recipe_reference:'<recipe>',status:'partial',artifacts:[{path:'report.html',title:'<title>',media_type:'text/html',size_bytes:10,sha256:'hash'},{path:'report.md',title:'Markdown',media_type:'text/markdown',size_bytes:10,sha256:'hash'}]};
test('report links preserve exact profile artifact and pagination scope',()=>{
 const html=renderReportList({items:[{result_id:'reports/id/result.json',recipe_reference:'<ref>',status:'failed'}],status:'partial',next_offset:50},{e,profile:'p&x'});
 assert.match(html,/profile=p%26x/);assert.match(html,/report=reports%2Fid%2Fresult.json/);assert.match(html,/&lt;ref&gt;/);assert.match(html,/部分報告索引/);assert.match(html,/data-reports-more="50"/);
 const api=new URL(artifactUrl('p&x','reports/id/result.json','nested/空白 a.html','download'),'http://local');
 assert.equal(api.searchParams.get('name'),'nested/空白 a.html');assert.equal(api.searchParams.get('profile'),'p&x');
});
test('HTML previews use an opaque sandbox without scripts or raw document injection',()=>{
 const html=renderReport(report,{e,profile:'main',artifact:'report.html'});
 assert.match(html,/sandbox=""/);assert.doesNotMatch(html,/allow-scripts|allow-same-origin|srcdoc=/);assert.match(html,/mode=preview/);assert.match(html,/mode=download/);assert.match(html,/停|不執行腳本/);assert.doesNotMatch(html,/<title>|<recipe>/);
});
test('text binary empty and unknown artifacts keep distinct views',()=>{
 assert.match(renderReport(report,{e,profile:'main',artifact:'report.md'}),/文字原文/);
 assert.doesNotMatch(renderReport(report,{e,profile:'main',artifact:'report.md'}),/<iframe/);
 assert.match(renderReport({...report,artifacts:[]},{e,profile:'main'}),/未宣告成果檔/);
 assert.match(renderReport(report,{e,profile:'main',artifact:'../bad'}),/找不到/);
 assert.match(renderReport({...report,artifacts:[{path:'file.bin',title:'Binary',media_type:'application/octet-stream',size_bytes:1}]},{e,profile:'main'}),/未提供內嵌預覽/);
});
test('artifact text uses textContent and never executes or recollects',async()=>{
 class Element {innerHTML='';textContent='';nodes={};querySelector(s){return this.nodes[s]??=new Element();}}
 const root=new Element(),calls=[];
 await mountReportViewer(root,{e,profile:'main',identifier:report.result_id,artifact:'report.md',api:async path=>{calls.push(path);return path.includes('/result?')?report:{content:'<script>bad()</script>'};}});
 assert.equal(root.querySelector('#report-text').textContent,'<script>bad()</script>');assert.equal(calls.length,2);assert.ok(calls.every(p=>p.startsWith('/api/v1/reports/')));
});
test('review shows exact sensor fields and completed reports offer a Web viewer',()=>{
 const html=renderReview({profile:'main',timeout:30,worker_deadline_seconds:600,pairs:[{reference:'inventory',host_id:'node',identity:{},variable_names:[],invocation:[],inventory_selection:{mode:'properties',jobs:['hardware-sensors'],properties:['sensors.fans']}}]},e);
 assert.match(html,/自選欄位 · 1 組／1 個欄位/);assert.match(html,/sensors.fans/);assert.match(html,/溫度／風扇/);
 const run=renderRun({id:'run',profile:'main',state:'completed',tasks:[{kind:'report',reference:'report',state:'success',result:{status:'success',result_id:report.result_id,artifacts:report.artifacts}}]},e);
 assert.match(run,/開啟報告成果/);assert.doesNotMatch(run,/既有 CLI 讀取/);
 assert.equal(loginDestination('?next='+encodeURIComponent('/recipe-plate?profile=main&report=reports%2Fid%2Fresult.json&artifact=report.html')),'/recipe-plate?profile=main&report=reports%2Fid%2Fresult.json&artifact=report.html');
});
