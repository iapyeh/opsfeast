import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewPlate as reviewPlateRaw} from '../web/assets/recipe-execution.mjs';
import {readScopeEditors,groupRecipes} from '../web/assets/recipe-menu-layout.mjs';
import {renderScopeEditor,renderSetEditor,renderReview,copy} from '../web/assets/locales/recipe-menu-zh-TW.mjs';
// Standard settings fixture; individual tests track preview/start requests only.
function reviewPlate(root,options){
 return reviewPlateRaw(root,{...options,api:(path,body)=>path==='/api/v1/recipe-execution/settings'?Promise.resolve({threads:8}):options.api(path,body)});
}
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
 await start.events.click();assert.deepEqual(calls[1],['/api/v1/recipe-runs',{preview_id:'reviewed',confirmed:true,threads:8}]);assert.equal(started[0].id,'run');
});
test('failed preview leaves an edit path and never sends a start request',async()=>{
 const root=new Node(),calls=[];
 await reviewPlate(root,{profile:'main',selection:{},e,api:async path=>{calls.push(path);throw new Error('<changed>');},onEdit(){},onStarted(){throw Error('must not start');}});
 assert.equal(calls.length,1);assert.equal(root.querySelector('#recipe-execution-error').textContent,'<changed>');assert.match(root.innerHTML,/返回選菜/);assert.equal(root.querySelector('#recipe-start').disabled,true);
});
test('review exposes host connection grouping and conditional permission boundaries',()=>{
 const html=renderReview({pairs:[],connection_groups:[{host_id:'<node>',composition:{members:[{reference:item.reference,routines:[{id:'sense',required_permission:'login',platforms:['linux'],properties:['sensors.fans']},{id:'identity',required_permission:'root',platforms:['linux'],properties:['hardware.serial']}]}]}}]},e);
 assert.match(html,/共用一個主機連線/);assert.match(html,/sense · login/);assert.match(html,/identity · root/);assert.match(html,/&lt;node&gt;/);
});

test('concise review groups recipes over hosts and keeps technical information closed',()=>{
 const pair={reference:'hardware',host_id:'a',access_mode:'read',identity:{},variable_names:['limit'],invocation:['PRIVATE_TECHNICAL_ARG'],side_effects:[],inventory_selection:{mode:'properties',jobs:['hardware'],properties:['cpu']}};
 const html=renderReview({profile:'main',timeout:30,pairs:[pair,{...pair,host_id:'b'}]},e,{items:[{reference:'hardware',title:'硬體盤點',purpose:'主機規格'}],hosts:[{host_id:'a',title:'<Host A>'},{host_id:'b',title:'Host B'}]});
 const simple=html.slice(0,html.indexOf('<details class="panel recipe-review-details"'));
 assert.match(simple,/2 台主機 · 1 道 recipes · 2 項工作/);
 assert.equal((simple.match(/<tr>/g)||[]).length,2);
 assert.match(simple,/硬體盤點/);assert.match(simple,/&lt;Host A&gt;、Host B/);assert.match(simple,/1 個採集欄位/);assert.doesNotMatch(simple,/<th scope="col">主機<\/th>/);assert.equal((simple.match(/class="panel recipe-reviewed-hosts"/g)||[]).length,1);
 assert.doesNotMatch(simple,/PRIVATE_TECHNICAL_ARG|fingerprint/);
 assert.match(html,/<details class="panel recipe-review-details"><summary>/);assert.doesNotMatch(html,/<details open/);
 assert.equal((html.match(/id="recipe-start"/g)||[]).length,1);
 assert.equal((html.match(/id="recipe-confirm"/g)||[]).length,1);
 assert.match(html,/確認執行這 2 項工作/);
});


test('thread validation explains invalid values in human language',()=>{
 assert.match(copy.failure('invalid_recipe_threads'),/大於零的整數/);
});

