"use strict";
import {getMessages, readLocale, saveLocale, supportedLocales, translate} from "./i18n.mjs";
import {mountSiteSettings} from "./site-settings.mjs";
import {mountProfiles} from "./profiles-settings.mjs";
import {mountRoadmap, roadmapPaths, roadmapCopy, versionPreview} from "./roadmap.mjs";
import {siteAssetUrl} from "./site-assets.mjs";
import {loginDestination} from "./login-navigation.mjs";
import {mountFirstUse} from "./first-use.mjs";
import {mountHostManager} from "./host-manager.mjs";

let storage;
try { storage = window.localStorage; } catch { /* Private/restricted browser storage. */ }
const locale = readLocale(storage, navigator.languages || [navigator.language]);
const m = getMessages(locale), s = m.shell, a = m.auth, h = m.home;
const t = (key, values) => translate(locale, key, values);
// Escape every translated string before inserting it into the authored templates.
const e = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
let authState={configured:false,authenticated:false,unavailable:true};
try {
  const response=await fetch('/api/v1/auth/status');
  if(response.ok)authState=await response.json();
} catch { /* No fabricated login state when the server is unavailable. */ }
let profileState=null;
if(authState.authenticated){
  try{const response=await fetch('/api/v1/profiles');if(response.ok)profileState=await response.json();}catch{}
}
let site;
let siteLoadFailed = false;
try {
  const response = await fetch("/api/v1/site");
  if (!response.ok) throw new Error("site_unavailable");
  site = await response.json();
} catch {
  siteLoadFailed = true;
  site = {site_name:null, slogan:"", logo:null, avatar:null};
}
let siteName = site.site_name || m.site.defaultName;
let siteSlogan = site.slogan || m.site.defaultSlogan;
const logo = () => `<img class="site-logo" src="${siteAssetUrl(site, "logo")}" width="36" height="36" alt="${e(m.site.logoAlt)}">`;
const path = location.pathname;
const key = path === "/workspace" ? "home" : path === "/settings/site" ? "site" : path.slice(1);
const settingsPage = path === "/settings" || path.startsWith("/settings/");
const settingsCategory = path.startsWith("/settings/") ? path.split("/")[2] : null;
let settingsCatalog = null;
if (settingsPage) {
  try {
    const response = await fetch("/api/v1/settings/catalog");
    if (!response.ok) throw new Error("catalog_unavailable");
    settingsCatalog = await response.json();
  } catch { /* Show unavailability explicitly instead of inventing capabilities. */ }
}
const firstUsePage=path==="/setup" || (["/","/login"].includes(path)&&!authState.unavailable&&!authState.configured);
const publicPage = firstUsePage || path === "/" || path === "/login";
const roadmapKey = path === "/workspace" ? "home" : path === "/recipes/data" || path === "/retention" ? "recipes" : path.slice(1);
const title = roadmapPaths.includes(path) ? roadmapCopy[roadmapKey].title : path === "/" ? s.entry : path === "/login" ? a.loginTitle : settingsPage ? (m.settings.categories[settingsCategory]?.title || m.settings.title) : m.pages[key]?.title || s.home;
document.documentElement.lang = locale;
document.title = `${siteName} · ${title}`;
document.querySelector('link[rel="icon"]').href = siteAssetUrl(site, "logo");

