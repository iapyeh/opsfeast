import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewPlate} from '../web/assets/recipe-execution.mjs';
import {readScopeEditors,groupRecipes} from '../web/assets/recipe-menu-layout.mjs';
import {renderScopeEditor,renderSetEditor,renderReview} from '../web/assets/locales/recipe-menu-zh-TW.mjs';
const e=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const item={reference:'system/inventory/hardware-sensors',title:'Sensors',inventory_catalog:{jobs:{sensors:{enabled:true}},properties:{'sensors.fans':{job:'sensors',description:'<fan>'},'sensors.temperatures':{job:'sensors'}}}};
test('scope roundtrip preserves exact sensor selection and never treats empty explicit scope as defaults',()=>{
 const section={dataset:{scopeRef:item.reference},querySelector:()=>({value:'properties'}),querySelectorAll:()=>[{value:'sensors.fans'}]};
 const root={querySelectorAll:()=>[section]};
 assert.deepEqual(readScopeEditors(root),{[item.reference]:{properties:['sensors.fans']}});
 assert.deepEqual(readScopeEditors(root,[]),{});
 const html=renderScopeEditor(item,{properties:['sensors.fans']},e);
 assert.match(html,/value="sensors.fans" checked/);assert.doesNotMatch(html,/value="sensors.temperatures" checked/);assert.match(html,/&lt;fan&gt;/);
 const editor=renderSetEditor({items:[item],hosts:[]},{recipes:[item.reference],selections:{[item.reference]:{properties:['sensors.fans']}}},e);
 assert.match(editor,/value="sensors.fans" checked/);
 section.querySelectorAll=()=>[];assert.throws(()=>readScopeEditors(root),/至少/);
 section.querySelector=()=>({value:'default'});assert.deepEqual(readScopeEditors(root),{});
});
test('meal is offered as a set rather than a duplicate recipe dish',()=>{
 const groups=groupRecipes({items:[{reference:'overview',source:'repository',is_meal:true,domain:'hardware'},{...item,source:'repository',domain:'hardware'}],blueprint:{capabilities:[]}});
 assert.equal(groups.flatMap(g=>g.bundle).filter(i=>i.reference==='overview').length,0);
 assert.equal(groups.flatMap(g=>g.bundle).filter(i=>i.reference===item.reference).length,1);
});
class Node {events={};disabled=true;checked=false;textContent='';innerHTML='';nodes={};querySelector(s){return this.nodes[s]??=new Node();}addEventListener(n,f){this.events[n]=f;}}
test('review cannot start before explicit confirmation and sends only the reviewed preview ID',async()=>{
 const root=new Node(),calls=[],started=[];
 const plan={preview_id:'reviewed',profile:'main',pairs:[],connection_groups:[],timeout:30,worker_deadline_seconds:600};
 await reviewPlate(root,{profile:'main',selection:{hosts:['node'],recipes:[]},e,api:async(path,body)=>{calls.push([path,body]);return path.endsWith('preview')?plan:{id:'run'};},onEdit(){},onStarted:run=>started.push(run)});
 const start=root.querySelector('#recipe-start'),confirm=root.querySelector('#recipe-confirm');
 await start.events.click();assert.equal(calls.length,1);
 confirm.checked=true;confirm.events.change();assert.equal(start.disabled,false);
 await start.events.click();assert.deepEqual(calls[1],['/api/v1/recipe-runs',{preview_id:'reviewed',confirmed:true}]);assert.equal(started[0].id,'run');
});
test('failed preview leaves an edit path and never sends a start request',async()=>{
 const root=new Node(),calls=[];
 await reviewPlate(root,{profile:'main',selection:{},e,api:async path=>{calls.push(path);throw new Error('<changed>');},onEdit(){},onStarted(){throw Error('must not start');}});
 assert.equal(calls.length,1);assert.match(root.innerHTML,/&lt;changed&gt;/);assert.match(root.innerHTML,/返回選菜/);
});
test('review exposes host connection grouping and conditional permission boundaries',()=>{
 const html=renderReview({pairs:[],connection_groups:[{host_id:'<node>',composition:{members:[{reference:item.reference,routines:[{id:'sense',required_permission:'login',platforms:['linux'],properties:['sensors.fans']},{id:'identity',required_permission:'root',platforms:['linux'],properties:['hardware.serial']}]}]}}]},e);
 assert.match(html,/共用一個主機連線/);assert.match(html,/sense · login/);assert.match(html,/identity · root/);assert.match(html,/&lt;node&gt;/);
});
