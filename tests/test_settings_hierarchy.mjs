import test from 'node:test';
import assert from 'node:assert/strict';
import {renderSettingsTree,mountSettingsHub,profileChildren,renderParameterGuide} from '../web/assets/settings-hub.mjs';
import {updateResult,updatePrompt} from '../web/assets/updates.mjs';
import {getMessages} from '../web/assets/i18n.mjs';
const e=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const m=getMessages('zh-TW');
const catalog={categories:[...['site','profiles','bundle-recipes'].map(id=>({id,parent:null,route:'/settings/'+id,status:'available'})),...['hosts','recipes','parameters','retention'].map(id=>({id,parent:'profiles',route:'/settings/'+id,status:id==='hosts'?'available':'planned'}))]};
test('settings exposes three peer roots with Profile-owned children and exact scoped links',()=>{
  const html=renderSettingsTree(catalog,{default_profile:'qa&profile',profiles:[{name:'qa&profile'}]},{m,e,profile:'qa&profile'});
  assert.equal((html.match(/class="panel settings-root/g)||[]).length,3);
  assert.match(html,/profile-settings-children/);
  assert.match(html,/\/settings\/recipes\?profile=qa%26profile/);
  assert.match(html,/隸屬於 Profile：qa&amp;profile/);
  const nested=profileChildren('p',{m,e,catalog});
  assert.doesNotMatch(nested,/Bundle Recipes|\/settings\/site/);
  assert.match(nested,/使用者 Recipes/);
});
test('version check failures and local-ahead sources never offer an invented update',()=>{
  assert.match(updateResult({status:'failed'},e),/無法確認/);
  const data={status:'success',product:'opsfeast',source:'https://github.com/iapyeh/opsfeast',current:{version:'0.1',local_changes:true},latest:{version:'0.1'},checked_at:'2026-11-05T00:00:00Z',comparison:'local_newer',update_available:false};
  const html=updateResult(data,e);
  assert.match(html,/本機版本較新/);assert.match(html,/本機修改/);
  assert.doesNotMatch(html,/data-request-update/);
});
test('new-release confirmation gives an exact, scoped Agent handoff without claiming installation',()=>{
  const data={status:'success',product:'sshscript',source:'https://pypi.org/project/sshscript/',current:{version:'7.0.1'},latest:{version:'7.1.0'},checked_at:'2026-11-05T00:00:00Z',comparison:'update_available',update_available:true,compatible:false};
  const html=updateResult(data,e);
  assert.match(html,/data-request-update/);assert.match(html,/尚未列入/);
  const prompt=updatePrompt(data);
  assert.match(prompt,/7.0.1/);assert.match(prompt,/7.1.0/);
  assert.match(prompt,/docs\/skill-updates.md/);assert.match(prompt,/不得覆寫/);
  assert.match(prompt,/不授權 commit\/push/);
  assert.match(prompt,/docs\/update-preservation.md/);
  assert.match(prompt,/migrate-port/);
  assert.match(prompt,/installation-data/);
});

test('Bundle parameters guide identifies the selected Profile file and its current editing limits',()=>{
  const html=renderParameterGuide({profile:'vault-test4',root:'/private/<fixture>',m,e});
  assert.match(html,/vault-test4/);assert.match(html,/\/private\/&lt;fixture&gt;\/hosts.yaml/);
  assert.match(html,/目前 Web 尚未提供參數編輯器/);
  assert.match(html,/system\/network\/check\/port/);
  assert.match(html,/default:/);assert.match(html,/port: 443/);
  assert.doesNotMatch(html,/enabled: true|<fixture>/);
});

test('Settings home always displays saved default and ignores an alternate Profile URL',()=>{
  const profiles={default_profile:'main<&',profiles:[{name:'main<&'},{name:'other'}]};
  const root={innerHTML:'',querySelector(){throw new Error('no selector listener should be registered');}};
  mountSettingsHub(root,{m,e,catalog,profiles,search:'?profile=other'});
  assert.match(root.innerHTML,/目前預設 profile：main&lt;&amp;/);
  assert.match(root.innerHTML,/settings\/recipes\?profile=main%3C%26/);
  assert.match(root.innerHTML,/href="\/settings\/profiles"/);
  assert.doesNotMatch(root.innerHTML,/<select|<option|settings-profile|other/);
  mountSettingsHub(root,{m,e,catalog,profiles,search:'?profile=unknown'});
  assert.match(root.innerHTML,/main&lt;&amp;/);
});
test('Settings home without a default never silently selects the first registered Profile',()=>{
  const html=renderSettingsTree(catalog,{default_profile:null,profiles:[{name:'not-default'}]},{m,e});
  assert.match(html,new RegExp(m.profiles.empty));assert.doesNotMatch(html,/not-default|profile-settings-children|<select/);
  assert.match(renderSettingsTree(catalog,null,{m,e}),new RegExp(m.profiles.loginRequired));
});
