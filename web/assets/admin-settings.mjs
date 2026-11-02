// Credentials stay in form memory only; never in URLs, storage, or rendered errors.
export function adminInputError(username,password,confirmation) {
  if(!/^[A-Za-z0-9_.-]{3,64}$/.test(username))return 'usernameHint';
  if(password!==confirmation)return 'mismatch';
  if([...password].length<12||[...password].length>256)return 'passwordHint';
  return null;
}
export async function mountAdminSettings(container, {m,e,request,onSaved}) {
  const l=m.admin;
  let state;
  try {state=await request('/api/v1/admin');}
  catch (error) {container.innerHTML=`<section class="panel admin-panel"><h2>${e(l.title)}</h2><p>${e(error.status===401?l.locked:l.failed)}</p><a class="button" href="/login">${e(l.login)} →</a></section>`;return;}
  container.innerHTML=`<section class="panel admin-panel"><div class="panel-heading"><h2>${e(l.title)}</h2><span class="subtle-tag">${e(state.configured?l.configured:l.unconfigured)}</span></div><p>${e(state.configured?l.changeHint:l.bootstrapHint)}</p><label for="admin-username">${e(l.username)}</label><input id="admin-username" autocomplete="username" minlength="3" maxlength="64"><p class="field-hint">${e(l.usernameHint)}</p>${state.configured?`<label for="admin-current">${e(l.currentPassword)}</label><input id="admin-current" type="password" autocomplete="current-password">`:""}<label for="admin-password">${e(l.newPassword)}</label><input id="admin-password" type="password" autocomplete="new-password"><label for="admin-confirm">${e(l.confirm)}</label><input id="admin-confirm" type="password" autocomplete="new-password"><p class="field-hint">${e(l.passwordHint)}</p><button id="admin-save" class="button primary" type="button">${e(state.configured?l.change:l.setup)}</button><p id="admin-status" role="status" class="field-hint"></p></section>`;
  const $=id=>container.querySelector('#'+id);
  const result=(message,error=false)=>{
    $('admin-status').textContent=message;
    $('admin-status').className='admin-result '+(error?'admin-error':'admin-success');
    $('admin-status').setAttribute('tabindex','-1');
    $('admin-status').focus();
  };
  $('admin-username').value=state.username||'';
  $('admin-save').addEventListener('click',async()=>{
    const password=$('admin-password').value;
    const errorKey=adminInputError($('admin-username').value.trim(),password,$('admin-confirm').value);
    if(errorKey){result(l[errorKey],true);return;}
    const payload={username:$('admin-username').value.trim(),password,expected_revision:state.revision};
    if(state.configured)payload.current_password=$('admin-current').value;
    $('admin-save').disabled=true;
    let savedResult;
    try{
      const saved=await request(state.configured?'/api/v1/admin':'/api/v1/admin/bootstrap',{
        method:state.configured?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)
      });
      if(!saved?.configured||saved.revision!==state.revision+1)throw new Error('account_save_not_confirmed');
      $('admin-password').value='';$('admin-confirm').value='';
      if(state.configured)$('admin-current').value='';
      result(l.saved);
      container.querySelector('.subtle-tag').textContent=l.configured;
      if(!onSaved){
        const link=document.createElement('a');link.href='/login';link.className='button';link.textContent=l.login+' →';
        container.append(link);
      }
      savedResult=saved;
      // Changing a credential invalidates the session; reload/relogin for further edits.
    }catch(error){result(error.status===401?l.invalid: error.status===409?l.conflict:l.failed,true);$('admin-save').disabled=false;}
    if(savedResult&&onSaved)onSaved(savedResult);
  });
  window.addEventListener('pagehide',()=>{
    for(const input of container.querySelectorAll('input[type="password"]'))input.value='';
  });
}
