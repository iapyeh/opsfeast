// Local host declarations only. No passwords are read or submitted by this UI.
export function accountPatch(name,sudo,{remove=false}={}) {
  return {users:{[name]:remove?null:{sudo}}};
}
export function accountRows(users,{l,e}) {
  return users.map(user=>`<tr><th scope="row">${e(user.name)}</th><td>${e(user.sudo?l.on:l.off)}</td><td><div class="host-account-actions"><button type="button" class="button" data-account-edit="${e(user.name)}">${e(l.accountEdit)}</button><button type="button" class="button" data-account-remove="${e(user.name)}">${e(l.accountRemove)}</button></div></td></tr>`).join('');
}
export function mountHostAccounts(root,{profile,host,l,e,request,getRevision,onSaved}) {
  let users=host.users.map(user=>({...user})),busy=false,editing=null,removing=false;
  root.innerHTML=`<section class="panel roadmap-section host-accounts-panel"><div class="panel-heading"><h2>${e(l.users)}</h2><button class="button primary" type="button" id="account-add">${e(l.accountAdd)}</button></div><p>${e(l.usersNote)}</p><p class="host-account-login">${e(l.connectionAccount)}：<strong>${e(host.login_user||l.unknown)}</strong> · ${e(l.connectionAccountHint)}</p><div class="host-account-list" id="account-list"></div><p id="account-status" class="host-account-status" role="status"></p></section><dialog class="host-confirm-dialog" id="account-dialog"><form id="account-form"><h2 id="account-title"></h2><p id="account-scope"></p><label>${e(l.accountName)}<input id="account-name" required maxlength="200" autocomplete="off"></label><p class="field-hint" id="account-name-hint">${e(l.accountNameHint)}</p><label class="draft-toggle" id="account-sudo-field"><input type="checkbox" id="account-sudo">${e(l.accountSudo)}</label><p class="field-hint" id="account-secret-hint">${e(l.accountSecretHint)}</p><p id="account-error" role="alert" tabindex="-1"></p><div class="setup-actions"><button class="button primary" id="account-save" type="submit"></button><button class="button" id="account-cancel" type="button">${e(l.cancel)}</button></div></form></dialog>`;
  const $=id=>root.querySelector('#'+id),dialog=$('account-dialog');
  function render(){
    $('account-list').innerHTML=users.length?`<div class="table-scroll"><table class="roadmap-table"><thead><tr><th scope="col">${e(l.accountName)}</th><th scope="col">${e(l.sudo)}</th><th scope="col">${e(l.accountActions)}</th></tr></thead><tbody>${accountRows(users,{l,e})}</tbody></table></div>`:`<p>${e(l.noAccounts)}</p>`;
    root.querySelectorAll('[data-account-edit]').forEach(button=>button.onclick=()=>open(button.dataset.accountEdit));
    root.querySelectorAll('[data-account-remove]').forEach(button=>button.onclick=()=>open(button.dataset.accountRemove,true));
  }
  function open(name=null,remove=false){
    editing=name;removing=remove;
    const user=users.find(item=>item.name===name);
    $('account-title').textContent=remove?l.accountRemove:name?l.accountEdit:l.accountAdd;
    $('account-scope').textContent=(remove?l.accountRemoveHint:l.accountScope).replace('{host}',host.host_id);
    $('account-name').value=name||'';$('account-name').readOnly=name!==null;
    $('account-sudo').checked=user?user.sudo:false;
    $('account-sudo-field').hidden=remove;
    $('account-name-hint').hidden=remove;$('account-secret-hint').hidden=remove;
    $('account-error').textContent='';
    $('account-save').textContent=remove?l.accountRemove:l.accountSave;
    $('account-save').className=remove?'button danger':'button primary';
    dialog.showModal();(remove?$('account-cancel'):name?$('account-save'):$('account-name')).focus();
  }
  $('account-add').onclick=()=>open();
  $('account-cancel').onclick=()=>{if(!busy)dialog.close();};
  dialog.oncancel=event=>{if(busy)event.preventDefault();};
  $('account-form').onsubmit=async event=>{
    event.preventDefault();if(busy)return;
    const name=$('account-name').value.trim();
    if(!name||(!editing&&users.some(user=>user.name===name))){$('account-error').textContent=l.accountDuplicate;$('account-error').focus();return;}
    busy=true;$('account-save').disabled=true;$('account-cancel').disabled=true;
    $('account-error').textContent=l.saving;
    try{
      const saved=await request('/api/v1/hosts',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,host_id:host.host_id,expected_revision:getRevision(),changes:accountPatch(name,$('account-sudo').checked,{remove:removing})})});
      if(saved.configuration_changed!==true||typeof saved.revision!=='string')throw new Error('account_save_unconfirmed');
      onSaved(saved.revision);
      if(removing)users=users.filter(user=>user.name!==name);
      else{const user=users.find(item=>item.name===name);if(user)user.sudo=$('account-sudo').checked;else users.push({name,sudo:$('account-sudo').checked});}
      render();dialog.close();$('account-status').textContent=l.accountSaved;$('account-add').focus();
    }catch(error){$('account-error').textContent=l.errors[error.code]||l.errors.default;$('account-error').focus();}
    finally{busy=false;$('account-save').disabled=false;$('account-cancel').disabled=false;}
  };
  render();
}
