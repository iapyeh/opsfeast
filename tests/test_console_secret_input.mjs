import test from 'node:test';
import assert from 'node:assert/strict';
import {mountSecretInput} from '../web/assets/console-secret-input.mjs';
function element(tag='section'){
 return {tagName:tag.toUpperCase(),children:[],attributes:{},textContent:'',value:'',disabled:false,
 append(child){this.children.push(child);},replaceChildren(...nodes){this.children=nodes;},setAttribute(k,v){this.attributes[k]=v;},
 querySelectorAll(selector){return this.children.flatMap(c=>[...(selector==='input'&&c.tagName==='INPUT'?[c]:[]),...c.querySelectorAll(selector)]);}};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const doc={createElement:element};
const response=data=>({ok:true,status:200,json:async()=>data});
const all=(root,tag)=>root.children.flatMap(c=>[...(c.tagName===tag?[c]:[]),...all(c,tag)]);
test('masked single-use input clears before transport, never retries, and cleans on page departure',async()=>{
 const root=element(),calls=[];let resolveSubmit,visibleUpdates=0;
 const stop=mountSecretInput(root,{api:'/api/session/exact',document:doc,onChange:()=>{assert.equal(all(root,'INPUT').length,1);visibleUpdates++;},fetcher:async(url,options)=>{
  calls.push({url,options});
  if(options.method==='GET')return response({requests:[{request_id:'one',label:'MySQL password <script>',state:'waiting'}]});
  return new Promise(resolve=>{resolveSubmit=resolve;});
 }});
 await flush();
 assert.equal(visibleUpdates,1,'the reader is notified after mounting input so it can reveal the field');
 const form=all(root,'FORM')[0],input=all(root,'INPUT')[0];
 assert.equal(input.type,'password');assert.equal(input.autocomplete,'off');assert.equal(form.autocomplete,'off');
 input.value='synthetic-secret';const pending=form.onsubmit({preventDefault(){}});
 assert.equal(input.value,'');assert.equal(input.disabled,true);
 assert.equal(JSON.parse(calls.at(-1).options.body).value,'synthetic-secret');
 await form.onsubmit({preventDefault(){}});assert.equal(calls.filter(c=>c.options.method==='POST').length,1);
 resolveSubmit(response({state:'submitted'}));await pending;
 assert.equal(all(root,'INPUT').length,0);stop();assert.equal(root.children.length,0);
});
test('failed delivery erases input and does not automatically resend',async()=>{
 const root=element();let posts=0;
 const stop=mountSecretInput(root,{api:'/exact',document:doc,fetcher:async(url,options)=>{
  if(options.method==='GET')return response({requests:[{request_id:'r',label:'Password',state:'waiting'}]});
  posts++;throw Error('offline');
 }});
 await flush();const form=all(root,'FORM')[0],input=all(root,'INPUT')[0];input.value='synthetic';
 await form.onsubmit({preventDefault(){}});assert.equal(input.value,'');assert.equal(posts,1);
 await form.onsubmit({preventDefault(){}});assert.equal(posts,1);stop();
});
test('cancel posts no credential and erases the unsent password',async()=>{
 const root=element(),writes=[];
 const stop=mountSecretInput(root,{api:'/exact',document:doc,fetcher:async(url,options)=>{
  if(options.method==='GET')return response({requests:[{request_id:'r',label:'Password',state:'waiting'}]});
  writes.push({url,body:options.body});return response({state:'cancelled'});
 }});
 await flush();const input=all(root,'INPUT')[0];input.value='never-send-this';
 await all(root,'BUTTON')[1].onclick();assert.equal(input.value,'');assert.equal(writes[0].body,'{}');
 assert.match(writes[0].url,/\/r\/cancel$/);stop();
});
