import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeDomains,groupRecipes,applyUserSet} from '../web/assets/recipe-menu-layout.mjs';
import {renderRecipeChoice,renderSet,renderSetEditor,renderSetDelete} from '../web/assets/locales/recipe-menu-zh-TW.mjs';
import {declaredFields,renderDeclarations,fieldTree,renderDetail} from '../web/assets/locales/recipe-detail-zh-TW.mjs';
import {defaultChanges,renderRecords} from '../web/assets/recipe-detail.mjs';
const e=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const item={reference:':system/network/check/local',title:'<Local>',source:'profile',runnable:true};
const data={items:[item],hosts:[{host_id:'node',title:'Node'}],blueprint:{capabilities:[]},custom_categories:[{id:'user-a',title:'Owner'}]};
test('recipe title is an independent exact-reference page link with a labelled checkbox',()=>{
 const html=renderRecipeChoice(item,e,'main');
 assert.match(html,/href="\/recipes\?profile=main&amp;recipe=%3Asystem%2Fnetwork%2Fcheck%2Flocal"/);
 assert.match(html,/target="_blank" rel="noopener"/);assert.match(html,/aria-label="挑選 &lt;Local&gt;"/);assert.doesNotMatch(html,/<label[^>]*>.*<a /);
});
test('manual classifications override path inference including explicit uncategorized',()=>{
 assert.deepEqual(recipeDomains({...item,category_ids:['user-a','hardware']}),['user-a','hardware']);
 assert.deepEqual(recipeDomains({...item,category_ids:[]}),['custom']);
 const groups=groupRecipes({...data,items:[{...item,category_ids:['user-a']}]});assert.equal(groups.find(g=>g.id==='user-a').user.length,1);
});
test('draft restores direct recipes and preserves meal references separately',()=>{
 const applied=applyUserSet(data,{recipes:[item.reference,item.reference,':gone'],hosts:['node','node','gone'],meals:['bundle:foundation']});
 assert.equal(applied.recipes.size,1);assert.equal(applied.hosts.size,1);assert.deepEqual([...applied.meals],['bundle:foundation']);
});
test('meal cards and creation preserve nested references without host or edit controls',()=>{
 const child={id:'child',title:'Inner',description:'',recipes:[item.reference],meals:[]};
 const saved={id:'a',title:'<Meal>',description:'Scope',recipes:[],meals:['child'],selections:{}};
 const catalog={...data,sets:[],user_sets:[child,saved]};
 const html=renderSet(saved,catalog,true,e,'main');assert.match(html,/<details/);assert.doesNotMatch(html,/data-edit-set=/);assert.match(html,/data-delete-set=/);assert.match(html,/Inner/);assert.match(html,/&lt;Meal&gt;/);
 const editor=renderSetEditor(catalog,{...saved,recipes:[':gone',item.reference]},e);assert.match(editor,/:gone/);assert.match(editor,/請移除後儲存/);assert.doesNotMatch(editor,/data-set-host/);assert.match(editor,/data-set-meal/);
 assert.match(renderSetDelete(child,e,catalog),/將同時從以下套餐移除引用：&lt;Meal&gt;/);
 assert.match(renderSet({...saved,meals:[]},catalog,true,e,'main'),/空套餐/);
});
test('default changes parse typed values, keep strings literal, remove overrides and skip protected inputs',()=>{
 const rows=[['count',true,'7'],['text',true,'raw'],['reset',false,'9']].map(([name,checked,value])=>({dataset:{option:name},querySelector:s=>s==='[data-override]'?{checked}:{value}}));
 const variables=[{name:'count',editable:true,definition:{type:'integer'}},{name:'text',editable:true,definition:{type:'string'}},{name:'reset',editable:true,configured:true},{name:'secret',editable:false}];
 assert.deepEqual(defaultChanges({querySelectorAll:()=>rows},variables),{changes:{count:7,text:'raw'},remove:['reset']});
 rows[0].querySelector=()=>({checked:true,value:'bad'});assert.throws(()=>defaultChanges({querySelectorAll:()=>rows},variables),SyntaxError);
});
test('saved data preserves status/time and escapes hostile contents, unavailable is not empty',()=>{
 const html=renderRecords({status:'success',items:[{host_id:'node',status:'partial',observed_at:'2026-11-10T00:00:00Z',namespace:'a',record_id:'id',data_preview:'<script>bad</script>'}],next_offset:5},e,'main',item.reference);
 assert.match(html,/partial/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);assert.match(html,/data-records-more="5"/);
 assert.match(renderRecords({status:'unavailable',reason_code:'unavailable'},e,'main',item.reference),/不代表沒有採集紀錄/);
});

test('declared schema fields form a bounded readable summary while raw contract remains collapsed',()=>{
 const declarations={retention:{data_schema:{properties:{users:{type:'array',items:{properties:{name:{type:'string'}}}}}}}};
 assert.deepEqual(declaredFields(declarations).map(f=>f.id),['users','users[].name']);
 const html=renderDeclarations(declarations,e);assert.match(html,/users\[\]\.name/);assert.doesNotMatch(html,/<details open/);
});

test('field tree groups dotted paths under closed root and intermediate branches',()=>{
 const fields=[{id:'system.hostname',description:'<host>'},{id:'system.kernel_name'},{id:'network.ipv4.address'}];
 const tree=fieldTree(fields);assert.deepEqual(tree.map(n=>n.name),['system','network']);
 assert.equal(tree[0].children.size,2);assert.equal(tree[1].children.get('ipv4').children.get('address').id,'network.ipv4.address');
 const html=renderDeclarations({inventory:{properties:Object.fromEntries(fields.map(f=>[f.id,f]))}},e);
 assert.match(html,/<summary><strong>system<\/strong><\/summary>/);assert.doesNotMatch(html,/<details[^>]*open/);assert.match(html,/&lt;host&gt;/);
});
test('exact matching field options live with the field and are not repeated among common options',()=>{
 const variables=[{name:'port',definition:{type:'integer'},editable:true,base_present:true,base_value:80,value_present:true,value:80},{name:'timeout',definition:{type:'number'},editable:true}];
 const data={profile:'main',recipe:{reference:':local',title:'Local',source:'profile'},defaults:{variables},preferences:{},declarations:{retention:{fields:{port:{type:'integer'}}}},saved:{status:'success',hosts:[],items:[]},reports:{items:[]}};
 const html=renderDetail(data,[],e);
 assert.equal((html.match(/data-option="port"/g)||[]).length,1);
 assert.ok(html.indexOf('data-option="port"')<html.indexOf('共用選項與儲存'));
 assert.ok(html.indexOf('data-option="timeout"')>html.indexOf('共用選項與儲存'));
 assert.doesNotMatch(html,/id="recipe-new-category"/);assert.match(html,/前往 Recipes 管理自訂分類/);
 assert.equal((html.match(/id="recipe-default-form"/g)||[]).length,1);
});

test('array-item paths stay inside their array field rather than becoming another root',()=>{
 const tree=fieldTree([{id:'users',type:'array'},{id:'users[].name',type:'string'}]);
 assert.equal(tree.length,1);assert.equal(tree[0].name,'users');assert.equal(tree[0].field.type,'array');assert.equal(tree[0].children.get('name').id,'users[].name');
});