function brand(home = "/") {
  return `<a class="brand owner-brand" href="${home}">${logo()}<span class="site-brand-text">${e(siteName)}<span class="brand-sub">${e(siteSlogan)}</span></span></a>`;
}
function languageControl() {
  return `<label class="language-control" title="${e(s.languageHint)}"><span>${e(s.language)}</span><select id="language" aria-label="${e(s.language)}">${supportedLocales.map(code => `<option value="${e(code)}">${e(getMessages(code).languageName)}</option>`).join("")}</select></label>`;
}
function footer() {
  const modified = document.querySelector('meta[name="opsfeast-last-modified"]').content;
  return `<footer><span><img class="product-attribution" src="/assets/mark.svg" width="14" height="14" alt=""><span class="product-credit">${e(m.site.poweredBy)}</span> <span class="footer-dot">·</span> ${e(siteSlogan)}</span><span>${e(s.localPreview)} <span class="footer-dot">/</span> <time>${e(t("shell.modified", {time:modified}))}</time></span></footer>`;
}
function notice() {
  return `<div class="notice"><span class="notice-mark">i</span><span>${e(siteLoadFailed ? m.site.loadError : s.notice)}</span><span class="notice-label">${e(s.previewNumber)}</span></div>`;
}
function publicView() {
  const login = path === "/login";
  return `<div class="public-shell"><a class="skip" href="#main">${e(s.skip)}</a><header class="public-header">${brand()}<nav class="public-nav"><a href="/learn">${e(s.learn)}</a><a href="/docs">${e(s.docs)}</a><a href="/settings">${e(m.settings.title)}</a>${languageControl()}<span class="preview-pill">${e(s.guest)}</span></nav></header><main id="main" tabindex="-1">${notice()}<div class="public-content ${login ? "login-layout" : "welcome-layout"}"><section class="public-intro"><p class="eyebrow">${e(login ? a.loginKicker : m.site.kicker)}</p><h1>${e(siteName)}</h1><p class="public-description">${e(siteSlogan)}</p>${login ? `<img class="login-avatar" src="${siteAssetUrl(site, "avatar")}" alt="${e(m.site.avatarAlt)}">` : ""}${login ? `<a class="public-back" href="/">← ${e(a.back)}</a>` : `<div class="public-actions"><a class="button primary" href="/login">${e(a.loginAction)} <span>↗</span></a><a class="button" href="/learn">${e(a.learnAction)} <span>→</span></a></div>`}<div class="public-features">${a.features.map(([name, text], i) => `<div><span>0${i+1}</span><strong>${e(name)}</strong><p>${e(text)}</p></div>`).join("")}</div></section>${login ? loginCard() : welcomeCard()}</div><p class="public-boundary">${e(login ? a.accountNote : a.publicNote)}</p>${footer()}</main></div>`;
}
function welcomeCard() {
  return `<section class="welcome-card guardian-card"><div class="panel-heading"><span class="entry-kicker">${e(m.site.guardian)}</span><span class="welcome-symbol">◇</span></div><img class="site-avatar${site.avatar ? "" : " default-avatar"}" src="${siteAssetUrl(site, "avatar")}" alt="${e(m.site.avatarAlt)}">${site.avatar ? "" : `<p class="default-avatar-note">${e(m.site.avatarEmpty)}</p>`}<a class="guardian-action" href="/settings/site">${e(m.site.avatarAction)} ↗</a></section>`;
}
function loginCard() {
  const ready=authState.configured&&!authState.unavailable;
  return `<section class="login-card"><div class="login-card-heading">${logo()}<span class="subtle-tag">${e(ready?m.admin.signIn:m.admin.unconfigured)}</span></div><h2>${e(a.loginTitle)}</h2><p class="field-hint">${e(authState.unavailable?m.admin.unavailable:ready?m.admin.loginHint:m.admin.notReady)}</p><form id="login-form"><label for="account">${e(a.account)}</label><input id="account" type="text" autocomplete="username" required maxlength="64" ${ready?'':'disabled'}><label for="password">${e(a.password)}</label><input id="password" type="password" autocomplete="current-password" required ${ready?'':'disabled'}><button id="login-submit" class="button primary login-preview" type="submit" ${ready?'':'disabled'}>${e(m.admin.signIn)} ↗</button></form><p id="login-status" role="status" class="preview-hint"></p><div class="login-help"><a href="/settings/site">${e(m.site.title)} →</a></div><details class="account-help"><summary>${e(m.admin.recoveryTitle)}</summary><p class="field-hint">${e(m.admin.recoveryHint)}</p></details></section>`;
}
function workspaceView() {
  const links = [["home", "/workspace", "◈"], ["hosts", "/hosts", "▤"], ["recipes", "/recipes", "▧"], ["work", "/work", "☷"], ["logs", "/logs", "≡"], ["apps", "/apps", "⊞"], ["settings", "/settings", "⚙"]];
  const nav = ([id, href, icon]) => `<a href="${href}"${((key === id || id === "recipes" && (path === "/recipes/data" || path === "/retention")) || id === "settings" && settingsPage) ? ' class="active" aria-current="page"' : ""}><span class="nav-icon">${icon}</span>${e(id === "settings" ? m.settings.title : (roadmapCopy.nav[id] || s[id]))}${id === "operations" ? `<span class="nav-tag">${e(s.previewTag)}</span>` : ""}</a>`;
  return `<a class="skip" href="#main">${e(s.skip)}</a><aside class="sidebar" aria-label="${e(s.navigation)}">${brand("/workspace")}<div class="workspace"><span class="workspace-icon">O</span><div>${e(s.workspace)}<small>${e(authState.authenticated?(profileState?(profileState.default_profile||m.profiles.none):m.profiles.unknown):s.noProfile)}</small></div></div><div class="nav-label">${e(s.area)}</div><nav>${links.map(nav).join("")}</nav><div class="nav-label second-label">${e(s.reference)}</div><nav>${[["learn", "/learn", "▱"], ["docs", "/docs", "≡"], ["skills", "/skills", "◇"]].map(nav).join("")}</nav><div class="sidebar-bottom"><span class="status-dot"></span>${e(s.local)}<small>${e(s.server)}</small></div></aside><div class="shell"><header class="topbar"><nav class="breadcrumb" aria-label="${e(s.area)}"><a href="/workspace">${e(s.area)}</a><span>/</span><strong>${e(title)}</strong></nav><div class="topbar-right">${languageControl()}<a class="guest-link" href="/">${e(s.guestLink)}</a><span class="preview-pill">${e(authState.authenticated?t("admin.authenticated",{username:authState.username}):s.user)}</span>${authState.authenticated?`<button id="logout" class="logout-button" type="button">${e(m.admin.logout)}</button>`:""}</div></header><main id="main" tabindex="-1">${notice()}${roadmapPaths.includes(path) ? `<section id="roadmap-view"></section>` : key === "site" ? `<section id="site-settings"></section>` : settingsCategory === "profiles" ? `<section id="profile-settings"></section>` : settingsPage ? settingsView() : detailView()}${footer()}</main></div>`;
}
function settingsView() {
  const c = m.settings;
  const header = `<div class="page-heading"><div><p class="eyebrow">${e(c.kicker)}</p><h1>${e(settingsCategory ? c.categories[settingsCategory].title : c.title)}</h1><p class="intro">${e(settingsCategory ? c.categories[settingsCategory].text : c.intro)}</p></div></div>`;
  if (!settingsCatalog) return header + `<div class="detail-note" role="status">${e(c.catalogError)}</div>`;
  if(settingsCategory==="hosts")return header+`<section class="panel"><p>${e(m.hostManagement.intro)}</p><a class="button primary" href="/hosts">${e(m.hostManagement.title)} →</a></section>`;
  if (settingsCategory) {
    const category = c.categories[settingsCategory];
    return header + `<div class="settings-category-state"><span class="subtle-tag">${e(c.planned)}</span><span>${e(c.profile)}</span></div><div class="detail-note">${e(c.pending)}</div><section class="panel settings-contract"><h2>${e(c.boundaries)}</h2><p>${e(category.detail)}</p><ul>${category.rules.map(rule => `<li>${e(rule)}</li>`).join("")}</ul><p class="settings-shared-rule">${e(c.principle)}</p></section>`;
  }
  return header + versionPreview(e) + `<div class="detail-note">${e(c.principle)}</div><section class="settings-category-grid">${settingsCatalog.categories.map(category => {
    const text = c.categories[category.id];
    if (!text) return "";
    const available = category.status === "available";
    return `<a class="settings-category-card" href="${e(category.route)}"><div class="settings-card-meta"><span>${e(category.scope === "installation" ? c.installation : c.profile)}</span><span class="${available ? "available-tag" : "subtle-tag"}">${e(available ? c.available : c.planned)}</span></div><h2>${e(text.title)}</h2><p>${e(text.text)}</p><small>${e(available ? c.implemented : c.pending)}</small><span class="entry-link">${e(available ? c.open : c.explore)} <b>↗</b></span></a>`;
  }).join("")}</section><p class="field-hint">${e(c.catalogLabel)}</p>`;
}
function detailView() {
  const page = m.pages[key];
  return `<section id="detail-view"><div class="page-heading"><div><p class="eyebrow">${e(page.kicker)}</p><h1>${e(page.title)}</h1><p class="intro">${e(page.intro)}</p></div></div><div class="detail-grid">${page.cards.map(([heading, text], i) => `<article class="detail-card"><span class="entry-kicker">0${i+1} / ${e(s.plannedShort)}</span><h3>${e(heading)}</h3><p>${e(text)}</p><small>${e(s.planned)}</small></article>`).join("")}</div><div class="detail-note">${e(page.note)}</div>${["docs","learn"].includes(key) ? `<div class="roadmap-actions">${roadmapCopy.reference.links.map(([url,label])=>`<a class="button" href="${url}">${e(label)} →</a>`).join("")}</div>` : ""}</section>`;
}

