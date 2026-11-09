import test from 'node:test';
import assert from 'node:assert/strict';
import {hostManagementUrl,filterManagedHosts,normalizeHostGroups} from '../web/assets/host-manager.mjs';
test('host links retain explicit profile and encode opaque host IDs',()=>{
  const url=new URL(hostManagementUrl('prod','a/b & c','settings'),'http://localhost');
  assert.equal(url.searchParams.get('profile'),'prod');assert.equal(url.searchParams.get('host'),'a/b & c');
  assert.equal(url.searchParams.get('view'),'settings');
});
test('real-host filters preserve empty inventory addresses and multiple groups',()=>{
  const hosts=[{host_id:'Web-01',groups:['prod','linux'],reference_ips:{ipv4_addresses:[]}}, {host_id:'DB-01',groups:['prod']}];
  assert.deepEqual(filterManagedHosts(hosts,' WEB ','linux'),[hosts[0]]);
  assert.deepEqual(filterManagedHosts(hosts,'DB','linux'),[]);
  assert.deepEqual(hosts[0].reference_ips.ipv4_addresses,[]);
  assert.deepEqual(normalizeHostGroups(['prod',' linux ','prod','']),['prod','linux']);
});

const {mountHostManager,renderManagedHostRows}=await import('../web/assets/host-manager.mjs');
const {default:l}=await import('../web/assets/locales/host-management-zh-TW.mjs');
const e=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const sample={host_id:'web-01',label:'台北入口',description:'edge service',login_user:'operator',groups:['prod'],enabled:true,source:'hosts.yaml',reference_ips:{status:'known',ipv4_addresses:['192.0.2.8'],ipv6_addresses:['2001:db8::8']},recipe_references:[]};
class Element {
  innerHTML='';textContent='';value='';nodes={};children=[];focused=false;
  querySelector(selector){return this.nodes[selector]??=new Element();}
  append(child){this.children.push(child);}
  focus(){this.focused=true;}
}
async function mountFixture(t,{hosts=[sample],search='',latest={result:null},failedPath=null,status=503}={}) {
  const calls=[],root=new Element(),oldFetch=globalThis.fetch,oldDocument=globalThis.document,oldLocation=globalThis.location;
  globalThis.location={href:'http://localhost/hosts'};
  globalThis.document={createElement:()=>new Element()};
  globalThis.fetch=async path=>{
    calls.push(path);
    const failed=failedPath&&path.startsWith(failedPath);
    const body=failed?{detail:'unavailable'}:path==='/api/v1/profiles'?{default_profile:'qa',profiles:[{name:'qa'}]}:path.startsWith('/api/v1/results/')?latest:{hosts,groups:[{id:'prod',label:'Production'}]};
    return {ok:!failed,status:failed?status:200,json:async()=>body};
  };
  t.after(()=>{globalThis.fetch=oldFetch;globalThis.document=oldDocument;globalThis.location=oldLocation;});
  await mountHostManager(root,{m:{hostManagement:l},e,search,setBreadcrumb:()=>{}});
  await new Promise(resolve=>setImmediate(resolve));
  return {root,calls};
}
test('search combines metadata, saved IPv4/IPv6, exact groups and enabled configuration',()=>{
  const disabled={...sample,host_id:'db-02',enabled:false,groups:['lab'],label:'資料庫'};
  for(const needle of ['台北','OPERATOR',' edge ','192.0.2.8','2001:DB8::8','prod'])assert.deepEqual(filterManagedHosts([sample],needle),[sample]);
  assert.deepEqual(filterManagedHosts([sample,disabled],'','lab','disabled'),[disabled]);
  assert.deepEqual(filterManagedHosts([sample,disabled],'','prod','disabled'),[]);
  assert.deepEqual(filterManagedHosts([sample],'','pro'),[]);
  assert.deepEqual(filterManagedHosts([sample],'<script>'),[]);
  assert.equal(sample.reference_ips.ipv4_addresses[0],'192.0.2.8');
});
test('host rows escape every user value and preserve opaque profile/host links',()=>{
  const html=renderManagedHostRows([{...sample,host_id:'<host> / &',label:'<img src=x>',description:'<script>bad</script>',groups:['<group>'],reference_ips:{status:'unknown',ipv4_addresses:[],ipv6_addresses:[]}}],{e,l,profile:'qa&scope'});
  assert.doesNotMatch(html,/<img|<script>|<group>|<host>/);
  assert.match(html,/&lt;img src=x&gt;/);assert.match(html,/profile=qa%26scope/);
  assert.match(html,/scope="row"/);assert.match(html,/尚無已保存的 IP/);
  assert.match(html,/已啟用/);assert.doesNotMatch(html,/健康|在線/);
});
test('list counts and combined filters update one status region; clearing restores focus',async t=>{
  const {root,calls}=await mountFixture(t,{hosts:[sample,{...sample,host_id:'db-02',enabled:false,reference_ips:{status:'unknown'}}]});
  assert.match(root.innerHTML,/設定允許使用，不代表已驗證連線/);
  assert.equal(root.querySelector('#host-filter-count').textContent,'顯示 2 / 2 台主機');
  assert.equal(root.querySelector('#host-clear').disabled,true);
  root.querySelector('#host-state-filter').value='disabled';root.querySelector('#host-state-filter').onchange();
  assert.equal(root.querySelector('#host-filter-count').textContent,'顯示 1 / 2 台主機');
  assert.match(root.querySelector('#managed-host-list').innerHTML,/db-02/);
  root.querySelector('#host-filter').value='not found';root.querySelector('#host-filter').oninput();
  assert.match(root.querySelector('#managed-host-list').innerHTML,/目前沒有符合條件/);
  root.querySelector('#host-clear').onclick();
  assert.equal(root.querySelector('#host-filter-count').textContent,'顯示 2 / 2 台主機');
  assert.equal(root.querySelector('#host-filter').focused,true);
  assert.equal(root.querySelector('#host-clear').disabled,true);
  assert.deepEqual(calls,['/api/v1/profiles','/api/v1/hosts?profile=qa']);
});
test('no configured hosts and failed/unauthorized reads remain distinct',async t=>{
  const {root}=await mountFixture(t,{hosts:[]});
  assert.match(root.querySelector('#managed-host-list').innerHTML,/這個環境還沒有主機/);
  for(const status of [401,503]){
    const result=await mountFixture(t,{failedPath:'/api/v1/hosts',status});
    assert.match(result.root.innerHTML,status===401?/請先登入/:/無法讀取/);
    assert.doesNotMatch(result.root.innerHTML,/顯示 0|host-metrics/);
  }
});
test('host summary preserves partial, unknown and failed evidence without collection',async t=>{
  const {root,calls}=await mountFixture(t,{search:'?profile=qa&host=web-01',latest:{result:{status:'partial',short_id:'a&b'},invalid_result_count:1}});
  const detail=root.querySelector('#managed-host-detail'),result=detail.children[0];
  assert.match(root.innerHTML,/返回主機清單/);assert.match(root.innerHTML,/aria-current="page"/);
  assert.match(detail.innerHTML,/尚無資料/);assert.match(detail.innerHTML,/hosts.yaml/);
  assert.match(result.innerHTML,/部分完成/);assert.match(result.innerHTML,/result=a%26b/);assert.match(result.innerHTML,/讀取失敗/);
  assert.equal(calls.length,3);assert.ok(calls.every(path=>!path.includes('run')&&!path.includes('connect')));
  const failure=await mountFixture(t,{search:'?profile=qa&host=web-01',failedPath:'/api/v1/results/'});
  assert.match(failure.root.querySelector('#managed-host-detail').children[0].innerHTML,/無法確認狀態/);
});
test('source times display Taipei seconds while malformed source evidence stays visible',async t=>{
  const valid=await mountFixture(t,{hosts:[{...sample,reference_ips:{...sample.reference_ips,observed_at:'2026-11-08T00:00:00Z'}}],search:'?host=web-01'});
  const html=valid.root.querySelector('#managed-host-detail').innerHTML;
  assert.match(html,/8:00:00/);assert.doesNotMatch(html,/T00:00:00Z/);
  const invalid=await mountFixture(t,{hosts:[{...sample,reference_ips:{...sample.reference_ips,observed_at:'<bad-time>'}}],search:'?host=web-01'});
  assert.match(invalid.root.querySelector('#managed-host-detail').innerHTML,/&lt;bad-time&gt;/);
});
