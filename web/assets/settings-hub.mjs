import {workspaceUrl} from './workspace.mjs';

export function renderParameterGuide({profile,root,m,e}) {
  const c=m.settings;
  return `<section class="panel parameter-guide"><h2>${e(c.parametersWhere)}</h2><p>${e(c.parametersOwnership)}</p><p><strong>${e(m.profiles.name)}: ${e(profile||m.profiles.none)}</strong></p><p>${e(c.parametersFile)} <code>${e(root?root+'/hosts.yaml':c.parametersGenericPath)}</code></p><p class="detail-note">${e(c.parametersNoEditor)}</p><ol>${c.parametersSteps.map(text=>`<li>${e(text)}</li>`).join('')}</ol><h3>${e(c.parametersExample)}</h3><pre class="log-content">${e(c.parametersYaml)}</pre><p>${e(c.parametersPrecedence)}</p><a class="button" href="/docs?doc=docs/recipe-sources.md">${e(c.parametersGuide)} →</a><a class="button" href="/settings/profiles">${e(c.parametersChooseProfile)} →</a></section>`;
}

export function profileChildren(profile,{m,e,catalog,defaultProfile=profile}) {
  return `<div class="profile-settings-children">${catalog.categories.filter(category=>category.parent==='profiles'&&(category.id!=='hosts'||profile===defaultProfile)).map(category=>`<a class="profile-setting-child" href="${e(workspaceUrl(category.route,profile))}"><strong>${e(m.settings.categories[category.id].title)}</strong><span>${e(m.settings.categories[category.id].text)}</span><small>${e(category.id==='parameters'?m.settings.parametersHelpLabel:category.status==='planned'?m.settings.planned:category.id==='recipes'?m.settings.readOnly:m.settings.available)}</small></a>`).join('')}</div>`;
}

export function renderSettingsTree(catalog,profiles,{m,e}) {
  const profile=profiles?.default_profile;
  const c=m.settings;
  return `<div class="settings-tree">${catalog.categories.filter(category=>category.parent===null).map(category=>{
    const text=c.categories[category.id];
    if(category.id!=='profiles')return `<section class="panel settings-root"><h2><a href="${e(category.route)}">${e(text.title)} →</a></h2><p>${e(text.text)}</p><small>${e(category.id==='bundle-recipes'?c.readOnly:c.installation)}</small></section>`;
    return `<section class="panel settings-root profile-settings-root"><h2><a href="/settings/profiles">${e(text.title)} →</a></h2><p>${e(c.profileHierarchy)}</p>${profiles?profile?`<p class="profile-current-default"><strong>${e(m.profiles.current)}：${e(profile)}</strong></p><div class="profile-owner-label">${e(c.ownedBy.replace('{profile}',profile))}</div>${profileChildren(profile,{m,e,catalog,defaultProfile:profile})}`:`<p>${e(m.profiles.empty)}</p>`:`<p>${e(m.profiles.loginRequired)}</p>`}</section>`;
  }).join('')}</div>`;
}

export function mountSettingsHub(root,{m,e,catalog,profiles}) {
  root.innerHTML=renderSettingsTree(catalog,profiles,{m,e});
}
