import test from 'node:test';
import assert from 'node:assert/strict';
import {renderCard,renderBlueprint,renderReview,renderRun,readVariables,mountRecipeMenu,readInventorySelection} from '../web/assets/recipe-menu.mjs';
import {loginDestination} from '../web/assets/login-navigation.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const item={reference:'<ref>',title:'<title>',purpose:'purpose',limitation:'explicit gap',domain:'identity',source:'repository',runnable:true,kind:'operation',platforms:{implemented:['linux']},inputs:{variables:{limit:{type:'integer',default:100},flag:{type:'boolean'},context:{type:'object'}}}};
test('menu explains purpose limits metadata and typed inputs without executing',()=>{
 const html=renderCard(item,true,e);assert.match(html,/explicit gap/);assert.match(html,/data-select="&lt;ref&gt;"/);assert.match(html,/沿用已配置值/);assert.match(html,/不是密碼輸入介面/);assert.doesNotMatch(html,/<title>|<ref>/);assert.match(html,/recipe-dish-selected/);
});
test('typed overrides preserve false zero empty string semantics and reject incorrect types',()=>{
 const defs={flag:{type:'boolean'},count:{type:'integer'},context:{type:'object'},name:{type:'string'}};
 assert.deepEqual(readVariables(new Map([['flag','false'],['count','0'],['context','{}'],['name','hello']]),defs),{flag:false,count:0,context:{},name:'hello'});
 assert.deepEqual(readVariables(new Map([['name','']]),defs),{});
 assert.throws(()=>readVariables(new Map([['context','[]']]),defs));assert.throws(()=>readVariables(new Map([['count','true']]),defs));
});
test('blueprint differentiates partial supply from undeveloped integration',()=>{
 const html=renderBlueprint({domains:[{id:'identity'}],capabilities:[{id:'identity.accounts',domain:'identity',observation_kind:'inventory',integration:'partial',scope_note:'<scope>'},{id:'identity.activity',domain:'identity',observation_kind:'events',integration:'not_integrated',scope_note:'gap'}]},e);
 assert.match(html,/1 項部分供應、1 項尚未整合/);assert.match(html,/不是|並非整項完成/);assert.match(html,/&lt;scope&gt;/);assert.match(html,/登入與特權使用事件/);
});
test('review requires confirmation and explains identity enabled overrides consumers stop limitations',()=>{
 const html=renderReview({profile:'<profile>',timeout:30,worker_deadline_seconds:600,pairs:[{reference:'ref',version:'1',host_id:'node',access_mode:'read',identity:{login_user:'user',requested:{via:'sudo',user:'root'},inventory_root_selection:true},variable_names:['limit'],invocation:['recipes','run','ref'],side_effects:['<effect>']}]},e);
 assert.match(html,/id="recipe-start" disabled/);assert.match(html,/root/);assert.match(html,/身分尚未連線驗證/);assert.match(html,/enabled/);assert.match(html,/consumers/);assert.match(html,/遠端命令停止與清理仍需另外確認/);assert.doesNotMatch(html,/<effect>|<profile>/);
});
test('run evidence preserves partial receipts interruptions unknown cleanup and escaped progress',()=>{
 const html=renderRun({id:'id',profile:'main',state:'stopped',remote_cleanup:'unknown',tasks:[{host_id:'node',reference:'ref',state:'partial',progress:'<script>secret</script>',local_termination:'confirmed',result:{retention:{status:'failed'},content_update:{status:'failed'}}}]},e);
 assert.match(html,/部分完成/);assert.match(html,/failed/);assert.match(html,/遠端清理未知/);assert.match(html,/target="_blank" rel="noopener" href="\/hosts\?profile=main&amp;host=node/);assert.doesNotMatch(html,/<script>/);assert.doesNotMatch(html,/id="recipe-stop"/);
});
test('login retains the exact recipe selection or saved run without open redirects',()=>{
 assert.equal(loginDestination('?next='+encodeURIComponent('/recipes?profile=main&run=id')),'/recipes?profile=main&run=id');
 for(const next of ['//evil/recipes','/recipes?command=bad','/recipes?profile=a&profile=b','/recipes#bad'])assert.equal(loginDestination('?next='+encodeURIComponent(next)),'/workspace');
});
test('mount preserves explicit Profile and discovery never sends a mutation',async()=>{
 class Element {innerHTML='';textContent='';nodes={};events={};querySelector(s){return this.nodes[s]??=new Element();}querySelectorAll(){return [];}addEventListener(n,f){this.events[n]=f;}}
 const root=new Element(),calls=[];
 await mountRecipeMenu(root,{e,search:'?profile=other',profiles:{default_profile:'main',profiles:[{name:'main'},{name:'other'}]},fetchImpl:async(path,options)=>{
  calls.push([path,options]);return {ok:true,json:async()=>path.includes('recipe-menu')?{items:[],sets:[],sources:[],hosts:[],status:'success',blueprint:{capabilities:[],domains:[]}}:{items:[]}};
 }});
 assert.match(calls[0][0],/recipe-menu\?profile=other/);assert.equal(calls.length,1);assert.ok(calls.every(([,o])=>!o.method));
 assert.match(root.innerHTML,/挑選這次需要的菜色/);assert.match(root.querySelector('#recipe-plate-content').innerHTML,/尚未挑選 Recipes/);
});

test('inventory picker defaults exclude sensors; job and individual property selections are explicit',()=>{
 const catalog={jobs:{'hardware-baseline':{title:'Hardware',enabled:true},'hardware-sensors':{title:'Sensors',enabled:false}},properties:{'sensors.fans':{job:'hardware-sensors',unit:'rpm',description:'Fan speed'}}};
 const html=renderCard({...item,inventory_catalog:catalog},false,e);
 assert.match(html,/name="_inventory_mode" value="default" checked/);assert.match(html,/value="hardware-baseline" checked/);assert.match(html,/value="hardware-sensors"  data-default="no"/);assert.match(html,/sensors.fans/);assert.match(html,/需明確選取/);
 const form=(mode,values)=>({get:()=>mode,getAll:()=>values});
 assert.equal(readInventorySelection(form('default',[]),catalog),undefined);
 assert.deepEqual(readInventorySelection(form('jobs',['hardware-sensors']),catalog),{jobs:['hardware-sensors']});
 assert.deepEqual(readInventorySelection(form('properties',['sensors.fans']),catalog),{properties:['sensors.fans']});
 assert.throws(()=>readInventorySelection(form('properties',[]),catalog));
});
