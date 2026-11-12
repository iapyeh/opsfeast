import test from 'node:test';
import assert from 'node:assert/strict';
import {groupRecipes,recipeDomains,hostSelection,selectionMark,mountMenuLayout} from '../web/assets/recipe-menu-layout.mjs';
import {renderLayout,renderPlate} from '../web/assets/locales/recipe-menu-zh-TW.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const data={status:'success',hosts:[{host_id:'a',title:'Host A',enabled:true,login_user:'NEVER_SHOW_LOGIN'},{host_id:'b',title:'Host B',enabled:true},{host_id:'c',title:'Disabled C',enabled:false}],groups:[{id:'web',title:'Web',host_ids:['a','b','c']},{id:'overlap',title:'Overlap',host_ids:['a']}],sets:[{id:'base',title:'套餐',description:'desc',references:['inventory']}],items:[{reference:'inventory',source:'repository',title:'系統盤點',purpose:'<purpose>',runnable:true,domain:'hardware',capabilities:['hardware.cpu','network.interfaces']},{reference:':system/network/check/local',source:'profile',title:'<local>',purpose:'Local',runnable:true,domain:'custom'},{reference:'team:system/storage/check/disk',source:'team',title:'External',runnable:true,domain:'custom'},{reference:':uncategorized',source:'profile',title:'Other',runnable:false,domain:'custom'}],blueprint:{capabilities:[{id:'hardware.identity',title:'identity',domain:'hardware',observation_kind:'inventory',integration:'partial',scope_note:'<scope>'},{id:'network.connections',title:'Connections',domain:'network',observation_kind:'events',integration:'not_integrated',scope_note:'No event source'}]}};
const profiles={profiles:[{name:'main'}]};
test('domain-first grouping reuses capability mappings and classifies user/external paths',()=>{
 const groups=groupRecipes(data);
 assert.deepEqual(recipeDomains(data.items[0]),['hardware','network']);
 assert.equal(groups.find(g=>g.id==='hardware').bundle.length,1);
 assert.equal(groups.find(g=>g.id==='network').bundle.length,1);
 assert.equal(groups.find(g=>g.id==='network').user[0].reference,':system/network/check/local');
 assert.equal(groups.find(g=>g.id==='storage').user[0].source,'team');
 assert.equal(groups.find(g=>g.id==='custom').user[0].reference,':uncategorized');
 assert.ok(groups.some(g=>g.id==='analysis'));
});
test('layout places category scope then bundle/user recipes before sets hosts and plate',()=>{
 const html=renderLayout(data,groupRecipes(data),profiles,'main',e);
 for(const [before,after] of [['recipe-categories','recipe-sets'],['recipe-sets','recipe-hosts'],['recipe-hosts','recipe-plate']])assert.ok(html.indexOf(`id="${before}"`)<html.indexOf(`id="${after}"`));
 assert.match(html,/主機識別與製造資訊/);assert.match(html,/清冊 · 部分供應/);assert.match(html,/menu-capability-scope/);assert.doesNotMatch(html,/<summary>涵蓋界線/);
 assert.ok(html.indexOf('menu-capabilities')<html.indexOf('Bundle recipes'));
 assert.match(html,/User recipes/);assert.match(html,/data-group="web"/);assert.match(html,/data-all-hosts/);
 assert.doesNotMatch(html,/搜尋菜色|recipe-search|recipe-timeout|recipe-history|recipe-reports|NEVER_SHOW_LOGIN/);
 assert.doesNotMatch(html,/<purpose>|<scope>|<local>/);assert.match(html,/&lt;scope&gt;/);
});
test('all and group choices resolve enabled hosts, overlap deduplicates, individuals remain explicit',()=>{
 let selected=hostSelection(data,new Set(),'group','web',true);
 assert.deepEqual([...selected],['a','b']);
 selected=hostSelection(data,selected,'group','overlap',true);assert.equal(selected.size,2);
 selected=hostSelection(data,selected,'host','c',true);assert.equal(selected.size,3);
 selected=hostSelection(data,selected,'all',null,false);assert.deepEqual([...selected],['c']);
 selected=hostSelection(data,selected,'host','missing',true);assert.equal(selected.size,1);
 assert.deepEqual(selectionMark(['a','b'],new Set(['a'])),{checked:false,indeterminate:true});
});
test('plate has separate columns and deduplicates multi-domain recipes and hosts',()=>{
 const html=renderPlate(data,new Set(['a','b','a']),new Set(['inventory','inventory']),e);
 assert.match(html,/主機 <span>2/);assert.match(html,/Recipes <span>1/);
 assert.equal((html.match(/系統盤點/g)||[]).length,1);assert.doesNotMatch(html,/NEVER_SHOW_LOGIN/);
});
test('interactive choices synchronize duplicate recipe rows and update the plate without requests',()=>{
 class Input {constructor(dataset={}){this.dataset=dataset;this.checked=false;this.events={};}addEventListener(n,f){this.events[n]=f;}closest(){return {classList:{toggle(){}}};}hasAttribute(n){return n==='data-group'?'group'in this.dataset:n==='data-all-hosts'?'allHosts'in this.dataset:false;}}
 const dishes=[new Input({dish:'inventory'}),new Input({dish:'inventory'})],host=new Input({host:'a'}),group=new Input({group:'web'}),all=new Input({allHosts:''}),set=new Input({set:'base'}),plate={innerHTML:''};
 const root={innerHTML:'',querySelector:s=>s==='#recipe-plate-content'?plate:s==='[data-all-hosts]'?all:null,querySelectorAll:s=>s==='[data-dish]'?dishes:s==='[data-host]'?[host]:s==='[data-group]'?[group]:s==='[data-set]'?[set]:s==='[data-host], [data-group], [data-all-hosts]'?[host,group,all]:[]};
 mountMenuLayout(root,{data,profiles,profile:'main',e,onProfile(){}});
 dishes[1].checked=true;dishes[1].events.change();assert.ok(dishes.every(i=>i.checked));
 group.checked=true;group.events.change();assert.match(plate.innerHTML,/主機 <span>2/);
 dishes[0].checked=false;dishes[0].events.change();assert.ok(dishes.every(i=>!i.checked));
 set.events.click();set.events.click();assert.match(plate.innerHTML,/Recipes <span>0/);assert.match(plate.innerHTML,/套餐 <span>1/);assert.match(plate.innerHTML,/<summary><strong>套餐/);
});

