import test from 'node:test';
import assert from 'node:assert/strict';
import {operationalSearch,pinnedFetch} from '../web/assets/default-profile.mjs';
import {renderLayout} from '../web/assets/locales/recipe-menu-zh-TW.mjs';
import {renderProfileCards} from '../web/assets/profiles-settings.mjs';
import {getMessages} from '../web/assets/i18n.mjs';
const e=x=>String(x).replaceAll('<','&lt;').replaceAll('"','&quot;');
test('daily links ignore foreign Profile and clear its host/result/recipe scope',()=>{
 assert.equal(operationalSearch('/recipes','?profile=other&run=old&host=shared','main'),'');
 assert.equal(operationalSearch('/hosts','?profile=main&host=shared','main'),'?host=shared');
 assert.equal(operationalSearch('/settings/recipes','?profile=other&recipe=private','main'),'?profile=other&recipe=private');
});
test('pinned requests detect changed default without retry or changing request targets',async()=>{
 const calls=[];let changed=0;
 const fetch=pinnedFetch(async(...args)=>{calls.push(args);return new Response(JSON.stringify({detail:'default_profile_changed_reload'}),{status:409});},'main',{origin:'http://localhost',onChanged:()=>changed++});
 const response=await fetch('/api/v1/recipe-runs',{method:'POST',body:'{}'});
 assert.equal(calls.length,1);assert.equal(changed,1);assert.equal(response.status,409);
 assert.equal(calls[0][1].headers.get('X-OpsFeast-Default-Profile'),'main');assert.equal(calls[0][1].body,'{}');
 await fetch('https://unrelated.example/data');assert.equal(calls[1][1].headers,undefined);
});
test('recipe host picker has only default label, no alternate Profile selector',()=>{
 const html=renderLayout({status:'success',items:[],sets:[],hosts:[],groups:[],user_sets:[]},[],{profiles:[{name:'main'},{name:'SHOULD_NOT_APPEAR'}]},'main',e);
 assert.doesNotMatch(html,/recipe-profile|SHOULD_NOT_APPEAR/);assert.match(html,/預設 Profile/);
});
test('Profile settings offers transfer/detach/delete and protects main/default',()=>{
 const html=renderProfileCards({default_profile:'lab',profiles:[{name:'main',status:'available',root:'/main'},{name:'lab',status:'available',root:'/lab'},{name:'other',status:'available',root:'/other'}]},{m:getMessages('zh-TW'),e});
 assert.match(html,/data-profile-export="main"/);assert.match(html,/data-profile-detach="lab"/);assert.match(html,/data-profile-delete="other"/);
 assert.doesNotMatch(html,/data-profile-delete="lab"|data-profile-delete="main"|data-profile-detach="main"/);
});

test('Unicode defaults are encoded safely for HTTP headers',async()=>{
 let value;
 const fetch=pinnedFetch(async(input,options)=>{value=options.headers.get('X-OpsFeast-Default-Profile');return new Response('{}');},'團隊 盤點',{origin:'http://localhost'});
 await fetch('/api/v1/profiles');assert.equal(decodeURIComponent(value),'團隊 盤點');
});