function setBreadcrumb(parts) {
  const breadcrumb=document.querySelector('.breadcrumb');
  if(!breadcrumb)return;
  breadcrumb.innerHTML=`<a href="/workspace">${e(s.area)}</a>`+parts.map(part=>`<span>/</span>${part.url?`<a href="${e(part.url)}">${e(part.label)}</a>`:`<strong>${e(part.label)}</strong>`}`).join('');
  document.title=`${siteName} · ${parts.map(part=>part.label).join(' / ')}`;
}

// These templates use only the bundled catalog and fixed routes, not remote data.
document.getElementById("app").innerHTML = firstUsePage ? `<div class="public-shell setup-shell"><header class="public-header"><a class="setup-brand" href="/">${e(m.firstUse.brand)}</a>${languageControl()}</header><main id="main"><div class="setup-heading"><h1>${e(m.firstUse.title)}</h1><p>${e(m.firstUse.intro)}</p></div><div id="first-use"></div>${footer()}</main></div>` : publicPage ? publicView() : workspaceView();
if(firstUsePage){if(path!=="/setup")history.replaceState(null,"","/setup");document.title=`${m.firstUse.title} · OpsFeast`;mountFirstUse(document.getElementById("first-use"),{m,e,origin:location.origin,port:location.port});}
if(settingsCategory)setBreadcrumb([{label:m.settings.title,url:"/settings"},{label:m.settings.categories[settingsCategory]?.title||m.settings.title}]);
document.getElementById("language").value = locale;
document.getElementById("language").addEventListener("change", event => {
  saveLocale(storage, event.target.value);
  location.reload();
});
if(path==="/hosts") mountHostManager(document.getElementById("roadmap-view"),{m,e,search:location.search,setBreadcrumb});
if (roadmapPaths.includes(path)&&path!=="/hosts") mountRoadmap(document.getElementById("roadmap-view"), {path,e,siteName,search:location.search,setBreadcrumb});
if (key === "site") mountSiteSettings(document.getElementById("site-settings"), {m, e, site, siteName, authState});
if (settingsCategory === "profiles") mountProfiles(document.getElementById("profile-settings"), {m,e,authState});
if (key === "operations") mountDemo(document.getElementById("detail-view"));