test('source lists stack Bundle above User and omit empty User sections',()=>{
 const html=renderLayout(data,groupRecipes(data),profiles,'main',e);
 const hardware=html.slice(html.indexOf('data-domain="hardware"'),html.indexOf('data-domain="storage"'));
 assert.match(hardware,/Bundle recipes/);assert.doesNotMatch(hardware,/User recipes/);
 const network=html.slice(html.indexOf('data-domain="network"'),html.indexOf('data-domain="workloads"'));
 assert.ok(network.indexOf('Bundle recipes')<network.indexOf('User recipes'));
 assert.match(network,/<p class="menu-capability-scope">No event source<\/p>/);
});

test('domain disclosures start closed and Scopes is a peer of recipe source headings',()=>{
 const html=renderLayout(data,groupRecipes(data),profiles,'main',e);
 assert.match(html,/<details class="panel menu-domain" data-domain="hardware"><summary><h2>硬體與環境/);
 assert.doesNotMatch(html,/<details class="panel menu-domain"[^>]* open/);
 assert.match(html,/<h3>Scopes<\/h3>/);
});

test('an unchanged Profile and browser origin retain the plate across product checkout updates',()=>{
 const values=new Map(),key='opsfeast-menu-draft-v2:same-profile-root';
 values.set(key,JSON.stringify({recipes:['inventory'],hosts:['a'],meals:['base'],scopes:{}}));
 const storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
 const initial=JSON.parse(values.get(key));
 const makeRoot=()=>{
  const plate={innerHTML:''},all={};
  return {plate,innerHTML:'',querySelector:s=>s==='#recipe-plate-content'?plate:s==='[data-all-hosts]'?all:null,querySelectorAll:()=>[]};
 };
 for(const productVersion of ['old-checkout','new-checkout']){
  const root=makeRoot();
  mountMenuLayout(root,{data:{...data,preferences:{scope_id:'same-profile-root'},items:data.items.map(item=>({...item,version:productVersion}))},profiles,profile:'main',e,storage,onProfile(){}});
  assert.match(root.plate.innerHTML,/主機 <span>1/);assert.match(root.plate.innerHTML,/Recipes <span>1/);assert.match(root.plate.innerHTML,/套餐 <span>1/);
  assert.deepEqual(JSON.parse(values.get(key)),initial);
 }
});
