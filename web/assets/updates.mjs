import c from './locales/updates-zh-TW.mjs';
import {formatDateTime} from './i18n.mjs';
export const updatePrompt=(data,origin)=>c.prompt({...data,origin});
export function updateResult(data,e) {
  if(data.status!=='success')return `<p role="alert">${e(c.failed)}</p>`;
  return `<p role="status">${e(c.comparisons[data.comparison]||c.comparisons.comparison_unknown)}</p><dl class="log-metadata"><dt>${e(c.latest)}</dt><dd>${e(data.latest.version)}</dd>${data.latest.commit?`<dt>${e(c.commit)}</dt><dd>${e(data.latest.commit)}</dd>`:''}<dt>${e(c.checked)}</dt><dd>${e(formatDateTime(data.checked_at))}</dd><dt>${e(c.source)}</dt><dd><a href="${e(data.source)}" target="_blank" rel="noopener noreferrer">${e(data.source)}</a></dd></dl>${data.current.local_changes?`<p>${e(c.localChanges)}</p>`:''}${data.compatible===false?`<p>${e(c.unsupported)}</p>`:''}${data.update_available===true||['diverged','comparison_unknown'].includes(data.comparison)?`<button type="button" class="button" data-request-update="${e(data.product)}">${e(data.update_available===true?c.ask:c.review)}</button>`:''}`;
}
export async function mountVersions(root,{e,fetchImpl=fetch}) {
  root.innerHTML=`<h2>${e(c.title)}</h2><p>${e(c.hint)}</p><div id="version-products" class="version-grid"></div><dialog id="update-confirm" class="host-confirm-dialog"><h2>${e(c.confirmTitle)}</h2><p>${e(c.confirmText)}</p><div id="update-review"></div><div class="setup-actions"><button type="button" id="update-accept" class="button primary">${e(c.confirm)}</button><button type="button" id="update-cancel" class="button">${e(c.cancel)}</button></div></dialog><section id="update-instruction" hidden><h3>${e(c.instruction)}</h3><textarea id="update-prompt" rows="12" readonly></textarea><button type="button" id="update-copy" class="button">${e(c.copy)}</button><p id="update-copy-status" role="status"></p></section>`;
  const $=selector=>root.querySelector(selector);
  let chosen=null;
  const open=data=>{if($('#update-confirm').open)return;chosen=data;$('#update-review').textContent=`${data.product==='opsfeast'?'OpsFeast':'SSHScript'}: ${data.current.version||c.unknown} → ${data.latest.version}${data.latest.commit?' · '+data.latest.commit:''}`+[data.current.local_changes?c.localChanges:'',data.compatible===false?c.unsupported:''].filter(Boolean).map(text=>'\n'+text).join('');$('#update-confirm').showModal();};
  $('#update-cancel').addEventListener('click',()=>{$('#update-confirm').close();chosen=null;});
  $('#update-accept').addEventListener('click',()=>{if(!chosen)return;$('#update-prompt').value=updatePrompt(chosen,location.origin);$('#update-instruction').hidden=false;$('#update-copy-status').textContent='';$('#update-confirm').close();});
  $('#update-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#update-prompt').value);$('#update-copy-status').textContent=c.copied;}catch{$('#update-copy-status').textContent=c.copyFailed;}});
  try {
    const response=await fetchImpl('/api/v1/updates');
    if(!response.ok)throw new Error();
    const installed=await response.json();
    $('#version-products').innerHTML=['opsfeast','sshscript'].map(product=>`<section><h3>${product==='opsfeast'?'OpsFeast':'SSHScript'}</h3><p>${e(c.current)}: <strong data-installed-version="${product}">${e(installed[product].version||c.missing)}</strong></p>${installed[product].commit?`<p class="field-hint">${e(c.commit)}: ${e(installed[product].commit)}</p>`:''}<button type="button" class="button" data-check-version="${product}">${e(c.check)}</button><div data-version-result="${product}"></div></section>`).join('');
    root.querySelectorAll('[data-check-version]').forEach(button=>button.addEventListener('click',async()=>{
      const product=button.dataset.checkVersion,target=$(`[data-version-result="${product}"]`);
      button.disabled=true;target.textContent=c.checking;
      try {
        const response=await fetchImpl('/api/v1/updates/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product})});
        if(!response.ok)throw new Error();
        const data=await response.json();if(data.current)$(`[data-installed-version="${product}"]`).textContent=data.current.version||c.missing;target.innerHTML=updateResult(data,e);
        target.querySelector('[data-request-update]')?.addEventListener('click',()=>open(data));
        if(data.status==='success'&&data.update_available===true)open(data);
      }catch{target.textContent=c.failed;}finally{button.disabled=false;}
    }));
  }catch{$('#version-products').textContent=c.failed;}
}
