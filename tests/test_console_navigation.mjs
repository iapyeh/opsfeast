import test from 'node:test';
import assert from 'node:assert/strict';
import {readerLocation,readerLink,readerScope,contentWindow} from '../web/assets/console-navigation.mjs';

test('live, historical and block URLs keep exact session and optional scope',()=>{
  for(const history of [false,true])for(const bid of [null,'block/one']){
    const scope={profile:'lab & test',host_id:'a/b'},url=readerLink('session/one',{history,bid,scope});
    const parsed=new URL(url,'http://localhost');
    assert.deepEqual(readerLocation(parsed.pathname),{sid:'session/one',history,bid});
    assert.deepEqual(readerScope({host_id:'lab & test / a/b'},parsed.search),scope);
    assert.equal(readerScope({host_id:'other / a/b'},parsed.search),null);
    assert.equal(readerScope({host_id:'lab / web'},''),null);
  }
  assert.deepEqual(readerScope({host_id:'Shared',targets:[{profile:'lab',host_id:'guest'}]},'?profile=lab&host_id=guest'),{profile:'lab',host_id:'guest'});
  assert.equal(readerScope({host_id:'Shared',targets:[{profile:'lab',host_id:'guest'}]},'?profile=other&host_id=guest'),null);
  assert.equal(contentWindow({size:20000},16384,true),3616);
  assert.equal(contentWindow({size:20000},20000,true),0);
  assert.equal(contentWindow({size:20000},20000,false),16384);
});

