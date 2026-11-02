import test from 'node:test';
import assert from 'node:assert/strict';
import {filterRows, roadmapCopy as c, mountRoadmap, versionPreview, recipeUrl, logUrl, observationHistory} from '../web/assets/roadmap.mjs';
const escape=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
test('host ID matching ignores case and whitespace, combines with group, preserves absent observed IPs',()=>{
  assert.equal(filterRows(c.hosts.rows,' DEMO-WEB ').length,2);
  assert.equal(filterRows(c.hosts.rows,'demo','database')[0][0],'demo-db-01');
  assert.equal(filterRows(c.hosts.rows,'web','database').length,0);
  assert.equal(filterRows(c.hosts.rows,'missing').length,0);
  assert.equal(filterRows(c.hosts.rows,'web')[0][3],'');
  assert.equal(c.hosts.rows[3][4],false);
  assert.equal(filterRows(c.logs.rows,'','Recipe',1).length,1);
  assert.equal(filterRows(c.logs.rows,'備份','',1,[0,2])[0][0],'2026-11-01 09:15:42');
});
test('overview and Skills state synthetic provenance and escape owner identity',()=>{
  const root={innerHTML:''};
  mountRoadmap(root,{path:'/workspace',e:escape,siteName:'<img src=x>'});
  assert.match(root.innerHTML,/&lt;img src=x&gt;/);
  assert.match(root.innerHTML,/合成示範資料/);
  assert.match(root.innerHTML,/優先通知/);assert.match(root.innerHTML,/待辦工作/);
  mountRoadmap(root,{path:'/skills',e:escape,siteName:'owner'});
  assert.match(root.innerHTML,/並非讀取真實 SKILL.md/);
  assert.ok(root.innerHTML.indexOf('我的 Skills')<root.innerHTML.indexOf('內建 Skills'));
});
test('version and transfer previews cannot perform writes or claim installed versions',()=>{
  const html=versionPreview(escape);
  assert.match(html,/版本讀取待接入/);assert.equal((html.match(/<button[^>]*disabled/g)||[]).length,2);
  const root={innerHTML:''};mountRoadmap(root,{path:'/recipes/data',e:escape,siteName:'owner'});
  assert.match(root.innerHTML,/匯入不會自動執行/);
  assert.equal((root.innerHTML.match(/<button[^>]*disabled/g)||[]).length,5);
});

test('stable detail links preserve nested recipe IDs and separate log identities',()=>{
  assert.equal(new URL(recipeUrl(2),'http://localhost').searchParams.get('recipe'),'system/inventory/overview');
  assert.notEqual(logUrl(0),logUrl(1));
});
test('individual logs have seconds, source, escaped content and independent new-window links',()=>{
  const root={innerHTML:''};let crumbs;
  mountRoadmap(root,{path:'/logs',e:escape,siteName:'owner',search:'?entry=demo-run-02',setBreadcrumb:value=>crumbs=value});
  assert.match(root.innerHTML,/2026-11-01 09:15:42/);
  assert.match(root.innerHTML,/target="_blank" rel="noopener"/);
  assert.match(root.innerHTML,/部分資料缺失/);
  assert.doesNotMatch(root.innerHTML,/DEMO-SESSION|18:04:15/);
  assert.equal(crumbs[0].url,'/logs');
  mountRoadmap(root,{path:'/logs',e:escape,siteName:'owner',search:'?entry=missing'});
  assert.match(root.innerHTML,/找不到這筆示範紀錄/);
  assert.doesNotMatch(root.innerHTML,/log-content/);
});
test('recipe histories retain failure and unknown coverage rather than fabricated zeros',()=>{
  const html=observationHistory(0,escape);
  assert.match(html,/觀測歷史/);assert.match(html,/部分完成/);assert.match(html,/失敗/);
  assert.match(html,/未產生資料/);assert.match(html,/08:10:05/);
  assert.notEqual(html,observationHistory(1,escape));
});


test('host rows link IDs to Summary, retain missing IPs and put disabled state in last notes',async()=>{
  const {hostCopy,hostRowsHtml,hostUrl}=await import('../web/assets/host-draft.mjs');
  const html=hostRowsHtml([hostCopy.rows[1],hostCopy.rows[3]],escape);
  assert.match(html,/<td>deploy<\/td>/);assert.match(html,/<td class="host-ip"><\/td>/);
  assert.match(html,/停用/);assert.match(html,/尚未執行 host-init/);
  assert.equal(new URL(hostUrl('a/b','console'),'http://localhost').searchParams.get('host'),'a/b');
  assert.match(html,/view=summary/);assert.doesNotMatch(html,/host-row-actions|available-tag/);
});
test('new host console stays disconnected and exposes selected host in breadcrumb',async()=>{
  const {mountHostDraft}=await import('../web/assets/host-draft.mjs');
  const content={innerHTML:''},root={innerHTML:'',querySelector:()=>content};let crumbs;
  mountHostDraft(root,{query:new URLSearchParams('host=demo-web-01&view=console&session=new'),e:escape,heading:()=>'',setBreadcrumb:value=>crumbs=value});
  assert.equal(crumbs[1].label,'demo-web-01');assert.equal(crumbs[2].label,'互動 Console');
  assert.match(content.innerHTML,/尚未連線/);assert.match(content.innerHTML,/<input disabled/);
  assert.equal((content.innerHTML.match(/<button[^>]*disabled/g)||[]).length,3);
});
test('login identity is pinned and nonlogin users cannot move into the first position',async()=>{
  const {seedHost,chooseLogin,moveUser}=await import('../web/assets/host-model.mjs');
  let users=seedHost(c.hosts.rows[0]).users;
  assert.equal(moveUser(users,'root',-1)[0].id,'login');
  assert.equal(moveUser(users,'login',1)[0].id,'login');
  users=moveUser(users,'audit',-1);assert.equal(users[1].id,'audit');
  users=chooseLogin(users,'root');assert.equal(users[0].id,'root');assert.equal(users.filter(user=>user.login).length,1);
  assert.equal(moveUser(users,'audit',-1)[0].id,'root');
});
test('host histories are scoped, ordered descending, and link to independent contextual logs',async()=>{
  const {hostRecords,hostLogUrl}=await import('../web/assets/host-model.mjs');
  const records=hostRecords('demo-db-01');
  assert.ok(records.every(record=>record.host==='demo-db-01'));
  assert.deepEqual(records.map(record=>record.time),records.map(record=>record.time).sort().reverse());
  assert.deepEqual(records.filter(record=>record.source==='recipe').map(record=>record.status),['failure','success']);
  const root={innerHTML:''};let crumbs;
  mountRoadmap(root,{path:'/logs',search:new URL(hostLogUrl(records[0]),'http://localhost').search,e:escape,siteName:'owner',setBreadcrumb:value=>crumbs=value});
  assert.equal(crumbs[1].label,'demo-db-01');assert.match(root.innerHTML,/10:32:12/);
  mountRoadmap(root,{path:'/logs',search:'?host=missing&entry=console-02',e:escape,siteName:'owner'});
  assert.match(root.innerHTML,/找不到/);assert.doesNotMatch(root.innerHTML,/log-content/);
});
