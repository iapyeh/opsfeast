import test from 'node:test';
import assert from 'node:assert/strict';
import {loginDestination} from '../web/assets/login-navigation.mjs';
import {mountProfiles} from '../web/assets/profiles-settings.mjs';
import {getMessages} from '../web/assets/i18n.mjs';

test('login returns to Profiles and rejects unsupported or external destinations',()=>{
  assert.equal(loginDestination('?next=%2Fsettings%2Fprofiles'),'/settings/profiles');
  assert.equal(loginDestination('?next=%2Fsettings%2Fsite'),'/settings/site');
  assert.equal(loginDestination('?next=%2Fsetup'),'/setup');
  const target='/hosts?profile=lab&host=web-01&view=settings';
  assert.equal(loginDestination('?next='+encodeURIComponent(target)),target);
  assert.equal(loginDestination('?next='+encodeURIComponent('/hosts?redirect=https://untrusted.example')),'/workspace');
  for(const next of ['', 'https://untrusted.example', '//untrusted.example', '/settings/profiles/../site']) {
    assert.equal(loginDestination('?next='+encodeURIComponent(next)),'/workspace');
  }
  const sid='11af0ac8-f21c-49ec-a5de-8f99d8116aac';
  for(const next of ['/console/'+sid,'/console/'+sid+'/blocks/'+sid,'/interactive?work='+sid])assert.equal(loginDestination('?next='+encodeURIComponent(next)),next);
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
