import {mountAdminSettings} from "./admin-settings.mjs";
import {siteAssetUrl} from "./site-assets.mjs";
// Local presentation settings only. The capability is never persisted in the browser.
export function mountSiteSettings(container, {m, e, site, siteName, authState,appearanceOnly=false,onSaved}) {
  const l = m.site;
  let token = "", current = site, unlocked = false, busy = false;
  const pending = {logo:undefined, avatar:undefined};
  const objectUrls = new Map();
  container.innerHTML = `<div class="page-heading"><div><p class="eyebrow">${e(l.kicker)}</p><h1>${e(l.title)}</h1><p class="intro">${e(l.intro)}</p></div></div><div class="detail-note">${e(l.publicWarning)}</div><section class="settings-unlock panel"><h2>${e(l.unlockTitle)}</h2><p>${e(l.settingsNote)}</p><label for="edit-token">${e(l.token)}</label><div class="unlock-row"><input id="edit-token" type="password" autocomplete="off" placeholder="${e(l.tokenPlaceholder)}"><button id="unlock-site" class="button primary" type="button">${e(l.unlock)}</button><button id="lock-site" class="button" type="button" hidden>${e(l.lock)}</button></div><p class="field-hint">${e(l.tokenHint)}</p></section><p id="settings-status" role="status" class="settings-status"></p><section id="identity-panel" class="identity-panel" hidden><h2>${e(l.identity)}</h2><dl id="identity-values"></dl><p>${e(l.namespaceHint)}</p></section><section class="site-appearance" aria-label="${e(l.appearance)}"><div class="settings-grid"><section class="panel site-fields"><label for="site-name">${e(l.name)}</label><input id="site-name" maxlength="80" placeholder="${e(siteName)}" disabled><p class="field-hint">${e(l.inheritName)}</p><label for="site-slogan">${e(l.slogan)}</label><input id="site-slogan" maxlength="160" disabled><p class="field-hint">${e(l.sloganHint)}</p><p class="field-hint">${e(l.identityHint)}</p></section><section class="panel image-fields">${["logo", "avatar"].map(kind => `<div class="image-setting"><h2>${e(l[kind])}</h2><p class="field-hint">${e(l[kind+"Hint"])}</p><div class="image-preview" id="${kind}-preview"></div><label class="image-file-label" for="${kind}-file">${e(l.chooseImage)}</label><input id="${kind}-file" type="file" accept="image/png,image/jpeg" disabled><button id="${kind}-remove" class="image-remove" type="button" disabled>${e(l.removeImage)}</button><p id="${kind}-status" class="field-hint"></p></div>`).join("")}<p class="field-hint">${e(l.imageRules)}</p></section></div><div class="panel settings-save-row site-save-bar"><div><strong>${e(l.saveScope)}</strong><p class="field-hint">${e(l.saveHint)}</p></div><button id="save-site" type="button" class="button primary" disabled>${e(l.save)}</button></div></section><p class="field-hint">${e(l.remaining)}</p><div id="admin-settings"></div>`;
  const $ = id => container.querySelector(`#${id}`);
  if(appearanceOnly){
    container.querySelector('.page-heading').hidden=true;
    container.querySelector('.settings-unlock').hidden=true;
    $('admin-settings').hidden=true;
  }
  const setStatus = value => { $("settings-status").textContent = value; };
  const errorText = error => ({401:l.unauthorized,403:l.unauthorized,409:l.conflict,413:l.uploadLimit,415:l.invalid,422:l.invalid}[error.status] || l.network);
  async function request(path, options = {}) {
    const response = await fetch(path, {...options, headers:{...options.headers, Authorization:`Bearer ${token}`}});
    if (!response.ok) { const error = new Error("site_request_failed"); error.status = response.status; throw error; }
    return response.json();
  }
  function renderImage(kind, src) {
    $(kind+"-preview").innerHTML = src ? `<img src="${e(src)}" alt="${e(l[kind])}">` : `<span>${e(l.noImage)}</span>`;
  }
  function showCurrent() {
    $("site-name").value = current.site_name || "";
    $("site-slogan").value = current.slogan;
    for (const kind of ["logo", "avatar"]) renderImage(kind, siteAssetUrl(current,kind));
  }
  function enableEditing() {
    for (const id of ["site-name", "site-slogan", "logo-file", "avatar-file", "logo-remove", "avatar-remove", "save-site"])
      $(id).disabled = !unlocked || busy;
    $("lock-site").hidden = !unlocked;
    $("lock-site").disabled = busy;
    $("unlock-site").disabled = busy;
  }
  showCurrent(); setStatus(l.locked);
  for (const id of ["site-name", "site-slogan"]) $(id).addEventListener("input",()=>setStatus(l.unsaved));
  if(authState.authenticated&&!appearanceOnly) mountAdminSettings($("admin-settings"),{m,e,request});
  else $("admin-settings").innerHTML=`<section class="panel admin-panel"><div class="panel-heading"><h2>${e(m.admin.title)}</h2><span class="subtle-tag">${e(authState.unavailable?m.admin.unavailable:authState.configured?m.admin.configured:m.admin.unconfigured)}</span></div><p>${e(authState.unavailable?m.admin.unavailable:authState.configured?m.admin.changeLoginHint:m.admin.setupRequired)}</p>${authState.configured?`<a class="button" href="/login?next=%2Fsettings%2Fsite">${e(m.admin.login)} →</a>`:""}<p class="field-hint">${e(m.admin.recoveryHint)}</p></section>`;
  async function loadEditor(focusAccount=false) {
    const data=await request("/api/v1/site/settings");
    current=data.site;unlocked=true;showCurrent();
    $("identity-panel").hidden=appearanceOnly;
    $("identity-values").innerHTML=`<dt>UUID</dt><dd>${e(data.identity.id)}</dd><dt>${e(l.inherited)}</dt><dd>${e(data.identity.name===data.identity.id?l.unknownIdentity:data.identity.name)}</dd>`;
    setStatus(appearanceOnly?l.appearanceUnlocked:l.unlocked);
    if(!appearanceOnly)await mountAdminSettings($("admin-settings"),{m,e,request});
    if(focusAccount) $("admin-settings").querySelector('#admin-username')?.focus();
  }
  $("unlock-site").addEventListener("click", async () => {
    if(busy)return;
    busy=true;enableEditing();
    token=$("edit-token").value.trim();$("edit-token").value="";
    try {
      await request('/api/v1/site/unlock',{method:'POST'});
      token=""; // Subsequent requests use the HttpOnly editing cookie, never stored token text.
      await loadEditor(true);
    } catch(error){token="";unlocked=false;setStatus(errorText(error));}
    busy=false;enableEditing();
  });
  $("lock-site").addEventListener("click", async () => {
    if(busy)return;
    busy=true;enableEditing();
    try{
      await request('/api/v1/site/lock',{method:'POST'});
      token="";unlocked=false;$("identity-panel").hidden=true;
      $("admin-settings").innerHTML=`<section class="panel admin-panel"><h2>${e(m.admin.title)}</h2><p>${e(l.locked)}</p><p>${e(m.admin.locked)}</p></section>`;
      setStatus(l.locked);
    }catch(error){setStatus(errorText(error));}
    busy=false;enableEditing();
  });
  // Rebuild this page from the server-scoped edit session after navigation/reload.
  busy=true;enableEditing();
  loadEditor().catch(error=>{unlocked=false;if(error.status!==401)setStatus(errorText(error));})
    .finally(()=>{busy=false;enableEditing();});
  for (const kind of ["logo", "avatar"]) {
    $(kind+"-file").addEventListener("change", () => {
      const file = $(kind+"-file").files[0];
      if (!file) return;
      if (file.size > 2 * 1024 * 1024 || !["image/png", "image/jpeg"].includes(file.type)) {
        $(kind+"-file").value = ""; setStatus(file.size > 2 * 1024 * 1024 ? l.uploadLimit : l.invalid); return;
      }
      if (objectUrls.has(kind)) URL.revokeObjectURL(objectUrls.get(kind));
      const url = URL.createObjectURL(file); objectUrls.set(kind, url);
      pending[kind] = file; renderImage(kind,url); $(kind+"-status").textContent = l.imagePending; setStatus(l.unsaved);
    });
    $(kind+"-remove").addEventListener("click", () => {
      pending[kind] = null; $(kind+"-file").value = ""; renderImage(kind,siteAssetUrl({[kind]:null},kind));
      if (objectUrls.has(kind)) { URL.revokeObjectURL(objectUrls.get(kind)); objectUrls.delete(kind); }
      $(kind+"-status").textContent = l.imageRemoved; setStatus(l.unsaved);
    });
  }
  $("save-site").addEventListener("click", async () => {
    if (!unlocked || busy) return;
    busy = true; enableEditing(); setStatus(l.saving);
    let saved=false;
    try {
      const data = {...current, site_name:$("site-name").value.trim() || null, slogan:$("site-slogan").value.trim()};
      for (const kind of ["logo", "avatar"]) {
        if (pending[kind] === null) data[kind] = null;
        else if (pending[kind]) {
          const uploaded = await request("/api/v1/site/images", {method:"POST", headers:{"Content-Type":pending[kind].type}, body:pending[kind]});
          data[kind] = uploaded.asset_id;
        }
      }
      current = await request("/api/v1/site/settings", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({settings:data, expected_revision:current.revision})});
      for (const kind of ["logo", "avatar"]) { pending[kind] = undefined; $(kind+"-file").value = ""; $(kind+"-status").textContent = ""; }
      for (const url of objectUrls.values()) URL.revokeObjectURL(url);
      objectUrls.clear(); showCurrent(); setStatus(l.saved);
      const response = await fetch("/api/v1/site");
      if (response.ok) window.dispatchEvent(new CustomEvent("opsfeast:site-updated", {detail:await response.json()}));
      saved=true;
    } catch (error) { setStatus(errorText(error)); }
    finally { busy = false; enableEditing(); }
    if(saved&&onSaved)onSaved(current);
  });
  window.addEventListener("pagehide", () => {
    token = ""; unlocked = false; enableEditing(); setStatus(l.locked);
    $("identity-panel").hidden = true;
    for (const url of objectUrls.values()) URL.revokeObjectURL(url);
  });
}
