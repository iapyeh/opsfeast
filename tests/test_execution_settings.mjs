import test from 'node:test';
import assert from 'node:assert/strict';
import {mountExecutionSettings} from '../web/assets/execution-settings.mjs';
import {renderSettingsTree} from '../web/assets/settings-hub.mjs';
import {getMessages} from '../web/assets/i18n.mjs';
const e=v=>String(v).replaceAll('<','&lt;');
class Element {
 constructor(){this.events={};this.nodes={};this.value='8';this.innerHTML='';this.textContent='';}
 querySelector(s){return this.nodes[s]??=new Element();}
 addEventListener(n,f){this.events[n]=f;}
}
test('execution defaults are an installation settings entry',()=>{
 const html=renderSettingsTree({categories:[{id:'execution',parent:null,route:'/settings/execution',status:'available'}]},null,{m:getMessages('zh-TW'),e});
 assert.match(html,/執行設定/);assert.match(html,/\/settings\/execution/);
});
test('settings save validates threads and uses the current revision without starting work',async()=>{
 const root=new Element(),calls=[];
 await mountExecutionSettings(root,{e,fetchImpl:async(path,options)=>{calls.push([path,options]);return {ok:true,json:async()=>({threads:options.method==='PUT'?3:8,revision:options.method==='PUT'?'new':'old'})};}});
 assert.match(root.innerHTML,/主機台數不限/);
 const form=root.querySelector('form'),input=root.querySelector('#execution-default-threads');
 input.value='0';await form.events.submit({preventDefault(){}});assert.equal(calls.length,1);
 input.value='3';await form.events.submit({preventDefault(){}});
 assert.equal(calls.length,2);assert.equal(calls[1][1].method,'PUT');assert.deepEqual(JSON.parse(calls[1][1].body),{threads:3,expected_revision:'old'});
 assert.match(root.querySelector('#execution-settings-status').textContent,/已儲存/);
});
test('settings conflict preserves entered value for review',async()=>{
 const root=new Element();let count=0;
 await mountExecutionSettings(root,{e,fetchImpl:async()=>({ok:count++===0,status:409,json:async()=>({threads:8,revision:'old'})})});
 root.querySelector('#execution-default-threads').value='4';
 await root.querySelector('form').events.submit({preventDefault(){}});
 assert.equal(root.querySelector('#execution-default-threads').value,'4');
 assert.match(root.querySelector('#execution-settings-status').textContent,/其他頁面修改/);
});
