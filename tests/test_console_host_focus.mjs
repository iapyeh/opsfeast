import test from 'node:test';
import assert from 'node:assert/strict';
import {hostList,hostPresentation,focusedIdentity,mountHostTabs} from '../web/assets/console-host-focus.mjs';
import {consume,activityState} from '../web/assets/console-reader-state.mjs';
const targets=[{id:'lab / guest',profile:'lab',host_id:'guest',icon:'🦉'},{id:'lab / host',profile:'lab',host_id:'host',icon:'🖥'}];
const session={session_id:'shared',targets};
test('host folding preserves chronology, common analysis and stable source colors through updates',()=>{
 const blocks=[{id:'a',position:1,target_id:targets[0].id},{id:'b',position:2,target_id:targets[1].id},{id:'c',position:3,kind:'analysis'}];
 const view=blocks.map(b=>({...b,...hostPresentation(session,b,new Set([targets[1].id]))}));
 assert.deepEqual(view.map(b=>b.id),['a','b','c']);assert.deepEqual(view.map(b=>b.muted),[false,true,false]);
 assert.equal(view[1].label,'🖥 host');assert.equal(view[0].tone,0);assert.equal(view[1].tone,1);
 assert.equal(hostPresentation(session,{...blocks[1],status:'streaming',head:'new output'},new Set([targets[1].id])).muted,true);
 assert.deepEqual(blocks.map(b=>hostPresentation(session,b).muted),[false,false,false]);
 assert.equal(hostPresentation(session,blocks[1],new Set([targets[1].id])).tone,1);
 assert.deepEqual(hostList({host_id:'single'}),[]);
});
test('identity and activity are scoped without one host clearing another',()=>{
 const blocks=targets.map((t,i)=>({kind:'identity',target_id:t.id,id:String(i)}));
 assert.equal(focusedIdentity(blocks,targets[0].id).id,'0');assert.equal(focusedIdentity(blocks,null).id,'1');
 const now=Date.now(),thinking={state:'thinking',expires_at:new Date(now+30000).toISOString()};
 const initial={session,seq:0,blocks:[]};
 const next=consume(initial,{session_id:'shared',seq:1,type:'activity.updated',activity:null,target_activities:{[targets[0].id]:{state:'idle'},[targets[1].id]:thinking}});
 assert.equal(activityState(next,now).thinking,true);assert.equal(activityState(next,now+30000).thinking,false);
});
test('tabs support clicks and keyboard navigation without parsing host text as HTML',t=>{
 const previous=globalThis.document;
 function element(){return {children:[],attrs:{},dataset:{},events:{},textContent:'',append(el){this.children.push(el);},replaceChildren(){this.children=[];},setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,v){this.events[k]=v;},focus(){this.focused=true;},click(){this.events.click();}};}
 globalThis.document={createElement:element};t.after(()=>globalThis.document=previous);
 const root=element();let selected=null;const closed=new Set();const tabs=mountHostTabs(root,id=>{selected=id;if(id===null)closed.clear();else if(closed.has(id))closed.delete(id);else closed.add(id);tabs.render(session,closed);});tabs.render(session);
 assert.equal(root.children.length,3);assert.equal(root.children[1].textContent,'🦉 guest');assert.equal(root.children[2].textContent,'🖥 host');assert.equal(root.children[0].attrs['aria-pressed'],'true');
 root.children[1].click();assert.equal(selected,targets[0].id);assert.equal(root.children[1].tabIndex,0);
 let prevented=false;root.children[1].events.keydown({key:'ArrowRight',preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(selected,targets[0].id);assert.equal(root.children[2].focused,true);root.children[2].click();assert.equal(closed.size,2);root.children[1].click();assert.equal(closed.has(targets[0].id),false);assert.equal(closed.has(targets[1].id),true);
 root.children[2].events.keydown({key:'Home',preventDefault(){}});root.children[0].click();assert.equal(selected,null);assert.equal(closed.size,0);
 tabs.render({targets:[{...targets[0],host_id:'<img src=x onerror=alert(1)>'}]});
 assert.match(root.children[1].textContent,/<img/);assert.equal(root.children[1].children.length,0);
 tabs.render({});assert.equal(root.hidden,true);
});