// Exercise the actual page module with a small DOM and recorded HTTP transport.
// No dependency on a browser package, managed host or running Web server.
class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.childNodes=[];this.textContent='';this.hidden=false;this.dataset={};this.events={};this.classes=new Set();this.classList={add:(...xs)=>xs.forEach(x=>this.classes.add(x)),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
  get children(){return this.childNodes;}
  focus(){this.focused=true;document.activeElement=this;}
  contains(node){return this===node||this.childNodes.some(c=>c.contains(node));}
  querySelectorAll(selector){return elements(this).slice(1).filter(el=>el.tagName===selector.toUpperCase());}
  click(){this.events.click?.();}
  append(el){el.parentNode=this;this.childNodes.push(el);}
  insertBefore(el,before){if(el.parentNode){if(el.contains(document.activeElement))document.activeElement=null;const old=el.parentNode.childNodes;old.splice(old.indexOf(el),1);}el.parentNode=this;this.childNodes.splice(this.childNodes.indexOf(before),0,el);}
  replaceChildren(...els){this.childNodes=els;this.textContent='';}
  setAttribute(key,value){this[key]=value;}
  addEventListener(name,fn){this.events[name]=fn;}
}
function elements(root){return [root,...root.childNodes.flatMap(elements)];}
function setup(history,secretRequest=false){
  const ids=new Map(['title','target','cursor','identity','toolbar','state','activity','breadcrumb','mode','new-window','history-view','connection','transcript','follow','latest'].map(id=>[id,new Element()]));
  ids.get('transcript').append(ids.get('activity'));
  const cleanup=[];
  globalThis.document={activeElement:null,getElementById:id=>ids.get(id)||[...ids.values()].flatMap(elements).find(el=>el.id===id),createElement:tag=>new Element(tag)};
  globalThis.location={pathname:'/console/fixture'+(history?'/history':''),search:'?profile=lab&host_id=web-01'};
  globalThis.window={addEventListener:(name,fn)=>cleanup.push(fn)};
  const base={title:'same task title',created_at:'2026-01-01T00:00:00Z',head:'output',tail:'tail',lines:1,revision:1};
  const snapshot={session:{session_id:'fixture',host_id:'lab / web-01',title:'inspection',activity:{state:'thinking',expires_at:'2999-01-01T00:00:00Z'}},seq:5,blocks:[
    {...base,id:'command',position:1,kind:'command',status:'streaming',size:6},
    {...base,id:'analysis',position:4,kind:'analysis',status:'completed',size:6},
    {...base,id:'output',position:2,kind:'stdout',status:'streaming',size:30000},
    {...base,id:'form',position:3,kind:'form',status:'waiting',size:6,form:{fields:[],choices:[{id:'yes',label:'approve'}]},response:null},
  ]};
  const calls=[],streams=[];
  globalThis.fetch=async(url,options={})=>{
    calls.push({url,options});
    if(url.endsWith('/secret-requests'))return {ok:true,json:async()=>({requests:secretRequest?[{request_id:'fixture-secret',label:'Synthetic password',state:'waiting'}]:[]})};
    if(url.includes('/stream?'))return {ok:true,body:{getReader:()=>({read:()=>new Promise(resolve=>streams.push(resolve))})}};
    if(url.includes('/content?')){
      const query=new URL(url,'http://localhost').searchParams,offset=Number(query.get('offset')),limit=Number(query.get('limit'));
      return {ok:true,json:async()=>({text:'x'.repeat(limit),next_offset:offset+limit,total_bytes:40000})};
    }
    return {ok:true,json:async()=>structuredClone(snapshot)};
  };
  return {ids,calls,cleanup,snapshot,streams};
}
test('history page never streams, animates or submits forms; expansion stops at loaded byte size',async()=>{
  const {ids,calls,cleanup}=setup(true);
  await import('../web/assets/console-reader.mjs?history-fixture');
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.length,2);assert.equal(calls[0].url,'/api/v1/console-sessions/fixture');
  assert.match(document.title,/Console 紀錄（唯讀）.*fixture/);
  assert.equal(ids.get('activity').hidden,true);
  const all=elements(ids.get('transcript'));
  assert.equal(all.filter(el=>el.tagName==='FORM').length,0);
  assert.equal(all.some(el=>el.classes.has('processing')),false);
  const analysis=all.find(el=>el.dataset.blockId==='analysis');
  assert.equal(elements(analysis).find(el=>el.tagName==='H2').hidden,true);
  assert.equal(elements(analysis).find(el=>el.tagName==='A').hidden,false);
  assert.equal(elements(analysis).find(el=>el.tagName==='PRE').textContent,'output\n⋯\ntail');
  const output=all.find(el=>el.dataset.blockId==='output');
  const buttons=elements(output).filter(el=>el.tagName==='BUTTON');
  await buttons[0].onclick();await buttons[1].onclick();
  assert.equal(new URL(calls.at(-1).url,'http://localhost').searchParams.get('limit'),'13616');
  assert.equal(buttons[1].hidden,true);
  assert.equal(elements(output).find(el=>el.className==='full-content').textContent.length,30000);
  assert.ok(calls.every(call=>call.options.method==='GET'||call.url.endsWith('/reader-events')));
  const notice=calls.filter(call=>call.url.endsWith('/reader-events'));assert.equal(notice.length,1);assert.deepEqual(JSON.parse(notice[0].options.body),{view:'history',block_id:null,seen_seq:5});
  assert.ok(elements(output).some(el=>el.href==='/console/fixture/history/blocks/output?profile=lab&host_id=web-01'));
  assert.match(ids.get('connection').textContent,/唯讀紀錄/);
  cleanup.forEach(fn=>fn());
});
test('live page streams only its own session and keeps live form replies explicitly scoped',async()=>{
  const {ids,calls,cleanup}=setup(false);
  try{
    await import('../web/assets/console-reader.mjs?live-fixture');
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(calls.at(-1).url,'/api/v1/console-sessions/fixture/stream?after=5');
    const notice=calls.filter(call=>call.url.endsWith('/reader-events'));assert.equal(notice.length,1);assert.deepEqual(JSON.parse(notice[0].options.body),{view:'live',block_id:null,seen_seq:5});
    assert.match(document.title,/互動河道/);
    assert.equal(ids.get('transcript').childNodes.at(-1),ids.get('activity'));
    const analysis=elements(ids.get('transcript')).find(el=>el.dataset.blockId==='analysis');
    assert.equal(elements(analysis).find(el=>el.tagName==='H2').hidden,true);
    assert.equal(elements(analysis).find(el=>el.tagName==='A').hidden,false);
    const form=elements(ids.get('transcript')).find(el=>el.tagName==='FORM');
    assert.ok(form);
    globalThis.crypto??=(await import('node:crypto')).webcrypto;
    await form.onsubmit({preventDefault(){},submitter:{value:'yes'}});
    assert.ok(calls.some(call=>call.url==='/api/v1/console-sessions/fixture/blocks/form/responses'&&call.options.method==='POST'));
    assert.equal(ids.get('history-view').href,'/console/fixture/history?profile=lab&host_id=web-01');
  }finally{cleanup.forEach(fn=>fn());}
});

