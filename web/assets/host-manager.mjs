import {mountHostNotes} from './host-notes.mjs';
import {mountHostConsoleHistory} from './host-console-history.mjs';
import {formatDateTime} from './i18n.mjs';
import {mountHostAccounts} from './host-accounts.mjs';
import {mountProfiling} from './profiling.mjs';
export function hostManagementUrl(profile,host=null,view='summary') {
  return '/hosts?'+new URLSearchParams({profile,...(host===null?{}:{host,view})});
}
export function filterManagedHosts(hosts,needle,group='',state='') {
  const query=needle.trim().toLowerCase();
  return hosts.filter(host=>{
    const values=[host.host_id,host.label,host.description,host.login_user,...host.groups,
      ...(host.reference_ips?.ipv4_addresses||[]),...(host.reference_ips?.ipv6_addresses||[])];
    return values.some(value=>String(value??'').toLowerCase().includes(query))
      &&(!group||host.groups.includes(group))&&(!state||(state==='enabled'?host.enabled:!host.enabled));
  });
}
export function normalizeHostGroups(names) {return [...new Set(names.map(name=>name.trim()).filter(Boolean))];}

export function renderManagedHostRows(hosts,{profile,l,e}) {
  return hosts.map(host=>{
    const addresses=[...(host.reference_ips.ipv4_addresses||[]),...(host.reference_ips.ipv6_addresses||[])];
    return `<tr role="row"><th scope="row" role="rowheader"><a class="host-name" href="${e(hostManagementUrl(profile,host.host_id))}">${e(host.host_id)}</a>${host.label?`<span class="host-secondary">${e(host.label)}</span>`:''}<span class="host-secondary">${e(l.user)} · ${e(host.login_user||l.unknown)}</span>${host.description?`<span class="host-description">${e(host.description)}</span>`:''}</th><td role="cell"><span class="host-cell-label" aria-hidden="true">${e(l.groups)}</span><div class="host-tags">${host.groups.length?host.groups.map(group=>`<span class="host-tag">${e(group)}</span>`).join(''):`<span class="host-secondary">${e(l.noGroups)}</span>`}</div></td><td role="cell"><span class="host-cell-label" aria-hidden="true">${e(l.savedAddresses)}</span>${addresses.length?addresses.map(ip=>`<code class="host-address">${e(ip)}</code>`).join(''):`<span class="host-secondary">${e(l.noIp)}</span>`}</td><td role="cell"><span class="host-cell-label" aria-hidden="true">${e(l.configuration)}</span><span class="host-state ${host.enabled?'is-enabled':'is-disabled'}">${e(host.enabled?l.enabledState:l.disabled)}</span></td></tr>`;
  }).join('');
}

