import test from 'node:test';
import assert from 'node:assert/strict';
import {loginDestination} from '../web/assets/login-navigation.mjs';
import {mountProfiles,renderProfileCards} from '../web/assets/profiles-settings.mjs';
import {getMessages} from '../web/assets/i18n.mjs';

test('login returns to Profiles and rejects unsupported or external destinations',()=>{
  assert.equal(loginDestination('?next=%2Fsettings%2Fprofiles'),'/settings/profiles');
  assert.equal(loginDestination('?next=%2Fsettings%2Fsite'),'/settings/site');
  assert.equal(loginDestination('?next=%2Fsetup'),'/setup');
  assert.equal(loginDestination('?next='+encodeURIComponent('/logs?profile=main&result=fixture')),'/logs?profile=main&result=fixture');
  assert.equal(loginDestination('?next='+encodeURIComponent('/logs?next=//bad')),'/workspace');
  const target='/hosts?profile=lab&host=web-01&view=settings';
  assert.equal(loginDestination('?next='+encodeURIComponent(target)),target);
  assert.equal(loginDestination('?next='+encodeURIComponent('/hosts?redirect=https://untrusted.example')),'/workspace');
  for(const next of ['', 'https://untrusted.example', '//untrusted.example', '/settings/profiles/../site']) {
    assert.equal(loginDestination('?next='+encodeURIComponent(next)),'/workspace');
  }
  const sid='11af0ac8-f21c-49ec-a5de-8f99d8116aac';
  for(const next of ['/console/'+sid,'/console/'+sid+'/blocks/'+sid,'/interactive?work='+sid])assert.equal(loginDestination('?next='+encodeURIComponent(next)),next);
  for(const suffix of ['', '/history', '/blocks/'+sid, '/history/blocks/'+sid]){
    const scoped='/console/'+sid+suffix+'?profile=vault-test&host_id=guest';
    assert.equal(loginDestination('?next='+encodeURIComponent(scoped)),scoped);
  }
  for(const tail of ['?profile=a&profile=b','?next=//bad','#https://bad','/bogus','/../hosts'])assert.equal(loginDestination('?next='+encodeURIComponent('/console/'+sid+tail)),'/workspace');
  for(const next of ['/console/'+sid+'?redirect=//bad','/console/../hosts','/interactive?work='+sid+'&next=//bad'])assert.equal(loginDestination('?next='+encodeURIComponent(next)),'/workspace');
});
test('unauthenticated Profiles retains its page and offers login or account setup without requesting data',async()=>{
  const m=getMessages('zh-TW');
  for(const configured of [true,false]) {
    const container={innerHTML:''};
    await mountProfiles(container,{m,e:String,authState:{configured,authenticated:false}});
    assert.match(container.innerHTML,/<h1>Profiles<\/h1>/);
    assert.ok(container.innerHTML.includes(configured?'/login?next=%2Fsettings%2Fprofiles':'/settings/site'));
    assert.ok(!container.innerHTML.includes('profile-create'));
  }
});

test('default badge and switch buttons stay inside their owning cards and use the canonical default',()=>{
  const m=getMessages('zh-TW'), e=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const state={default_profile:'vault-test4',profiles:[{name:'main',active:true,status:'available',root:'/main'},{name:'vault-test4',active:false,status:'available',root:'/vault'},{name:'broken',status:'unavailable',root:'/broken'}]};
  const html=renderProfileCards(state,{m,e,catalog:null});
  const cards=[...html.matchAll(/<article[^>]*data-profile="([^"]+)"[^>]*>(.*?)<\/article>/gs)];
  assert.equal(cards.length,3);
  assert.match(cards.find(card=>card[1]==='vault-test4')[2],/目前預設/);
  assert.doesNotMatch(cards.find(card=>card[1]==='vault-test4')[2],/data-use/);
  assert.match(cards.find(card=>card[1]==='main')[2],/data-use="main"/);
  assert.doesNotMatch(cards.find(card=>card[1]==='broken')[2],/data-use/);
  const switched=renderProfileCards({...state,default_profile:'main'},{m,e,catalog:null});
  assert.doesNotMatch(switched, /data-use="main"/);
  assert.match(switched,/data-use="vault-test4"/);
  assert.doesNotMatch(html,/<h2>目前預設 profile<\/h2>/);
});

test('profile descriptions are escaped, preserve line breaks and offer an editor even when unavailable',()=>{
  const m=getMessages('zh-TW'),e=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const html=renderProfileCards({default_profile:'main',profiles:[{name:'main',description:'Production\n<script>unsafe</script>',status:'missing',root:'/missing'},{name:'empty',description:'',root:'/empty'}]},{m,e,catalog:null});
  assert.match(html,/Production\n&lt;script&gt;unsafe&lt;\/script&gt;/);
  assert.doesNotMatch(html,/<script>/);
  assert.match(html,/data-edit-description="main"/);
  assert.ok(html.includes(m.profiles.noDescription));
});