test('reader keeps text selection open and copies full content without folding',async()=>{
  const {ids,cleanup}=setup(true);
  const navigator=Object.getOwnPropertyDescriptor(globalThis,'navigator');
  let copied='', selected='';
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:{
    writeText:async text=>{copied=text;},
  }}});
  window.getSelection=()=>({toString:()=>selected});
  try{
    await import('../web/assets/console-reader.mjs?copy-fixture');
    await new Promise(resolve=>setImmediate(resolve));
    const output=elements(ids.get('transcript')).find(el=>el.dataset.blockId==='output');
    const row=elements(output).find(el=>el.className==='source-line');
    const copy=elements(output).find(el=>el.className==='text-control block-copy');
    selected='a text selection';
    output.click();
    row.click();
    assert.equal(output.classes.has('block-closed'),false);
    selected='';
    row.click();
    assert.equal(output.classes.has('block-closed'),true);
    await copy.onclick();
    assert.equal(copied,'x'.repeat(30000));
    assert.equal(output.classes.has('block-closed'),true);
    assert.match(ids.get('connection').textContent,/已複製/);
  }finally{
    if(navigator)Object.defineProperty(globalThis,'navigator',navigator);
    else delete globalThis.navigator;
    cleanup.forEach(fn=>fn());
  }
});

