import {profileChildren} from './settings-hub.mjs';
export function renderProfileCards(current,{m,e,catalog}) {
  const l=m.profiles;
  return current.profiles.length?`<div class="profile-records">${current.profiles.map(row=>{
    const active=row.name===current.default_profile;
    return `<article class="profile-card${active?' is-default':''}" data-profile="${e(row.name)}" aria-label="${e(row.name)}"><header class="profile-card-header"><div><h2>${e(row.name)}</h2>${active?`<span class="profile-default-badge">${e(l.active)}</span>`:''}<span class="subtle-tag">${e(row.status==='available'?l.available:l.unavailable)}</span></div>${!active&&row.status==='available'?`<button class="button" data-use="${e(row.name)}" type="button">${e(l.use)}</button>`:''}</header><div class="profile-description"><p>${e(row.description||l.noDescription)}</p><button class="button" type="button" data-edit-description="${e(row.name)}">${e(l.editDescription)}</button></div><div class="profile-card-metadata"><p>${e(row.root)}</p><small>${e(l.namespace)}：${e(row.namespace||l.unknown)}</small></div>${!active?'<p class="field-hint">如需操作此環境的主機，請先設為預設 Profile。</p>':''}${catalog?profileChildren(row.name,{m,e,catalog,defaultProfile:current.default_profile}):''}<div class="setup-actions"><button class="button" type="button" data-profile-export="${e(row.name)}">匯出備份</button>${row.name!=='main'?`<button class="button" type="button" data-profile-detach="${e(row.name)}">卸離（保留資料）</button>${!active?`<button class="button" type="button" data-profile-delete="${e(row.name)}">刪除 Profile</button>`:''}`:''}</div></article>`;
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
  container.innerHTML=heading+`<p id="profiles-status" role="status" class="settings-status"></p><p class="field-hint">${e(l.statusHint)}</p><section id="profiles-list"></section><section class="profile-management-actions"><h2>${e(l.manageEnvironments)}</h2><p>${e(l.manageHint)}</p><div class="settings-grid profile-forms"><section class="panel"><h3>${e(l.create)}</h3><label for="profile-name">${e(l.name)}</label><input id="profile-name" maxlength="80"><label for="profile-namespace">${e(l.namespace)}</label><input id="profile-namespace" maxlength="80"><label for="profile-description-new">${e(l.description)}</label><textarea id="profile-description-new" rows="3" maxlength="1000"></textarea><p class="field-hint">${e(l.namespaceHint)}</p><button id="profile-create" type="button" class="button primary">${e(l.create)}</button></section><section class="panel"><h3>${e(l.attach)}</h3><p>${e(l.attachExplanation)}</p><label for="profile-attach-name">${e(l.name)}</label><input id="profile-attach-name" maxlength="80"><label for="profile-root">${e(l.root)}</label><input id="profile-root"><label for="profile-description-attach">${e(l.description)}</label><textarea id="profile-description-attach" rows="3" maxlength="1000"></textarea><p class="field-hint">${e(l.attachHint)}</p><button id="profile-attach" type="button" class="button primary">${e(l.attach)}</button></section></div></section><section class="panel"><h2>匯入 Profile 備份</h2><p>匯入到全新的管理目錄，不覆寫既有 Profile。備份中的外部檔案路徑不會自動搬移或重新綁定；匯入不會連線或執行 Recipes。</p><label for="profile-import-name">${e(l.name)}</label><input id="profile-import-name" maxlength="80"><label for="profile-import-file">Profile 備份 ZIP</label><input id="profile-import-file" type="file" accept=".zip,application/zip"><p>上限 256 MiB；備份可能包含主機憑證，請妥善保管。</p><button id="profile-import" class="button" type="button">匯入新 Profile</button></section><p class="detail-note">建立、掛接、卸離、切換、匯出與匯入都不會連線或執行 Recipes。Main 保留；刪除前請先切換預設 Profile。刪除會將目錄移至持久資料區的回收目錄，並移除登記，不會永久清除檔案。</p><dialog id="profile-action-dialog" class="host-confirm-dialog"><form id="profile-action-form"><h2 id="profile-action-title"></h2><p id="profile-action-message"></p><label for="profile-confirm-name">輸入 Profile 名稱以確認</label><input id="profile-confirm-name" autocomplete="off"><p id="profile-action-status" role="status"></p><div class="setup-actions"><button id="profile-action-confirm" class="button primary" type="submit">確認</button><button id="profile-action-cancel" class="button" type="button">取消</button></div></form></dialog><dialog id="profile-description-dialog" class="host-confirm-dialog"><form id="profile-description-form"><h2>${e(l.editDescription)}</h2><p id="profile-description-target"></p><label for="profile-description-value">${e(l.description)}</label><textarea id="profile-description-value" rows="5" maxlength="1000"></textarea><p>${e(l.descriptionHint)}</p><p id="profile-description-status" role="status"></p><div class="setup-actions"><button type="submit" class="button primary">${e(l.saveDescription)}</button><button id="profile-description-cancel" type="button" class="button">${e(l.cancelDescription)}</button></div></form></dialog>`;
  const $=id=>container.querySelector('#'+id);
  let editingProfile=null,pendingAction=null;
  const status=value=>{$('profiles-status').textContent=value;};
  function setBusy(busy){container.querySelectorAll('button').forEach(button=>{button.disabled=busy;});}
  function render(){
    $('profiles-list').innerHTML=renderProfileCards(current,{m,e,catalog});
    container.querySelectorAll('[data-use]').forEach(button=>button.addEventListener('click',()=>mutate('/api/v1/profiles/default','PUT',{name:button.dataset.use})));
    container.querySelectorAll('[data-edit-description]').forEach(button=>button.addEventListener('click',()=>{
      const row=current.profiles.find(item=>item.name===button.dataset.editDescription);if(!row)return;
      editingProfile=row.name;$('profile-description-target').textContent=row.name;$('profile-description-value').value=row.description||'';$('profile-description-status').textContent='';$('profile-description-dialog').showModal();
    }));
    for(const action of ['export','detach','delete'])container.querySelectorAll('[data-profile-'+action+']').forEach(button=>button.addEventListener('click',()=>{
      const name=button.dataset['profile'+action[0].toUpperCase()+action.slice(1)];pendingAction={action,name};
      $('profile-action-title').textContent=({export:'匯出私人備份',detach:'卸離 Profile',delete:'刪除 Profile'})[action]+' · '+name;
      $('profile-action-message').textContent=action==='export'?'備份包含此管理目錄的設定、可能的主機憑證、Recipes、筆記與附件、保存資料及 Vault；不包含目錄外的 SSH 金鑰或 recipe sources。請先停止其他寫入。':action==='detach'?'只移除登記，檔案保留原處。卸離目前預設時會切回 main；main 必須可用。':'移除登記並將整個管理目錄移入回收目錄。可從回收路徑重新掛接；不會永久清除資料。其他磁碟上的目錄請先卸離，不會自動跨磁碟搬移。';
      $('profile-confirm-name').value='';$('profile-action-status').textContent='';$('profile-action-dialog').showModal();
    }));
    window.dispatchEvent(new CustomEvent('opsfeast:profile-state' ,{detail:current}));
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
  $('profile-action-cancel').addEventListener('click',()=>$('profile-action-dialog').close());
  $('profile-action-form').addEventListener('submit',async event=>{
    event.preventDefault();if(!pendingAction)return;
    const {action,name}=pendingAction;
    if($('profile-confirm-name').value!==name){$('profile-action-status').textContent='名稱不符，尚未操作。';return;}
    if(action!=='export'){
      const ok=await mutate('/api/v1/profiles/'+action,'POST',{name,...(action==='delete'?{confirm_name:name}:{})});
      if(ok){$('profile-action-dialog').close();if(current.deleted)status('已刪除登記；資料回收路徑：'+current.deleted.recovery_root);}
      else $('profile-action-status').textContent=$('profiles-status').textContent;
      return;
    }
    setBusy(true);status('正在建立私人備份…');
    try{
      const response=await fetch('/api/v1/profiles/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,expected_revision:current.revision})});
      if(!response.ok)throw new Error('export_failed');
      const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name+'-profile.zip';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
      $('profile-action-dialog').close();status('備份已建立並開始下載。請妥善保管其中的私人資料。');
    }catch{status('無法匯出；請停止寫入並檢查目錄大小、符號連結與 Profile 設定。');$('profile-action-status').textContent=$('profiles-status').textContent;}
    finally{setBusy(false);}
  });
  $('profile-import').addEventListener('click',async()=>{
    const file=$('profile-import-file').files[0],name=$('profile-import-name').value.trim();
    if(!file||!name||file.size>256*1024*1024){status('請填寫新名稱並選擇 256 MiB 以內的 Profile ZIP。');return;}
    setBusy(true);status('正在驗證並匯入備份…');
    try{
      current=await request('/api/v1/profiles/import?'+new URLSearchParams({name,expected_revision:current.revision}),{method:'POST',headers:{'Content-Type':'application/zip'},body:file});
      render();status('匯入完成；未改變既有預設 Profile，也未執行任何 Recipe。');
    }catch(error){status(error.status===409?l.conflict:'匯入失敗，未覆寫既有 Profile。請檢查備份格式、名稱衝突與外部參照。');}
    finally{setBusy(false);}
  });
  $('profile-description-cancel').addEventListener('click',()=>$('profile-description-dialog').close());
  $('profile-description-form').addEventListener('submit',async event=>{event.preventDefault();if(editingProfile&&await mutate('/api/v1/profiles','PATCH',{name:editingProfile,description:$('profile-description-value').value}))$('profile-description-dialog').close();});
  $('profile-create').addEventListener('click',()=>mutate('/api/v1/profiles','POST',{name:$('profile-name').value.trim(),namespace:$('profile-namespace').value.trim()||null,description:$('profile-description-new').value}));
  $('profile-attach').addEventListener('click',()=>mutate('/api/v1/profiles/attach','POST',{name:$('profile-attach-name').value.trim(),root:$('profile-root').value.trim(),...($('profile-description-attach').value?{description:$('profile-description-attach').value}:{})}));
}
