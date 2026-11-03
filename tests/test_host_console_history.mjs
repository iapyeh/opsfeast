import test from 'node:test';
import assert from 'node:assert/strict';
import {consoleHistoryMarkup,mountHostConsoleHistory} from '../web/assets/host-console-history.mjs';
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const session=(id='a',extra={})=>({session_id:id,title:'saved '+id,created_at:'2026-11-03T16:00:01Z',updated_at:'2026-11-03T16:10:01Z',block_count:1,block_states:{completed:1},...extra});
function fixture(){const els=new Map();return {innerHTML:'',querySelector(key){if(!els.has(key))els.set(key,{});return els.get(key);}};}
test('history escapes data and derives local reader links without implying live connections',()=>{
 const html=consoleHistoryMarkup(session('"/<bad>',{title:'<script>x</script>',reader_url:'javascript:bad',block_states:{streaming:2,waiting:1,failed:1,interrupted:1}}),escape);
 assert.ok(!html.includes('<script>'));assert.ok(!html.includes('javascript:'));
 assert.ok(html.includes('href="/console/%22%2F%3Cbad%3E/history"'));
 assert.ok(html.includes('2026-11-04 00:00:01+08:00'));
 for(const label of ['未結束區塊 2','待回覆表單 1','失敗區塊 1','中斷區塊 1'])assert.ok(html.includes(label));
 assert.ok(!html.includes('執行成功'));assert.ok(html.includes('target="_blank" rel="noopener"'));
 const scoped=consoleHistoryMarkup(session(),escape,{profile:'lab & test',host_id:'a/b'});
 assert.ok(scoped.includes('/history?profile=lab+%26+test&amp;host_id=a%2Fb'));
});
test('pagination keeps explicit scope, preserves records on failure, refreshes from newest',async()=>{
 const root=fixture(),calls=[];let fail=false;
 const request=async path=>{calls.push(path);if(fail)throw Error('offline');const q=new URL(path,'http://localhost').searchParams;return q.has('before')?{sessions:[session('older')],next_cursor:null}:{sessions:[session('new')],next_cursor:'new'};};
 await mountHostConsoleHistory(root,{profile:'lab & test',host_id:'a/b',e:escape,request});
 assert.ok(root.innerHTML.includes('saved new'));
 const first=new URL(calls[0],'http://localhost');assert.equal(first.searchParams.get('profile'),'lab & test');assert.equal(first.searchParams.get('host_id'),'a/b');
 fail=true;await root.querySelector('#console-more').onclick();
 assert.ok(root.innerHTML.includes('saved new'));assert.ok(root.innerHTML.includes('無法讀取'));
 fail=false;await root.querySelector('#console-more').onclick();
 assert.equal(new URL(calls.at(-1),'http://localhost').searchParams.get('before'),'new');
 assert.ok(root.innerHTML.includes('saved older'));
 await root.querySelector('#console-refresh').onclick();
 assert.ok(!root.innerHTML.includes('saved older'));assert.ok(!new URL(calls.at(-1),'http://localhost').searchParams.has('before'));
});
test('empty history and initial read failure are recoverable without execution',async()=>{
 const root=fixture();let failure=true;
 await mountHostConsoleHistory(root,{profile:'lab',host_id:'web-01',e:escape,request:async()=>{if(failure)throw Error('unauthorized');return {sessions:[],next_cursor:null};}});
 assert.ok(root.innerHTML.includes('無法讀取'));
 failure=false;await root.querySelector('#console-refresh').onclick();assert.ok(root.innerHTML.includes('目前沒有這台主機'));
 assert.ok(root.innerHTML.includes('不會連線主機或重新執行指令'));
});
