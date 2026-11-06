import {workspaceUrl} from './workspace.mjs';

export function renderParameterGuide({profile,root,m,e}) {
  const c=m.settings;
  return `<section class="panel parameter-guide"><h2>${e(c.parametersWhere)}</h2><p>${e(c.parametersOwnership)}</p><p><strong>${e(m.profiles.name)}: ${e(profile||m.profiles.none)}</strong></p><p>${e(c.parametersFile)} <code>${e(root?root+'/hosts.yaml':c.parametersGenericPath)}</code></p><p class="detail-note">${e(c.parametersNoEditor)}</p><ol>${c.parametersSteps.map(text=>`<li>${e(text)}</li>`).join('')}</ol><h3>${e(c.parametersExample)}</h3><pre class="log-content">${e(c.parametersYaml)}</pre><p>${e(c.parametersPrecedence)}</p><a class="button" href="/docs?doc=docs/recipe-sources.md">${e(c.parametersGuide)} →</a><a class="button" href="/settings/profiles">${e(c.parametersChooseProfile)} →</a></section>`;
}

export function profileChildren(profile,{m,e,catalog}) {
  return `<div class="profile-settings-children">${catalog.categories.filter(category=>category.parent==='profiles').map(category=>`<a class="profile-setting-child" href="${e(workspaceUrl(category.route,profile))}"><strong>${e(m.settings.categories[category.id].title)}</strong><span>${e(m.settings.categories[category.id].text)}</span><small>${e(category.id==='parameters'?m.settings.parametersHelpLabel:category.status==='planned'?m.settings.planned:category.id==='recipes'?m.settings.readOnly:m.settings.available)}</small></a>`).join('')}</div>`;
}

export function renderSettingsTree(catalog,profiles,{m,e,profile}) {
  const c=m.settings;
  return `<div class="settings-tree">${catalog.categories.filter(category=>category.parent===null).map(category=>{
    const text=c.categories[category.id];
    if(category.id!=='profiles')return `<section class="panel settings-root"><h2><a href="${e(category.route)}">${e(text.title)} →</a></h2><p>${e(text.text)}</p><small>${e(category.id==='bundle-recipes'?c.readOnly:c.installation)}</small></section>`;
    return `<section class="panel settings-root profile-settings-root"><h2><a href="/settings/profiles">${e(text.title)} →</a></h2><p>${e(c.profileHierarchy)}</p>${profiles?profiles.profiles.length?`<label>${e(m.profiles.name)} <select id="settings-profile">${profiles.profiles.map(item=>`<option value="${e(item.name)}" ${item.name===profile?'selected':''}>${e(item.name)}</option>`).join('')}</select></label><div class="profile-owner-label">${e(c.ownedBy.replace('{profile}',profile||m.profiles.none))}</div>${profileChildren(profile,{m,e,catalog})}`:`<p>${e(m.profiles.empty)}</p>`:`<p>${e(m.profiles.loginRequired)}</p>`}</section>`;
  }).join('')}</div>`;
}

export function mountSettingsHub(root,{m,e,catalog,profiles,search=''}) {
  const requested=new URLSearchParams(search).get('profile');
  if(requested&&profiles&&!profiles.profiles.some(item=>item.name===requested)){
    root.innerHTML=`<p role="alert">${e(m.profiles.failed)}</p>`;return;
  }
  let profile=profiles?.profiles.some(item=>item.name===requested)?requested:profiles?.default_profile||profiles?.profiles[0]?.name;
  const render=()=>{
    root.innerHTML=renderSettingsTree(catalog,profiles,{m,e,profile});
    root.querySelector('#settings-profile')?.addEventListener('change',event=>{
      profile=event.target.value;
      history.replaceState(null,'',workspaceUrl('/settings',profile));render();
      window.dispatchEvent(new CustomEvent('opsfeast:profile-view',{detail:{profile}}));
    });
  };
  render();
}
