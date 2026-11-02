export async function mountProfiles(container,{m,e,authState}) {
  const l=m.profiles;
  const heading=`<div class="page-heading"><div><p class="eyebrow">${e(l.kicker)}</p><h1>${e(l.title)}</h1><p class="intro">${e(l.intro)}</p></div></div>`;
  if(!authState?.authenticated){
    container.innerHTML=heading+`<section class="panel"><p>${e(l.loginRequired)}</p><a class="button primary" href="${authState?.configured?'/login?next=%2Fsettings%2Fprofiles':'/settings/site'}">${e(authState?.configured?m.admin.signIn:m.admin.setup)} →</a></section>`;
    return;
  }
  let current;
  const request=async(path,options={})=>{
    const response=await fetch(path,options);
    if(!response.ok){const error=new Error('profile_request_failed');error.status=response.status;throw error;}
    return response.json();
  };
  container.innerHTML=`<div class="page-heading"><div><p class="eyebrow">${e(l.kicker)}</p><h1>${e(l.title)}</h1><p class="intro">${e(l.intro)}</p></div></div><p id="profiles-status" role="status" class="settings-status"></p><section class="panel" id="profiles-list"></section><div class="settings-grid profile-forms"><section class="panel"><h2>${e(l.create)}</h2><label for="profile-name">${e(l.name)}</label><input id="profile-name" maxlength="80"><label for="profile-namespace">${e(l.namespace)}</label><input id="profile-namespace" maxlength="80"><p class="field-hint">${e(l.namespaceHint)}</p><button id="profile-create" type="button" class="button primary">${e(l.create)}</button></section><section class="panel"><h2>${e(l.attach)}</h2><label for="profile-attach-name">${e(l.name)}</label><input id="profile-attach-name" maxlength="80"><label for="profile-root">${e(l.root)}</label><input id="profile-root"><p class="field-hint">${e(l.attachHint)}</p><button id="profile-attach" type="button" class="button primary">${e(l.attach)}</button></section></div><p class="detail-note">${e(l.boundary)}</p>`;
  const $=id=>container.querySelector('#'+id);
  const status=value=>{$('profiles-status').textContent=value;};
  function setBusy(busy){container.querySelectorAll('button').forEach(button=>{button.disabled=busy;});}
  function render(){
    const rows=current.profiles;
    $('profiles-list').innerHTML=`<div class="panel-heading"><h2>${e(l.current)}</h2><strong>${e(current.default_profile||l.none)}</strong></div><p class="field-hint">${e(l.statusHint)}</p>${rows.length?`<div class="profile-records">${rows.map(row=>`<article><div><strong>${e(row.name)}</strong> ${row.active?`<span class="subtle-tag">${e(l.active)}</span>`:""}<span class="subtle-tag">${e(row.status==='available'?l.available:l.unavailable)}</span></div><p>${e(row.root)}</p><small>${e(l.namespace)}：${e(row.namespace||l.unknown)}</small>${!row.active&&row.status==='available'?`<button class="button" data-use="${e(row.name)}" type="button">${e(l.use)}</button>`:''}</article>`).join('')}</div>`:`<p class="field-hint">${e(l.empty)}</p>`}`;
    container.querySelectorAll('[data-use]').forEach(button=>button.addEventListener('click',()=>mutate('/api/v1/profiles/default','PUT',{name:button.dataset.use})));
    window.dispatchEvent(new CustomEvent('opsfeast:profile-state',{detail:current}));
  }
  async function mutate(path,method,body){
    if(!current)return;
    setBusy(true);status(l.saving);
    try{current=await request(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,expected_revision:current.revision})});render();status(l.saved);}
    catch(error){status(error.status===409?l.conflict:error.status===401?l.loginRequired:l.failed);}
    finally{setBusy(false);}
  }
  try{current=await request('/api/v1/profiles');render();}
  catch(error){status(error.status===401?l.loginRequired:l.failed);setBusy(true);return;}
  $('profile-create').addEventListener('click',()=>mutate('/api/v1/profiles','POST',{name:$('profile-name').value.trim(),namespace:$('profile-namespace').value.trim()||null}));
  $('profile-attach').addEventListener('click',()=>mutate('/api/v1/profiles/attach','POST',{name:$('profile-attach-name').value.trim(),root:$('profile-root').value.trim()}));
}