function mountDemo(view) {
  const d = m.demo;
  const section = document.createElement("section");
  section.innerHTML = `<div class="demo-controls"><button id="demo-start" type="button">${e(d.start)}</button><button id="demo-stop" class="stop" type="button" disabled>${e(d.stop)}</button><span class="demo-label">${e(d.label)}</span></div><div class="terminal"><div class="terminal-title">${e(d.terminal)}</div><pre class="terminal-output" id="demo-output" aria-live="polite"></pre></div><p class="demo-status" id="demo-status" role="status"></p>`;
  view.append(section);
  const start = document.getElementById("demo-start"), stop = document.getElementById("demo-stop");
  const output = document.getElementById("demo-output"), status = document.getElementById("demo-status");
  const state = value => { status.textContent = t("demo.state", {state:value}); };
  output.textContent = d.idle; state(d.notStarted);
  let timer;
  start.addEventListener("click", () => {
    let index = 0;
    output.textContent = ""; start.disabled = true; stop.disabled = false;
    function next() {
      const [text, value] = d.frames[index++];
      output.textContent += text + "\n"; state(value);
      if (index < d.frames.length) timer = setTimeout(next, 1400);
      else { start.disabled = false; stop.disabled = true; }
    }
    next();
  });
  stop.addEventListener("click", () => {
    clearTimeout(timer); start.disabled = false; stop.disabled = true;
    output.textContent += d.stoppedOutput + "\n"; state(d.stopped);
  });
  window.addEventListener("pagehide", () => clearTimeout(timer));
}

window.addEventListener("opsfeast:site-updated", event => {
  site = event.detail;
  siteName = site.site_name || m.site.defaultName;
  siteSlogan = site.slogan || m.site.defaultSlogan;
  document.title = `${siteName} · ${title}`;
  document.querySelectorAll(".owner-brand").forEach(element => {
    element.innerHTML = `${logo()}<span class="site-brand-text">${e(siteName)}<span class="brand-sub">${e(siteSlogan)}</span></span>`;
  });
  document.querySelector("footer").outerHTML = footer();
  document.querySelector('link[rel="icon"]').href = siteAssetUrl(site, "logo");
});

if(path==='/login'&&!firstUsePage) {
  document.getElementById('login-form').addEventListener('submit',async event=>{
    event.preventDefault();
    const status=document.getElementById('login-status'),button=document.getElementById('login-submit');
    button.disabled=true;
    try{
      const response=await fetch('/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('account').value.trim(),password:document.getElementById('password').value})});
      document.getElementById('password').value='';
      if(!response.ok){status.textContent=response.status===429?m.admin.limited:m.admin.loginFailed;button.disabled=false;return;}
      location.href=loginDestination(location.search);
    }catch{status.textContent=m.admin.unavailable;button.disabled=false;}
  });
}
document.getElementById('logout')?.addEventListener('click',async()=>{
  const response=await fetch('/api/v1/auth/logout',{method:'POST'});
  if(response.ok)location.href='/';
});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
window.addEventListener('opsfeast:profile-state',event=>{
  const label=document.querySelector('.workspace small');
  if(label)label.textContent=event.detail.default_profile||m.profiles.none;
});
