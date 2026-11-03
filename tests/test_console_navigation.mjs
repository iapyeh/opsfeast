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
  assert.equal(contentWindow({size:20000},16384,true),3616);
  assert.equal(contentWindow({size:20000},20000,true),0);
  assert.equal(contentWindow({size:20000},20000,false),16384);
});

// Exercise the actual page module with a small DOM and recorded HTTP transport.
// No dependency on a browser package, managed host or running Web server.
class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.childNodes=[];this.textContent='';this.hidden=false;this.dataset={};this.classes=new Set();this.classList={add:(...xs)=>xs.forEach(x=>this.classes.add(x)),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
  append(el){this.childNodes.push(el);}
  insertBefore(el,before){this.childNodes.splice(this.childNodes.indexOf(before),0,el);}
  replaceChildren(...els){this.childNodes=els;this.textContent='';}
  setAttribute(key,value){this[key]=value;}
  addEventListener(){}
}
function elements(root){return [root,...root.childNodes.flatMap(elements)];}
function setup(history){
  const ids=new Map(['title','target','cursor','identity','toolbar','state','activity','breadcrumb','mode','new-window','history-view','connection','transcript','follow','latest'].map(id=>[id,new Element()]));
  ids.get('transcript').append(ids.get('activity'));
  const cleanup=[];
  globalThis.document={getElementById:id=>ids.get(id),createElement:tag=>new Element(tag)};
  globalThis.location={pathname:'/console/fixture'+(history?'/history':''),search:'?profile=lab&host_id=web-01'};
  globalThis.window={addEventListener:(name,fn)=>cleanup.push(fn)};
  const base={title:'same task title',created_at:'2026-01-01T00:00:00Z',head:'output',tail:'tail',lines:1,revision:1};
  const snapshot={session:{session_id:'fixture',host_id:'lab / web-01',title:'inspection',activity:{state:'thinking',expires_at:'2999-01-01T00:00:00Z'}},seq:5,blocks:[
    {...base,id:'command',position:1,kind:'command',status:'streaming',size:6},
    {...base,id:'output',position:2,kind:'stdout',status:'streaming',size:30000},
    {...base,id:'form',position:3,kind:'form',status:'waiting',size:6,form:{fields:[],choices:[{id:'yes',label:'approve'}]},response:null},
  ]};
  const calls=[];
  globalThis.fetch=async(url,options={})=>{
    calls.push({url,options});
    if(url.includes('/stream?'))return {ok:true,body:{getReader:()=>({read:()=>new Promise(()=>{})})}};
    if(url.includes('/content?')){
      const query=new URL(url,'http://localhost').searchParams,offset=Number(query.get('offset')),limit=Number(query.get('limit'));
      return {ok:true,json:async()=>({text:'x'.repeat(limit),next_offset:offset+limit,total_bytes:40000})};
    }
    return {ok:true,json:async()=>structuredClone(snapshot)};
  };
  return {ids,calls,cleanup};
}
test('history page never streams, animates or submits forms; expansion stops at loaded byte size',async()=>{
  const {ids,calls,cleanup}=setup(true);
  await import('../web/assets/console-reader.mjs?history-fixture');
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/v1/console-sessions/fixture');
  assert.match(document.title,/Console 紀錄（唯讀）.*fixture/);
  assert.equal(ids.get('activity').hidden,true);
  const all=elements(ids.get('transcript'));
  assert.equal(all.filter(el=>el.tagName==='FORM').length,0);
  assert.equal(all.some(el=>el.classes.has('processing')),false);
  const output=all.find(el=>el.dataset.blockId==='output');
  const buttons=elements(output).filter(el=>el.tagName==='BUTTON');
  await buttons[0].onclick();await buttons[1].onclick();
  assert.equal(new URL(calls.at(-1).url,'http://localhost').searchParams.get('limit'),'13616');
  assert.equal(buttons[1].hidden,true);
  assert.equal(elements(output).find(el=>el.className==='full-content').textContent.length,30000);
  assert.ok(calls.every(call=>call.options.method==='GET'));
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
    assert.match(document.title,/互動河道/);
    assert.equal(ids.get('transcript').childNodes.at(-1),ids.get('activity'));
    const form=elements(ids.get('transcript')).find(el=>el.tagName==='FORM');
    assert.ok(form);
    globalThis.crypto??=(await import('node:crypto')).webcrypto;
    await form.onsubmit({preventDefault(){},submitter:{value:'yes'}});
    assert.ok(calls.some(call=>call.url==='/api/v1/console-sessions/fixture/blocks/form/responses'&&call.options.method==='POST'));
    assert.equal(ids.get('history-view').href,'/console/fixture/history?profile=lab&host_id=web-01');
  }finally{cleanup.forEach(fn=>fn());}
});