test('threads is sent only at start and never requires another plate preview',async()=>{
 const root=new Node(),calls=[],started=[];
 const plan={preview_id:'reviewed',profile:'main',pairs:[],timeout:30,worker_deadline_seconds:600};
 await reviewPlate(root,{profile:'main',selection:{hosts:['node'],recipes:[]},e,api:async(path,body)=>{calls.push([path,body]);return path.endsWith('/preview')?plan:{id:'started'};},onEdit(){},onStarted:run=>started.push(run)});
 assert.doesNotMatch(root.innerHTML,/套用並重新檢閱|id="recipe-repreview"/);
 const confirm=root.querySelector('#recipe-confirm'),start=root.querySelector('#recipe-start'),threads=root.querySelector('#recipe-threads');
 confirm.checked=true;confirm.events.change();threads.value='2';threads.events.input();
 assert.equal(start.disabled,false);assert.equal(confirm.checked,true);
 assert.equal(calls.length,1);assert.equal('threads' in calls[0][1],false);
 await start.events.click();assert.equal(calls.length,2);
 assert.deepEqual(calls[1],['/api/v1/recipe-runs',{preview_id:'reviewed',confirmed:true,threads:2}]);assert.equal(started.length,1);
});


test('review shows the dish and shared host summary immediately while validation is pending',async()=>{
 const root=new Node();let resolve;const requests=[];
 const waiting=new Promise(done=>{resolve=done;});
 const pair={reference:'hardware',host_id:'a',access_mode:'read',identity:{},variable_names:[],invocation:[]};
 const pending=reviewPlate(root,{profile:'main',selection:{hosts:['a'],recipes:[{reference:'hardware'}]},catalog:{items:[{reference:'hardware',title:'硬體盤點',kind:'operation'}],hosts:[{host_id:'a',title:'Host A'}]},e,api:async(path)=>{requests.push(path);return waiting;},onEdit(){},onStarted(){throw Error('must not start');}});
 assert.match(root.innerHTML,/硬體盤點/);assert.match(root.innerHTML,/Host A/);
 assert.equal(root.querySelector('#recipe-confirm').disabled,true);assert.equal(root.querySelector('#recipe-start').disabled,true);
 const threads=root.querySelector('#recipe-threads');threads.value='2';threads.events.input();
 resolve({preview_id:'verified',profile:'main',pairs:[pair],threads:8,timeout:30});await pending;
 assert.equal(threads.value,'2');assert.equal(root.querySelector('#recipe-start').disabled,true);
 assert.equal(requests.length,1);
});

test('returning to the plate prevents a late validation response from replacing it',async()=>{
 const root=new Node();let resolve;
 const waiting=new Promise(done=>{resolve=done;});
 const pending=reviewPlate(root,{profile:'main',selection:{hosts:[],recipes:[]},e,api:()=>waiting,onEdit(){root.innerHTML='returned-to-plate';},onStarted(){throw Error('must not start');}});
 root.querySelector('#recipe-edit').events.click();
 resolve({profile:'main',pairs:[],threads:8,timeout:30});await pending;
 assert.equal(root.innerHTML,'returned-to-plate');
});


test('threads shows 8 immediately and independently loads a saved default before the plan',async()=>{
 const root=new Node();let finishPlan;
 const waiting=new Promise(done=>{finishPlan=done;});
 const pending=reviewPlateRaw(root,{profile:'main',selection:{hosts:[],recipes:[]},e,api:path=>path==='/api/v1/recipe-execution/settings'?Promise.resolve({threads:3}):waiting,onEdit(){},onStarted(){throw Error('must not start');}});
 assert.match(root.innerHTML,/id="recipe-threads"[^>]*value="8"/);
 await new Promise(done=>setImmediate(done));
 assert.equal(root.querySelector('#recipe-threads').value,3);
 assert.equal(root.querySelector('#recipe-start').disabled,true);
 finishPlan({profile:'main',pairs:[],threads:3,timeout:30});await pending;
});

test('late default settings do not replace a manually entered threads value',async()=>{
 const root=new Node();let finishPlan,finishDefaults;
 const plan=new Promise(done=>{finishPlan=done;}),defaults=new Promise(done=>{finishDefaults=done;});
 const pending=reviewPlateRaw(root,{profile:'main',selection:{hosts:[],recipes:[]},e,api:path=>path==='/api/v1/recipe-execution/settings'?defaults:plan,onEdit(){},onStarted(){throw Error('must not start');}});
 const threads=root.querySelector('#recipe-threads');threads.value='2';threads.events.input();
 finishDefaults({threads:3});await new Promise(done=>setImmediate(done));
 assert.equal(threads.value,'2');
 finishPlan({profile:'main',pairs:[],threads:3,timeout:30});await pending;
 assert.equal(threads.value,'2');
});
