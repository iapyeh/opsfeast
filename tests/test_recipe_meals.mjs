import test from 'node:test';
import assert from 'node:assert/strict';
import {mealEntries,renderMealDetail,readMealForm} from '../web/assets/recipe-meals.mjs';
import {renderRecipeCatalog,filterRecipes} from '../web/assets/recipe-catalog.mjs';
import {renderSetEditor} from '../web/assets/locales/recipe-menu-zh-TW.mjs';
import {loginDestination} from '../web/assets/login-navigation.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const child={id:'child',title:'Child <meal>',description:'Synthetic',recipes:[':valid'],meals:[],selections:{}};
const parent={id:'parent',title:'Parent',description:'Outer',recipes:[],meals:['child'],selections:{}};
const data={items:[{reference:':valid',title:'Valid',runnable:true},{reference:':draft',title:'Draft',status:'success',runnable:false}],sets:[{...parent,id:'bundle:foundation'}],user_sets:[child,parent]};
test('combined list is a table of review links without per-row operations',()=>{
 const meals=mealEntries(data),html=renderRecipeCatalog([...data.items,...meals],{e,profile:'main'});
 assert.match(html,/<table/);assert.match(html,/meal=child/);assert.match(html,/recipe=%3Avalid/);
 assert.doesNotMatch(html,/<button|加入執行餐盤|修改套餐|刪除套餐/);
 assert.deepEqual(filterRecipes(meals,{kind:'meal',status:'runnable'}).map(m=>m.id),['bundle:foundation','child','parent']);
});
test('meal readiness retains empty, missing, draft and cyclic states and nested results',()=>{
 const invalid=[{...child,id:'empty',recipes:[]},{...child,id:'draft',recipes:[':draft']},{...child,id:'missing',recipes:[':missing']},{...child,id:'cycle',recipes:[],meals:['cycle']}];
 const entries=mealEntries({...data,user_sets:[...data.user_sets,...invalid]});
 assert.ok(entries.filter(m=>invalid.some(i=>i.id===m.id)).every(m=>!m.runnable));
 assert.ok(entries.find(m=>m.id==='parent').runnable);
});
test('meal detail owns edit/delete/add actions; Bundle definitions remain read-only',()=>{
 const meals=mealEntries(data),html=renderMealDetail(meals.find(m=>m.id==='child'),data,{e,profile:'qa&profile'});
 assert.match(html,/id="meal-edit"/);assert.match(html,/id="meal-delete"/);assert.match(html,/\/recipe-plate\?meal=child&amp;profile=qa%26profile/);
 assert.match(html,/meal=parent/);assert.match(html,/Child &lt;meal&gt;/);assert.doesNotMatch(html,/<meal>/);
 const bundle=renderMealDetail(meals[0],data,{e,profile:'main'});assert.match(bundle,/Bundle 套餐為唯讀/);assert.doesNotMatch(bundle,/id="meal-edit"|id="meal-delete"/);
});
test('meal editor excludes itself and unselected drafts, retaining exact references',()=>{
 const html=renderSetEditor(data,child,e,{heading:'修改套餐'});
 assert.match(html,/<h2>修改套餐<\/h2>/);assert.match(html,/data-set-recipe value=":valid"/);
 assert.doesNotMatch(html,/data-set-meal value="child"|data-set-recipe value=":draft"/);
 assert.match(html,/data-set-meal value="parent"/);
 const compiled={reference:'system/inventory/overview',title:'Overview',runnable:true,is_meal:true};
 const preserved=renderSetEditor({...data,items:[...data.items,compiled]},{...child,recipes:[compiled.reference]},e);
 assert.match(preserved,/data-set-recipe value="system\/inventory\/overview" checked/);
});
test('meal form emits only definition and selected scopes, never host/privilege state',()=>{
 const previous=globalThis.FormData;
 globalThis.FormData=class{get(name){return name==='title'?'  Updated meal  ':'Description';}};
 const form={querySelectorAll:s=>s==='[data-set-recipe]:checked'?[{value:':valid'}]:s==='[data-set-meal]:checked'?[{value:'bundle:foundation'}]:[]};
 try{assert.deepEqual(readMealForm(form),{title:'Updated meal',description:'Description',recipes:[':valid'],meals:['bundle:foundation'],selections:{}});}finally{globalThis.FormData=previous;}
});
test('login preserves exact meal management and plate destinations',()=>{
 for(const next of ['/recipes?meal=new','/recipes?meal=bundle%3Afoundation','/recipes?kind=meal','/recipe-plate?meal=child'])assert.equal(loginDestination('?next='+encodeURIComponent(next)),next);
});

test('nested agent meals retain static readiness but offer recipe prompts rather than Web execution',()=>{
 const catalog={...data,items:[{...data.items[0],launch:{mode:'agent',prompt:'Synthetic task.'}},data.items[1]]};
 const meal=mealEntries(catalog).find(m=>m.id==='parent');assert.equal(meal.runnable,true);
 const html=renderMealDetail(meal,catalog,{e,profile:'main'});
 assert.match(html,/複製建議 prompt/);assert.match(html,/recipe=%3Avalid/);assert.doesNotMatch(html,/加入執行餐盤/);
});
