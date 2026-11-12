import test from 'node:test';
import assert from 'node:assert/strict';
import {noteMarkup,noteMatches} from '../web/assets/host-notes.mjs';
import {encodedFiles,folderFiles,mountBundleUpload} from '../web/assets/note-bundles.mjs';
import {loginDestination} from '../web/assets/login-navigation.mjs';
import {mountBundleReader} from '../web/assets/note-bundle-reader.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const note={uuid:'note-id',title:'Note',content:'Plain text',source:'user',timestamp:'2026-11-12T00:00:00Z',attachments:[{uuid:'bundle-id',title:'<Report>',entry:'report.md',kind:'markdown',file_count:2}]};
test('attachment identity stays scoped and metadata joins note search without executing markup',()=>{
 const html=noteMarkup(note,e,{profile:'lab',host_id:'node'});
 assert.match(html,/&lt;Report&gt;/);assert.doesNotMatch(html,/<Report>/);
 assert.match(html,/profile=lab&amp;host_id=node&amp;note_uuid=note-id&amp;bundle_uuid=bundle-id/);
 assert.match(html,/target="_blank" rel="noopener noreferrer"/);
 assert.equal(noteMatches(note,{query:'report.md'}),true);
});
test('folder upload preserves nested paths and exact bytes, rejecting size limits before reading',async()=>{
 const file=new File([new Uint8Array([0,255,10])],'a.png');Object.defineProperty(file,'webkitRelativePath',{value:'report/images/a.png'});
 assert.equal(folderFiles([file])[0].path,'images/a.png');
 assert.deepEqual(await encodedFiles([file]),[{path:'images/a.png',base64:'AP8K'}]);
 await assert.rejects(encodedFiles([{size:17*1024*1024,name:'large'}]),/單檔/);
 await assert.rejects(encodedFiles([]),/256/);
});
function node(){return {value:'',textContent:'',disabled:false,files:[]};}
test('ZIP save uses the reviewed host/note/revision and reports conflicts without retries',async()=>{
 const form={elements:{title:{value:'Report'},entry:{value:'index.md'},archive:{files:[new File(['zip'],'report.zip')]},folder:{files:[]}}};
 const message=node(),controls=[node(),node()],cancel=node();
 const target={innerHTML:'',querySelector:selector=>selector==='form'?form:selector==='#bundle-cancel'?cancel:message,querySelectorAll:()=>controls};
 const calls=[];let saved=false;
 mountBundleUpload(target,{scope:{profile:'lab',host_id:'node'},note,revision:'revision-1',e,request:async(path,options)=>{calls.push({path,options});throw {code:'note_revision_conflict'};},onSaved:()=>saved=true,onCancel(){}});
 await form.onsubmit({preventDefault(){}});
 assert.equal(calls.length,1);assert.equal(saved,false);assert.match(message.textContent,/筆記已變更/);
 const url=new URL(calls[0].path,'http://local.invalid');assert.equal(url.searchParams.get('note_uuid'),'note-id');assert.equal(url.searchParams.get('expected_revision'),'revision-1');assert.equal(calls[0].options.headers['Content-Type'],'application/zip');assert.ok(controls.every(c=>!c.disabled));
});
test('HTML reader waits for an explicit click, uses an opaque sandbox, and can stop the frame',async(t)=>{
 const original=Object.getOwnPropertyDescriptor(globalThis,'document');t.after(()=>{if(original)Object.defineProperty(globalThis,'document',original);else delete globalThis.document;});
 let frame=null;const elements=new Map();
 const get=key=>{if(!elements.has(key))elements.set(key,{...node(),innerHTML:'',querySelector:selector=>selector==='iframe'?frame:get(selector),replaceChildren(value){frame=value;}});return elements.get(key);};
 const root={innerHTML:'',querySelector:get};
 Object.defineProperty(globalThis,'document',{configurable:true,value:{createElement(){return {attrs:{},setAttribute(k,v){this.attrs[k]=v;},remove(){frame=null;}};}}});
 let deferred=false,release;
 const calls=[];const request=async(path,options)=>{
  if(deferred&&path.endsWith('/preview'))await new Promise(resolve=>release=resolve);
  calls.push({path,options});return {ok:true,json:async()=>path.endsWith('/preview')?{url:'http://127.0.0.1:19000/narrow-token/files/index.html',expires_in:60}:{bundle:{title:'Interactive',kind:'html',entry:'index.html',created_at:'time'},files:[],warnings:[]}};
 };
 const stop=await mountBundleReader(root,{search:'?profile=lab&host_id=node&note_uuid=note&bundle_uuid=bundle',request});t.after(stop);
 assert.equal(calls.length,1);assert.equal(frame,null);
 await get('#bundle-open-preview').onclick();assert.equal(calls.length,2);
 assert.deepEqual(frame.attrs,{sandbox:'allow-scripts'});assert.equal(frame.referrerPolicy,'no-referrer');assert.equal(calls[1].options.method,'POST');
 get('#bundle-stop-preview').onclick();assert.equal(frame,null);
 deferred=true;const pending=get('#bundle-open-preview').onclick();get('#bundle-stop-preview').onclick();release();await pending;assert.equal(frame,null);
});

test('login retains the exact attachment context and rejects duplicate, foreign or extra keys',()=>{
 const next='/note-attachments?profile=lab&host_id=node&note_uuid=note&bundle_uuid=bundle';
 assert.equal(loginDestination('?next='+encodeURIComponent(next)),next);
 for(const url of [next+'&profile=other',next+'&next=https://example.invalid',next+'#extra','https://example.invalid'+next])assert.equal(loginDestination('?next='+encodeURIComponent(url)),'/workspace');
});
