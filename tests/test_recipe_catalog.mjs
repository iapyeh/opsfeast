import test from 'node:test';
import assert from 'node:assert/strict';
import {filterRecipes,renderRecipeCatalog,mountRecipeCatalog} from '../web/assets/recipe-catalog.mjs';
import {mountMenuLayout} from '../web/assets/recipe-menu-layout.mjs';
import {mountRecipeMenu} from '../web/assets/recipe-menu.mjs';
import {loginDestination} from '../web/assets/login-navigation.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const items=[
 {reference:'system/network/check/port',title:'Port check',purpose:'Network reachability',source:'repository',version:'1.0',status:'success',runnable:true},
 {reference:':finance/rate',title:'USD <rate>',purpose:'Monthly quote',source:'profile',status:'success',runnable:false},
 {reference:'team:system/network/check/custom',title:'External',purpose:'Review errors',source:'team',status:'failed',runnable:false,errors:['<unsafe>']}
];
test('catalog filters exact source, draft state, category and human search independently',()=>{
 assert.deepEqual(filterRecipes(items,{status:'unavailable',source:'profile'}).map(i=>i.reference),[':finance/rate']);
 assert.deepEqual(filterRecipes(items,{status:'runnable',category:'network',q:'REACHABILITY'}),[items[0]]);
 assert.deepEqual(filterRecipes(items,{source:'team',status:'unavailable'}),[items[2]]);
 assert.deepEqual(filterRecipes(items,{source:'profile',category:'network'}),[]);
});
test('review list includes drafts and safe exact links without execution controls',()=>{
 const html=renderRecipeCatalog(items,{e,profile:'qa&profile'});
 assert.doesNotMatch(html,/草稿/);assert.match(html,/<table/);assert.doesNotMatch(html,/<button|加入執行餐盤/);assert.match(html,/USD &lt;rate&gt;/);
 assert.match(html,/\/recipes\?recipe=%3Afinance%2Frate&amp;profile=qa%26profile/);
 assert.match(html,/可執行/);assert.match(html,/不可執行/);
 assert.doesNotMatch(html,/add=%3Afinance|add=team|data-host|data-dish|recipe-preview|<unsafe>|<rate>/);

 assert.match(renderRecipeCatalog([],{e,profile:'main'}),/沒有符合條件/);
});
class Element {
 innerHTML='';textContent='';value='';events={};nodes={};
 querySelector(s){return this.nodes[s]??=new Element();}
 querySelectorAll(){return [];}
 addEventListener(name,handler){this.events[name]=handler;}
}
test('catalog mounts read-only using saved default Profile and refresh preserves filters',async()=>{
 const root=new Element(),calls=[];let updated=false;
 await mountRecipeCatalog(root,{e,profiles:{default_profile:'main'},search:'?profile=other&status=unavailable',fetchImpl:async(path,options)=>{
  calls.push([path,options]);return {ok:true,json:async()=>({status:'success',items:updated?items.slice(0,1):items,sources:[{name:'repository',status:'available'},{name:'profile',status:'available'}],preferences:{categories:[],revision:'fixture'}})};
 }});
 assert.equal(calls[0][0],'/api/v1/recipe-menu?profile=main');
 assert.match(root.querySelector('#recipe-catalog-items').innerHTML,/USD &lt;rate&gt;/);
 assert.doesNotMatch(root.querySelector('#recipe-catalog-items').innerHTML,/Port check/);
 assert.match(root.innerHTML,/前往執行餐盤/);assert.doesNotMatch(root.innerHTML,/recipe-hosts|recipe-preview/);
 updated=true;await root.querySelector('#recipe-catalog-refresh').events.click({target:{}});
 assert.match(root.querySelector('#recipe-catalog-items').innerHTML,/沒有符合條件/);
 assert.ok(calls.every(([,options])=>!options.method));
});
test('catalog reports discovery failure instead of an empty list',async()=>{
 const root=new Element();await mountRecipeCatalog(root,{e,profiles:{default_profile:'main'},fetchImpl:async()=>({ok:false,status:401,json:async()=>({})})});
 assert.match(root.innerHTML,/role="alert"/);assert.match(root.innerHTML,/請先登入/);
});
test('add link merges with restored plate and ignores draft references',()=>{
 let stored=JSON.stringify({recipes:[items[0].reference],hosts:['synthetic-host'],meals:[]});
 const data={items:[...items,{reference:':other',title:'Other',runnable:true}],hosts:[{host_id:'synthetic-host'}],groups:[],sets:[],blueprint:{},preferences:{scope_id:'fixture'}};
 const storage={getItem:()=>stored,setItem:(_,value)=>{stored=value;}};
 mountMenuLayout(new Element(),{data,profile:'main',profiles:{},initialRecipe:':other',e,storage});
 assert.deepEqual(JSON.parse(stored).recipes,[items[0].reference,':other']);assert.deepEqual(JSON.parse(stored).hosts,['synthetic-host']);
 mountMenuLayout(new Element(),{data,profile:'main',profiles:{},initialRecipe:':finance/rate',e,storage});
 assert.ok(!JSON.parse(stored).recipes.includes(':finance/rate'));
});
test('login preserves catalog reviews and plate scope with strict separate destinations',()=>{
 for(const next of ['/recipes?recipe=%3Afinance%2Frate','/recipes?status=unavailable&source=profile','/recipe-plate?add=%3Afinance%2Frate','/recipe-plate?history=1','/recipe-plate?run=fixture'])assert.equal(loginDestination('?next='+encodeURIComponent(next)),next);
 for(const next of ['/recipes?run=old','/recipe-plate?recipe=wrong','/recipe-plate?run=a&run=b','//evil/recipe-plate','/recipe-plate#bad'])assert.equal(loginDestination('?next='+encodeURIComponent(next)),'/workspace');
});
test('plate consumes add query so reset and reload do not re-add the recipe',async()=>{
 const previous=globalThis.window;let destination;
 globalThis.window={history:{replaceState:(_,__,url)=>{destination=url;}}};
 try {
  const root=new Element();await mountRecipeMenu(root,{e,profiles:{default_profile:'main'},search:'?add=system%2Fnetwork%2Fcheck%2Fport',fetchImpl:async()=>({ok:true,json:async()=>({status:'success',items,hosts:[],groups:[],sets:[],blueprint:{}})})});
  assert.equal(destination,'/recipe-plate?profile=main');
  assert.match(root.querySelector('#recipe-plate-content').innerHTML,/Port check/);
  root.querySelector('#menu-reset-plate').events.click();
  assert.doesNotMatch(root.querySelector('#recipe-plate-content').innerHTML,/Port check/);
 }finally{globalThis.window=previous;}
});