export async function mountHostManager(root,{m,e,search,setBreadcrumb}) {
  const l=m.hostManagement,query=new URLSearchParams(search);
  root.className='host-manager';
  let snapshot,profile,profiles,busy=false;
  const request=async(path,options={})=>{
    const response=await fetch(path,options);
    const body=await response.json();
    if(!response.ok){const error=new Error('host_request_failed');error.status=response.status;error.code=body.detail;throw error;}
    return body;
  };
  const heading=(title=l.title,intro=l.intro)=>`<div class="page-heading"><div><h1>${e(title)}</h1><p class="intro">${e(intro)}</p></div></div>`;
  const errorText=error=>l.errors[error.code]||l.errors.default;
  const listUrl=()=>hostManagementUrl(profile);
  const field=(name,label,value='',attributes='')=>`<label for="host-${name}">${e(label)}<input id="host-${name}" name="${name}" value="${e(value??'')}" ${attributes}></label>`;
  const option=(value,label,selected)=>`<option value="${e(value)}" ${selected?'selected':''}>${e(label)}</option>`;
  try {
    root.innerHTML=heading()+`<p role="status">${e(l.loading)}</p>`;
    profiles=await request('/api/v1/profiles');
    profile=globalThis.location?.pathname?.startsWith('/settings')?(query.get('profile')||profiles.default_profile):profiles.default_profile;
    if(!profile){root.innerHTML=heading()+`<section class="panel"><p>${e(l.noProfile)}</p><a class="button" href="/settings/profiles">${e(l.profiles)}</a></section>`;return;}
    snapshot=await request('/api/v1/hosts?'+new URLSearchParams({profile}));
    if(query.get('new')==='1')renderEditor(null);
    else if(query.has('host'))renderDetail();
    else renderList();
  }catch(error){
    root.innerHTML=heading()+`<section class="panel"><p role="status">${e(error.status===401?l.loginRequired:l.unavailable)}</p><a class="button" href="${error.status===401?'/login?next=%2Fhosts':location.href}">${e(error.status===401?l.login:l.reload)}</a></section>`;
  }
  function renderList(){
    setBreadcrumb([{label:l.title}]);
    const enabled=snapshot.hosts.filter(host=>host.enabled).length;
    const saved=snapshot.hosts.filter(host=>host.reference_ips.status==='known').length;
    root.innerHTML=`<div class="page-heading host-page-heading"><div><p class="host-eyebrow">${e(l.kicker)}</p><h1>${e(l.title)}</h1><p class="intro">${e(l.listIntro)}</p></div><a class="button primary host-add" href="${e(listUrl()+'&new=1')}"><span aria-hidden="true">＋</span>${e(l.add)}</a></div><section class="host-metrics" aria-label="${e(l.configurationSummary)}">${[[l.totalHosts,snapshot.hosts.length,l.totalHint],[l.enabledState,enabled,l.enabledHint],[l.savedIpHosts,saved,l.savedHint]].map(([title,count,hint])=>`<article><span>${e(title)}</span><strong>${count}</strong><small>${e(hint)}</small></article>`).join('')}</section><section class="panel host-list-panel"><div class="host-list-heading"><div><h2>${e(l.listTitle)}</h2><p>${e(l.intro)}</p></div><p class="field-hint">預設 Profile：${e(profile)} · <a href="/settings/profiles">管理 Profiles</a></p></div><div class="host-filters"><label class="host-search" for="host-filter">${e(l.search)}<input type="search" id="host-filter" placeholder="${e(l.searchHint)}" aria-controls="managed-host-list" autocomplete="off"></label><label for="host-group-filter">${e(l.groupFilter)}<select id="host-group-filter"><option value="">${e(l.allGroups)}</option>${snapshot.groups.map(item=>option(item.id,item.label,false)).join('')}</select></label><label for="host-state-filter">${e(l.configuration)}<select id="host-state-filter"><option value="">${e(l.allStates)}</option>${option('enabled',l.enabledState,false)}${option('disabled',l.disabled,false)}</select></label><button class="button host-clear" id="host-clear" type="button">${e(l.clearFilters)}</button></div><p id="host-filter-count" class="host-filter-count" role="status" aria-atomic="true"></p><div id="managed-host-list"></div></section><p class="host-evidence-note">${e(l.evidenceNote)}</p>`;
    const render=()=>{
      const needle=root.querySelector('#host-filter').value,group=root.querySelector('#host-group-filter').value,state=root.querySelector('#host-state-filter').value;
      const hosts=filterManagedHosts(snapshot.hosts,needle,group,state);
      root.querySelector('#host-filter-count').textContent=l.filterCount.replace('{count}',hosts.length).replace('{total}',snapshot.hosts.length);
      root.querySelector('#host-clear').disabled=!needle&&!group&&!state;
      root.querySelector('#managed-host-list').innerHTML=hosts.length?`<table class="host-table" role="table"><caption class="host-visually-hidden">${e(l.listTitle+' · '+profile)}</caption><thead role="rowgroup"><tr role="row">${l.columns.map(name=>`<th scope="col" role="columnheader">${e(name)}</th>`).join('')}</tr></thead><tbody role="rowgroup">${renderManagedHostRows(hosts,{profile,l,e})}</tbody></table>`:`<div class="host-empty"><h3>${e(snapshot.hosts.length?l.empty:l.noHosts)}</h3><p>${e(snapshot.hosts.length?l.emptyHint:l.noHostsHint)}</p></div>`;
    };
    root.querySelector('#host-filter').oninput=render;root.querySelector('#host-group-filter').onchange=render;root.querySelector('#host-state-filter').onchange=render;
    root.querySelector('#host-clear').onclick=()=>{for(const id of ['host-filter','host-group-filter','host-state-filter'])root.querySelector('#'+id).value='';render();root.querySelector('#host-filter').focus();};render();
  }
  function renderDetail(){
    const host=snapshot.hosts.find(item=>item.host_id===query.get('host'));
    if(!host){root.innerHTML=heading(l.missing);setBreadcrumb([{label:l.title,url:listUrl()},{label:l.missing}]);return;}
    const tabs=[['summary',l.summary],['profiling',l.profiling],['settings',l.settings],['notes',l.notes],['console',l.console],['recipes',l.recipes]],view=query.get('view')||'summary';
    const label=tabs.find(([id])=>id===view)?.[1]||l.summary;
    setBreadcrumb([{label:l.title,url:listUrl()},{label:host.host_id,url:hostManagementUrl(profile,host.host_id)},{label}]);
    root.innerHTML=`<a class="host-back" href="${e(listUrl())}">← ${e(l.backToHosts)}</a><div class="page-heading host-page-heading"><div><p class="host-eyebrow">${e(l.profile)} · ${e(profile)}</p><h1>${e(host.host_id)}</h1>${host.label?`<p class="intro">${e(host.label)}</p>`:''}</div><span class="host-state ${host.enabled?'is-enabled':'is-disabled'}">${e(host.enabled?l.enabledState:l.disabled)}</span></div><nav class="draft-tabs host-tabs" aria-label="${e(l.hostSections)}">${tabs.map(([id,name])=>`<a href="${e(hostManagementUrl(profile,host.host_id,id))}" ${view===id?'aria-current="page"':''}>${e(name)}</a>`).join('')}</nav><div id="managed-host-detail"></div>`;
    const detail=root.querySelector('#managed-host-detail');
    if(view==='profiling'){void mountProfiling(detail,{profile,host_id:host.host_id,e,request});return;}
    if(view==='notes'){void mountHostNotes(detail,{profile,host_id:host.host_id,e,request});return;}
    if(view==='settings'){renderEditor(host,detail);return;}
    if(view==='recipes'){detail.innerHTML=`<section class="panel"><h2>${e(l.recipes)}</h2><p>${e(l.recipesNote)}</p><ul>${host.recipe_references.map(reference=>`<li>${e(reference)}</li>`).join('')}</ul></section>`;return;}
    if(view==='console'){void mountHostConsoleHistory(detail,{profile,host_id:host.host_id,e,request});return;}
    detail.className='host-overview';
    const observedAt=host.reference_ips.observed_at;
    const sampleTime=observedAt&&!Number.isNaN(Date.parse(observedAt))?formatDateTime(observedAt):observedAt||l.unknown;
    detail.innerHTML=`<section class="panel host-evidence-panel"><p class="host-eyebrow">${e(l.savedEvidence)}</p><h2>${e(l.inventory)}</h2><p>${e(l.summaryNote)}</p>${host.reference_ips.collected_families?.join(',')==='4'?`<p class="field-hint">${e(l.ipv4Only)}</p>`:''}<dl class="log-metadata"><dt>IPv4</dt><dd>${e(host.reference_ips.ipv4_addresses?.join(', ')||l.unknown)}</dd><dt>IPv6</dt><dd>${e(host.reference_ips.ipv6_addresses?.join(', ')||l.unknown)}</dd><dt>${e(l.sampledAt)}</dt><dd>${e(sampleTime)}</dd><dt>${e(l.groups)}</dt><dd>${e(host.groups.join(' / ')||l.noGroups)}</dd><dt>${e(l.source)}</dt><dd>${e(host.source)}</dd></dl></section>`;
    const resultPanel=document.createElement('section');resultPanel.className='panel host-result-panel';detail.append(resultPanel);
    const resultHeading=`<p class="host-eyebrow">${e(l.savedEvidence)}</p><h2>${e(l.latestResult)}</h2>`;
    resultPanel.innerHTML=resultHeading+`<p role="status">${e(l.loading)}</p>`;
    request('/api/v1/results/latest?'+new URLSearchParams({profile,host_id:host.host_id})).then(data=>{
      const row=data.result;
      resultPanel.innerHTML=resultHeading+(row?`<p class="host-result-state" role="status">${e(l.resultStates[row.status]||row.status)}</p><a class="button host-secondary-button" href="${e('/logs?'+new URLSearchParams({profile,result:row.short_id}))}">${e(l.inspectCauses)} →</a>${data.invalid_result_count?`<p role="status">${e(l.resultError)}</p>`:''}`:`<p role="status">${e(data.invalid_result_count?l.resultError:l.noResult)}</p>`);
    }).catch(()=>{resultPanel.innerHTML=resultHeading+`<p role="status">${e(l.resultError)}</p>`;});
  }
  function renderEditor(host,target=root){
    const creating=host===null,connection=host?.connection||{},mode=connection.local?'local':connection.ssh_config_alias?'alias':'ssh';
    let groups=[...(host?.groups||[])];
    if(creating)setBreadcrumb([{label:l.title,url:listUrl()},{label:l.add}]);
    target.innerHTML=(creating?heading(l.add,profile):'')+`<form id="managed-host-form" class="panel managed-host-form">${field('id',l.hostId,host?.host_id||'',creating?'required maxlength="200"':'readonly')}<p class="field-hint">${e(l.immutable)}</p>${field('label',l.label,host?.label||'','maxlength="4000"')}<label>${e(l.description)}<textarea name="description" maxlength="4000">${e(host?.description||'')}</textarea></label><label class="draft-toggle"><input name="enabled" type="checkbox" ${host?.enabled?'checked':''}>${e(l.enabled)}</label><h2>${e(l.connection)}</h2><label>${e(l.mode)}<select name="mode" ${creating?'':'disabled'}>${[['ssh',l.ssh],['local',l.local],['alias',l.alias]].map(([id,name])=>option(id,name,mode===id)).join('')}</select></label><div id="host-connection-fields"></div><p class="field-hint">${e(l.connectionNote)}</p><h2>${e(l.groups)}</h2>${host?.parent_group?`<p class="field-hint">${e(l.parentGroup.replace('{group}',host.parent_group))}</p>`:''}<div id="host-group-chips"></div><div class="unlock-row"><label>${e(l.groupInput)}<input id="host-group-input" list="host-group-options" autocomplete="off"></label><button class="button" type="button" id="host-group-add">${e(l.groupAdd)}</button></div><datalist id="host-group-options">${snapshot.groups.map(item=>`<option value="${e(item.id)}">${e(item.label)}</option>`).join('')}</datalist><p class="field-hint">${e(l.groupHint)}</p><p id="host-form-status" class="admin-result" role="status" tabindex="-1"></p><p class="field-hint">${e(l.backupNote)}</p><div class="setup-actions"><button id="host-submit" type="submit" class="button primary">${e(creating?l.create:l.save)}</button><a class="button" href="${e(creating?listUrl():hostManagementUrl(profile,host.host_id))}">${e(l.cancel)}</a></div></form>${!creating?`<div id="managed-host-accounts"></div><section class="panel roadmap-section host-delete-zone"><h2>${e(l.deleteTitle)}</h2><p>${e(l.deleteIntro)}</p><button class="button danger" id="host-delete-open" type="button">${e(l.deleteTitle)}</button></section><dialog id="host-delete-dialog" class="host-confirm-dialog"><form id="host-delete-form"><h2>${e(l.deleteTitle)}</h2><p>${e(l.deleteIntro)}</p><dl class="log-metadata"><dt>${e(l.profile)}</dt><dd>${e(profile)}</dd><dt>${e(l.hostId)}</dt><dd>${e(host.host_id)}</dd><dt>${e(l.source)}</dt><dd>${e(host.source)}</dd></dl><label>${e(l.deletePrompt.replace('{host}',host.host_id))}<input id="host-delete-confirm" autocomplete="off"></label><p id="host-delete-status" role="status" class="admin-result"></p><div class="setup-actions"><button id="host-delete-submit" class="button danger" type="submit" disabled>${e(l.deleteConfirm)}</button><button id="host-delete-cancel" class="button" type="button">${e(l.cancel)}</button></div></form></dialog>`:''}`;
    if(!creating)mountHostAccounts(target.querySelector('#managed-host-accounts'),{profile,host,l,e,request,getRevision:()=>snapshot.revision,onSaved:revision=>{snapshot.revision=revision;}});
    const form=target.querySelector('#managed-host-form');
    function connectionFields(){
      const currentMode=form.elements.mode.value;
      target.querySelector('#host-connection-fields').innerHTML=currentMode==='local'?'':currentMode==='alias'?field('alias',l.sshAlias,connection.ssh_config_alias||'','required'):`<div class="draft-grid">${field('hostname',l.hostname,connection.hostname||'','required')}${field('user',l.user,connection.user||'')}${field('port',l.port,connection.port||22,'type="number" min="1" max="65535" required')}${field('identity_file',l.identityFile,connection.identity_file||'')}</div>`;
      if(currentMode!=='local'&&(!host?.advanced_connection||connection.via))target.querySelector('#host-connection-fields').insertAdjacentHTML('beforeend',`<label>${e(l.via)}<select name="via"><option value="">${e(l.direct)}</option>${snapshot.hosts.filter(item=>item.host_id!==host?.host_id&&!item.connection.local&&item.enabled).map(item=>option(item.host_id,item.host_id,item.host_id===connection.via?.host)).join('')}</select></label>`);
    }
    function chips(){
      target.querySelector('#host-group-chips').innerHTML=groups.map((group,index)=>`<span class="host-group-chip">${e(group)}<button type="button" data-group-remove="${index}" aria-label="${e(l.groupRemove+' '+group)}" ${group===host?.parent_group?'disabled':''}>×</button></span>`).join('');
      target.querySelectorAll('[data-group-remove]').forEach(button=>button.onclick=()=>{groups.splice(Number(button.dataset.groupRemove),1);chips();});
    }
    const addGroup=()=>{const input=target.querySelector('#host-group-input');groups=normalizeHostGroups([...groups,input.value]);input.value='';chips();};
    target.querySelector('#host-group-add').onclick=addGroup;
    target.querySelector('#host-group-input').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();addGroup();}};
    form.elements.mode.onchange=connectionFields;connectionFields();chips();
    form.onsubmit=async event=>{
      event.preventDefault();if(busy)return;
      const pendingGroup=target.querySelector('#host-group-input').value.trim();
      if(pendingGroup)addGroup();
      const data={group:groups,enabled:form.elements.enabled.checked,label:form.elements.label.value,description:form.elements.description.value};
      const currentMode=form.elements.mode.value;
      if(currentMode==='local'){if(creating)data.connection={local:true};}
      else if(currentMode==='alias')data.connection={ssh_config_alias:form.elements.alias.value.trim()};
      else{
        data.connection={hostname:form.elements.hostname.value.trim(),user:form.elements.user.value.trim(),port:Number(form.elements.port.value)};
        if(form.elements.identity_file.value.trim())data.connection.identity_file=form.elements.identity_file.value.trim();
        else if(!creating)data.connection.identity_file=null;
        if(!data.connection.user){if(creating)delete data.connection.user;else data.connection.user=null;}
      }
      if(form.elements.via){
        if(form.elements.via.value)data.connection.via={host:form.elements.via.value};
        else if(!creating)data.connection.via=null;
      }
      busy=true;target.querySelector('#host-submit').disabled=true;
      const message=target.querySelector('#host-form-status');message.textContent=l.saving;
      try{
        await request('/api/v1/hosts',{method:creating?'POST':'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,host_id:form.elements.id.value,expected_revision:snapshot.revision,changes:data})});
        location.href=hostManagementUrl(profile,form.elements.id.value,'settings');
      }catch(error){message.textContent=errorText(error);message.focus();busy=false;target.querySelector('#host-submit').disabled=false;}
    };
    if(!creating){
      const dialog=target.querySelector('#host-delete-dialog'),confirm=target.querySelector('#host-delete-confirm');
      target.querySelector('#host-delete-open').onclick=()=>{confirm.value='';target.querySelector('#host-delete-submit').disabled=true;dialog.showModal();confirm.focus();};
      target.querySelector('#host-delete-cancel').onclick=()=>dialog.close();
      dialog.oncancel=event=>{if(busy)event.preventDefault();};
      confirm.oninput=()=>{target.querySelector('#host-delete-submit').disabled=confirm.value!==host.host_id;};
      target.querySelector('#host-delete-form').onsubmit=async event=>{
        event.preventDefault();if(busy||confirm.value!==host.host_id)return;
        busy=true;target.querySelector('#host-delete-submit').disabled=true;target.querySelector('#host-delete-cancel').disabled=true;
        target.querySelector('#host-delete-status').textContent=l.deleteBusy;
        try{
          await request('/api/v1/hosts',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,host_id:host.host_id,expected_revision:snapshot.revision,confirmation:confirm.value})});location.href=listUrl();
        }catch(error){target.querySelector('#host-delete-status').textContent=errorText(error);busy=false;target.querySelector('#host-delete-submit').disabled=false;target.querySelector('#host-delete-cancel').disabled=false;}
      };
    }
  }
}
