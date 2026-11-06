import {profileChildren} from './settings-hub.mjs';
export function renderProfileCards(current,{m,e,catalog}) {
  const l=m.profiles;
  return current.profiles.length?`<div class="profile-records">${current.profiles.map(row=>{
    const active=row.name===current.default_profile;
    return `<article class="profile-card${active?' is-default':''}" data-profile="${e(row.name)}" aria-label="${e(row.name)}"><header class="profile-card-header"><div><h2>${e(row.name)}</h2>${active?`<span class="profile-default-badge">${e(l.active)}</span>`:''}<span class="subtle-tag">${e(row.status==='available'?l.available:l.unavailable)}</span></div>${!active&&row.status==='available'?`<button class="button" data-use="${e(row.name)}" type="button">${e(l.use)}</button>`:''}</header><div class="profile-description"><p>${e(row.description||l.noDescription)}</p><button class="button" type="button" data-edit-description="${e(row.name)}">${e(l.editDescription)}</button></div><div class="profile-card-metadata"><p>${e(row.root)}</p><small>${e(l.namespace)}：${e(row.namespace||l.unknown)}</small></div>${catalog?profileChildren(row.name,{m,e,catalog}):''}</article>`;
  }).join('')}</div>`:`<p class="field-hint">${e(l.empty)}</p>`;
}
export async function mountProfiles(container,{m,e,authState}) {
  const l=m.profiles;
  const heading=`<div class="page-heading"><div><p class="eyebrow">${e(l.kicker)}</p><h1>${e(l.title)}</h1><p class="intro">${e(l.intro)}</p></div></div>`;
  if(!authState?.authenticated){
    container.innerHTML=heading+`<section class="panel"><p>${e(l.loginRequired)}</p><a class="button primary" href="${authState?.configured?'/login?next=%2Fsettings%2Fprofiles':'/settings/site'}">${e(authState?.configured?m.admin.signIn:m.admin.setup)} →</a></section>`;
    return;
  }
  let current;
  const catalog=await fetch('/api/v1/settings/catalog').then(response=>response.ok?response.json():null).catch(()=>null);
  const request=async(path,options={})=>{
    const response=await fetch(path,options);
    if(!response.ok){const error=new Error('profile_request_failed');error.status=response.status;throw error;}
    return response.json();
  };
  container.innerHTML=heading+`<p id="profiles-status" role="status" class="settings-status"></p><p class="field-hint">${e(l.statusHint)}</p><section id="profiles-list"></section><section class="profile-management-actions"><h2>${e(l.manageEnvironments)}</h2><p>${e(l.manageHint)}</p><div class="settings-grid profile-forms"><section class="panel"><h3>${e(l.create)}</h3><label for="profile-name">${e(l.name)}</label><input id="profile-name" maxlength="80"><label for="profile-namespace">${e(l.namespace)}</label><input id="profile-namespace" maxlength="80"><label for="profile-description-new">${e(l.description)}</label><textarea id="profile-description-new" rows="3" maxlength="1000"></textarea><p class="field-hint">${e(l.namespaceHint)}</p><button id="profile-create" type="button" class="button primary">${e(l.create)}</button></section><section class="panel"><h3>${e(l.attach)}</h3><p>${e(l.attachExplanation)}</p><label for="profile-attach-name">${e(l.name)}</label><input id="profile-attach-name" maxlength="80"><label for="profile-root">${e(l.root)}</label><input id="profile-root"><label for="profile-description-attach">${e(l.description)}</label><textarea id="profile-description-attach" rows="3" maxlength="1000"></textarea><p class="field-hint">${e(l.attachHint)}</p><button id="profile-attach" type="button" class="button primary">${e(l.attach)}</button></section></div></section><p class="detail-note">${e(l.boundary)}</p><dialog id="profile-description-dialog" class="host-confirm-dialog"><form id="profile-description-form"><h2>${e(l.editDescription)}</h2><p id="profile-description-target"></p><label for="profile-description-value">${e(l.description)}</label><textarea id="profile-description-value" rows="5" maxlength="1000"></textarea><p>${e(l.descriptionHint)}</p><p id="profile-description-status" role="status"></p><div class="setup-actions"><button type="submit" class="button primary">${e(l.saveDescription)}</button><button id="profile-description-cancel" type="button" class="button">${e(l.cancelDescription)}</button></div></form></dialog>`;
  const $=id=>container.querySelector('#'+id);
  let editingProfile=null;
  const status=value=>{$('profiles-status').textContent=value;};
  function setBusy(busy){container.querySelectorAll('button').forEach(button=>{button.disabled=busy;});}
  function render(){
    $('profiles-list').innerHTML=renderProfileCards(current,{m,e,catalog});
    container.querySelectorAll('[data-use]').forEach(button=>button.addEventListener('click',()=>mutate('/api/v1/profiles/default','PUT',{name:button.dataset.use})));
    container.querySelectorAll('[data-edit-description]').forEach(button=>button.addEventListener('click',()=>{
      const row=current.profiles.find(item=>item.name===button.dataset.editDescription);if(!row)return;
      editingProfile=row.name;$('profile-description-target').textContent=row.name;$('profile-description-value').value=row.description||'';$('profile-description-status').textContent='';$('profile-description-dialog').showModal();
    }));
    window.dispatchEvent(new CustomEvent('opsfeast:profile-state',{detail:current}));
  }
  async function mutate(path,method,body){
    if(!current)return;
    if(path==='/api/v1/profiles/default'&&body.name===current.default_profile)return;
    setBusy(true);status(l.saving);
    try{current=await request(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,expected_revision:current.revision})});render();status(l.saved);return true;}
    catch(error){const message=error.status===409?l.conflict:error.status===401?l.loginRequired:l.failed;status(message);$('profile-description-status').textContent=message;return false;}
    finally{setBusy(false);}
  }
  try{current=await request('/api/v1/profiles');render();}
  catch(error){status(error.status===401?l.loginRequired:l.failed);setBusy(true);return;}
  $('profile-description-cancel').addEventListener('click',()=>$('profile-description-dialog').close());
  $('profile-description-form').addEventListener('submit',async event=>{event.preventDefault();if(editingProfile&&await mutate('/api/v1/profiles','PATCH',{name:editingProfile,description:$('profile-description-value').value}))$('profile-description-dialog').close();});
  $('profile-create').addEventListener('click',()=>mutate('/api/v1/profiles','POST',{name:$('profile-name').value.trim(),namespace:$('profile-namespace').value.trim()||null,description:$('profile-description-new').value}));
  $('profile-attach').addEventListener('click',()=>mutate('/api/v1/profiles/attach','POST',{name:$('profile-attach-name').value.trim(),root:$('profile-root').value.trim(),...($('profile-description-attach').value?{description:$('profile-description-attach').value}:{})}));
}
