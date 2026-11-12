import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {formatNoteTimestamp,noteMarkup,mountHostNotes} from '../web/assets/host-notes.mjs';
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
test('notes display Taipei timestamps to seconds and escape every data field',()=>{
 assert.equal(formatNoteTimestamp('2026-11-03T11:43:01+00:00'),'2026-11-03 19:43:01+08:00');
 assert.equal(formatNoteTimestamp('2026-11-03T16:00:01Z'),'2026-11-04 00:00:01+08:00');
 const html=noteMarkup({title:'<img>',content:'<script>alert(1)</script>\n  indented  notes\n\n\tlast line',uuid:'" onfocus="x',source:'user',timestamp:'2026-11-03T11:43:01Z'},escape);
 assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<img>'));assert.ok(html.includes('&lt;script&gt;'));assert.ok(html.includes('19:43:01+08:00'));
 assert.ok(html.includes('\n  indented  notes\n\n\tlast line'));
 assert.doesNotMatch(html,/style=/);
 const css=readFileSync(new URL('../web/assets/workbench.css',import.meta.url),'utf8');
 assert.match(css,/\.host-note-content\s*\{[^}]*white-space:\s*pre-wrap;[^}]*overflow-wrap:\s*anywhere/s);
});
// Small semantic DOM fake exercises actual event handlers and HTTP payloads.
function element(){return {innerHTML:'',textContent:'',value:'',disabled:false,focus(){},showModal(){this.open=true;},close(){this.open=false;},querySelectorAll(){return []}};}
function fixture(){
 const els=new Map();const get=key=>{if(!els.has(key))els.set(key,element());return els.get(key);};
 const root=element();root.querySelector=get;root.querySelectorAll=()=>[];
 const form=get('form');form.elements={title:element(),content:element(),recipe_references:element(),tags:element()};
 const editor=get('#note-editor');editor.querySelector=key=>key==='form'?form:get(key);editor.querySelectorAll=()=>[];
 const dialog=get('#note-delete-dialog');dialog.querySelector=()=>get('#delete-form');
 const list=get('#notes-list');list.querySelectorAll=selector=>selector==='[data-note-edit]'?[get('edit-button')]:selector==='[data-note-delete]'?[get('delete-button')]:[];
 const note={uuid:'3fdf4d52-d52d-4d1d-b9c3-eed636caa702',title:'Existing',content:'Saved',source:'console',timestamp:'2026-11-03T11:43:01Z'};
 get('edit-button').dataset={noteEdit:note.uuid};get('delete-button').dataset={noteDelete:note.uuid};
 return {root,get,form,note};
}
test('create/edit use user source and current revision, failed saves preserve the draft',async()=>{
 const f=fixture(),calls=[];let conflict=false;
 await mountHostNotes(f.root,{profile:'lab',host_id:'sample',e:escape,request:async(path,options)=>{
  calls.push({path,options});if(options){if(conflict)throw {code:'note_revision_conflict'};return {};}
  return {revision:'revision-1',notes:[f.note]};
 }});
 f.get('#note-add').onclick();f.form.elements.title.value='New';f.form.elements.content.value='Body';
 await f.form.onsubmit({preventDefault(){}});
 let payload=JSON.parse(calls.find(c=>c.options).options.body);assert.equal(payload.changes.source,'user');assert.equal(payload.expected_revision,'revision-1');assert.equal(payload.host_id,'sample');
 f.get('edit-button').onclick();conflict=true;f.form.elements.content.value='Draft';await f.form.onsubmit({preventDefault(){}});
 assert.equal(f.form.elements.content.value,'Draft');assert.match(f.get('#note-status').textContent,/其他人更新/);
 payload=JSON.parse(calls.filter(c=>c.options).at(-1).options.body);assert.equal(payload.note_uuid,f.note.uuid);
});
test('delete is scoped and requires modal confirmation; cancel sends nothing',async()=>{
 const f=fixture(),writes=[];
 await mountHostNotes(f.root,{profile:'lab',host_id:'sample',e:escape,request:async(path,options)=>{
  if(options)writes.push(options);return {revision:'r',notes:[f.note]};
 }});
 f.get('delete-button').onclick();f.get('#note-delete-cancel').onclick();assert.equal(writes.length,0);
 f.get('delete-button').onclick();await f.get('#delete-form').onsubmit({preventDefault(){}});
 const payload=JSON.parse(writes[0].body);assert.equal(writes[0].method,'DELETE');assert.equal(payload.confirmation,f.note.uuid);assert.equal(payload.note_uuid,f.note.uuid);
});

test('structured associations filter exact recipes, general notes and all tags',async()=>{
 const {noteMatches}=await import('../web/assets/host-notes.mjs');
 const n={title:'Title',content:'Body',recipe_references:['system/check',':private/check'],tags:['linux','network']};
 assert.equal(noteMatches(n,{recipe:'bundle:system/check',tags:['LINUX','network']}),true);
 assert.equal(noteMatches(n,{recipe:'system/check-more'}),false);
 assert.equal(noteMatches(n,{recipe:'vendor:system/check'}),false);
 assert.equal(noteMatches(n,{tags:['linux','storage']}),false);
 assert.equal(noteMatches(n,{query:':private/check'}),true);
 assert.equal(noteMatches({title:'General',content:'Body'},{recipe:'system/check',includeGeneral:true}),true);
 assert.equal(noteMatches({title:'General',content:'Body'},{recipe:'system/check'}),false);
 const html=noteMarkup({...n,uuid:'x',source:'agent',timestamp:'2026-11-06T00:00:00Z',tags:['<img>'],recipe_references:['<script>']},escape);
 assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<img>'));
});
test('editor retains and submits metadata and permits explicit clearing',async()=>{
 const f=fixture(),writes=[];f.note.recipe_references=['system/check'];f.note.tags=['linux'];
 await mountHostNotes(f.root,{profile:'lab',host_id:'sample',e:escape,request:async(path,options)=>{
  if(options)writes.push(JSON.parse(options.body));return {revision:'r',notes:[f.note]};
 }});
 f.get('edit-button').onclick();assert.equal(f.form.elements.recipe_references.value,'system/check');assert.equal(f.form.elements.tags.value,'linux');
 await f.form.onsubmit({preventDefault(){}});
 assert.deepEqual(writes[0].changes.recipe_references,['system/check']);assert.deepEqual(writes[0].changes.tags,['linux']);
 f.get('edit-button').onclick();f.form.elements.recipe_references.value='';f.form.elements.tags.value='';await f.form.onsubmit({preventDefault(){}});
 assert.deepEqual(writes[1].changes.recipe_references,[]);assert.deepEqual(writes[1].changes.tags,[]);
});