test('host and block toggles preserve chronology, loaded content, drafts and new-stream defaults',async()=>{
 const {ids,calls,cleanup,snapshot,streams}=setup(false);
 snapshot.session.host_id='Shared investigation';snapshot.session.targets=[
  {id:'lab / guest',profile:'lab',host_id:'guest',icon:'🦉'},
  {id:'lab / hypervisor',profile:'lab',host_id:'hypervisor',icon:'🖥'}];
 snapshot.blocks[0].target_id='lab / guest';snapshot.blocks[1].target_id='lab / guest';snapshot.blocks[2].target_id='lab / hypervisor';snapshot.blocks[3].target_id='lab / hypervisor';
 snapshot.blocks[3].form.fields=[{name:'note',label:'Note',type:'text',required:false}];
 try{
  await import('../web/assets/console-reader.mjs?shared-fixture');await new Promise(resolve=>setImmediate(resolve));
  const tabs=ids.get('toolbar').children.find(el=>el.id==='host-tabs');assert.equal(tabs.children.length,3);assert.deepEqual(tabs.children.map(b=>b['aria-pressed']),['true','true','true']);
  const articles=()=>ids.get('transcript').children.filter(el=>el.dataset.blockId);
  const order=articles().map(el=>el.dataset.blockId);
  const output=articles().find(el=>el.dataset.blockId==='output'),analysis=articles().find(el=>el.dataset.blockId==='analysis');
  await elements(output).find(el=>el.tagName==='BUTTON').onclick();
  const full=elements(output).find(el=>el.className==='full-content'),text=full.textContent;
  const form=elements(ids.get('transcript')).find(el=>el.tagName==='FORM'),input=elements(form).find(el=>el.tagName==='INPUT');
  input.value='keep draft';input.events.input();
  tabs.children[1].click();assert.deepEqual(tabs.children.map(b=>b['aria-pressed']),['false','false','true']);
  assert.equal(output.classes.has('block-closed'),false);assert.equal(analysis.classes.has('block-closed'),true);tabs.children[2].click();assert.equal(output.classes.has('block-closed'),true);assert.equal(articles().find(el=>el.dataset.blockId==='form').classes.has('block-closed'),false);
  assert.deepEqual(articles().map(el=>el.dataset.blockId),order);
  const arrow=elements(output).find(el=>el.tagName==='A');assert.equal(arrow.hidden,true);assert.equal(arrow.target,'_blank');assert.equal(arrow.rel,'noopener');assert.match(arrow.href,/blocks\/output/);
  assert.equal(elements(analysis).find(el=>el.tagName==='A').hidden,true);
  const time=elements(output).find(el=>el.className==='source-time'),row=elements(output).find(el=>el.className==='source-line');assert.equal(row.children[0],time);assert.equal(time.hidden,false);assert.ok(time.textContent);
  const toggle=elements(output).find(el=>el.className==='text-control block-toggle');assert.equal(toggle.hidden,false);assert.equal(toggle.textContent,'↓');toggle.onclick();assert.equal(output.classes.has('block-closed'),false);assert.equal(arrow.hidden,false);assert.equal(toggle.hidden,false);assert.equal(toggle.textContent,'↑');assert.equal(toggle.parentNode.children.at(-1),toggle);toggle.onclick();assert.equal(output.classes.has('block-closed'),true);assert.equal(arrow.hidden,true);assert.equal(toggle.textContent,'↓');assert.equal(time.hidden,false);assert.equal(tabs.children[0]['aria-pressed'],'false');assert.equal(tabs.children[2]['aria-pressed'],'false');
  streams.shift()({done:false,value:new TextEncoder().encode('data: '+JSON.stringify({session_id:'fixture',seq:6,type:'block.appended',block:{...snapshot.blocks[2],revision:2,head:'new host output'}})+'\n\n')});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(output.classes.has('block-closed'),true);assert.deepEqual(articles().map(el=>el.dataset.blockId),order);
  tabs.children[2].click();assert.equal(output.classes.has('block-closed'),false);assert.equal(analysis.classes.has('block-closed'),true);assert.equal(full.textContent,text);assert.equal(input.value,'keep draft');
  const source=elements(output).find(el=>el.className==='source-line');source.events.keydown({key:'Enter',preventDefault(){}});assert.equal(output.classes.has('block-closed'),true);assert.equal(elements(output).find(el=>el.className==='source-suffix').textContent,'new host output');source.events.keydown({key:' ',preventDefault(){}});assert.equal(output.classes.has('block-closed'),false);
  const waiting=articles().find(el=>el.dataset.blockId==='form');elements(waiting).find(el=>el.className==='source-line').events.keydown({key:'Enter',preventDefault(){}});assert.equal(waiting.classes.has('block-closed'),false);
  streams.shift()({done:false,value:new TextEncoder().encode('data: '+JSON.stringify({session_id:'fixture',seq:7,type:'block.created',block:{...snapshot.blocks[0],id:'new-guest',position:6,head:'first line\nsecond line'}})+'\n\n')});
  await new Promise(resolve=>setImmediate(resolve));
  const incoming=articles().find(el=>el.dataset.blockId==='new-guest');assert.equal(incoming.classes.has('block-closed'),true);assert.equal(tabs.children[1]['aria-pressed'],'false');assert.equal(elements(incoming).find(el=>el.className==='source-suffix').textContent,'first line');
  tabs.children[0].click();assert.equal(articles().some(el=>el.classes.has('block-closed')),false);assert.deepEqual(tabs.children.map(b=>b['aria-pressed']),['true','true','true']);
  assert.equal(calls.filter(c=>c.url.includes('/content?')).length,1);assert.equal(calls.filter(c=>c.url.endsWith('/reader-events')).length,1);
 }finally{cleanup.forEach(fn=>fn());}
});

test('secret input retains focus across polling and newly streamed blocks without moving its subtree',async()=>{
 const {ids,cleanup,snapshot,streams}=setup(false,true);
 try{
  await import('../web/assets/console-reader.mjs?focus-regression');await new Promise(resolve=>setImmediate(resolve));
  const input=elements(ids.get('transcript')).find(el=>el.tagName==='INPUT'&&el.type==='password');assert.ok(input);
  input.focus();input.value='synthetic-unsent';
  await new Promise(resolve=>setTimeout(resolve,1100));
  assert.equal(document.activeElement,input);assert.equal(input.value,'synthetic-unsent');
  const block={...snapshot.blocks[0],id:'new-block',position:5,kind:'stdout',head:'next result',tail:'',status:'completed'};
  streams.shift()({done:false,value:new TextEncoder().encode('data: '+JSON.stringify({session_id:'fixture',seq:6,type:'block.created',block})+'\n\n')});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(document.activeElement,input);assert.equal(input.value,'synthetic-unsent');
  const children=ids.get('transcript').children,secret=document.getElementById('secret-input');
  assert.ok(children.indexOf(children.find(el=>el.dataset.blockId==='new-block'))<children.indexOf(secret));
 }finally{cleanup.forEach(fn=>fn());}
});
