import test from 'node:test';
import assert from 'node:assert/strict';
import {accountPatch,accountRows,mountHostAccounts} from '../web/assets/host-accounts.mjs';
import {uiIcon} from '../web/assets/ui-icons.mjs';
import l from '../web/assets/locales/host-management-zh-TW.mjs';
const e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
class Element {
  innerHTML='';textContent='';value='';nodes={};disabled=false;checked=false;open=false;dataset={};
  querySelector(selector){return this.nodes[selector]??=new Element();}
  querySelectorAll(selector){
    const attr=selector.slice(1,-1),camel=attr.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
    return [...this.querySelector('#account-list').innerHTML.matchAll(new RegExp(attr+'="([^"]*)"','g'))].map(match=>{
      const button=new Element();button.dataset[camel]=match[1];this.nodes[selector+':'+match[1]]=button;return button;
    });
  }
  focus(){this.focused=true;}
  showModal(){this.open=true;}
  close(){this.open=false;}
}
function fixture(request){
  const root=new Element(),revisions=[];
  mountHostAccounts(root,{profile:'prod&qa',host:{host_id:'web-01',login_user:'login',users:[{name:'operator',sudo:true}]},l,e,request,getRevision:()=>revisions.at(-1)||'rev1',onSaved:value=>revisions.push(value)});
  return {root,revisions,$:id=>root.querySelector('#'+id)};
}
test('account changes are narrow and escaped rows keep names as inert data',()=>{
  assert.deepEqual(accountPatch('__proto__',false),{users:{['__proto__']:{sudo:false}}});
  assert.deepEqual(accountPatch('operator',true,{remove:true}),{users:{operator:null}});
  const html=accountRows([{name:'<img src=x>',sudo:false}],{l,e});
  assert.doesNotMatch(html,/<img/);assert.match(html,/&lt;img src=x&gt;/);assert.match(html,/scope="row"/);
  assert.match(html,/停用/);
});
test('add defaults sudo off, updates revision and exposes no secret fields',async()=>{
  const requests=[];
  const {root,revisions,$}=fixture(async(path,options)=>{requests.push([path,JSON.parse(options.body)]);return {configuration_changed:true,revision:'rev2'};});
  $('account-add').onclick();assert.equal($('account-dialog').open,true);assert.equal($('account-sudo').checked,false);
  $('account-name').value='auditor';await $('account-form').onsubmit({preventDefault(){}});
  assert.deepEqual(requests,[['/api/v1/hosts',{profile:'prod&qa',host_id:'web-01',expected_revision:'rev1',changes:{users:{auditor:{sudo:false}}}}]]);
  assert.deepEqual(revisions,['rev2']);assert.equal($('account-dialog').open,false);
  assert.match($('account-list').innerHTML,/auditor/);assert.equal($('account-add').focused,true);
  assert.doesNotMatch(root.innerHTML,/type="password"/);
});
test('editing keeps account name fixed and removal requires the dialog submit',async()=>{
  const bodies=[];
  const {root,$}=fixture(async(_,options)=>{bodies.push(JSON.parse(options.body));return {configuration_changed:true,revision:'rev'+(bodies.length+1)};});
  root.nodes['[data-account-edit]:operator'].onclick();assert.equal($('account-name').readOnly,true);
  $('account-sudo').checked=false;await $('account-form').onsubmit({preventDefault(){}});
  assert.deepEqual(bodies[0].changes,{users:{operator:{sudo:false}}});
  root.nodes['[data-account-remove]:operator'].onclick();assert.equal(bodies.length,1);assert.equal($('account-sudo-field').hidden,true);assert.equal($('account-secret-hint').hidden,true);assert.equal($('account-cancel').focused,true);
  await $('account-form').onsubmit({preventDefault(){}});
  assert.equal(bodies[1].expected_revision,'rev2');assert.deepEqual(bodies[1].changes,{users:{operator:null}});
  assert.match($('account-list').innerHTML,/尚未宣告/);
});
test('conflicts keep the draft and displayed accounts; duplicate additions never send',async()=>{
  let calls=0;
  const {root,revisions,$}=fixture(async()=>{calls++;const error=new Error();error.code='revision_conflict';throw error;});
  $('account-add').onclick();$('account-name').value='operator';await $('account-form').onsubmit({preventDefault(){}});assert.equal(calls,0);
  $('account-name').value='auditor';await $('account-form').onsubmit({preventDefault(){}});
  assert.equal(calls,1);assert.equal($('account-dialog').open,true);assert.equal($('account-name').value,'auditor');
  assert.match($('account-error').textContent,/其他人更新/);assert.equal($('account-error').focused,true);
  assert.doesNotMatch($('account-list').innerHTML,/auditor/);assert.deepEqual(revisions,[]);
  assert.equal($('account-save').disabled,false);
});
test('navigation SVGs are decorative and unknown names cannot inject markup',()=>{
  for(const name of ['home','hosts','recipes','work','logs','apps','settings','learn','docs','skills']){
    const svg=uiIcon(name);assert.match(svg,/aria-hidden="true"/);assert.match(svg,/focusable="false"/);assert.doesNotMatch(svg,/<script|onload|<image|<use/);
  }
  assert.throws(()=>uiIcon('<script>'),/unknown_ui_icon/);
});
