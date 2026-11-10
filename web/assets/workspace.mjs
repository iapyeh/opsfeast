import c from './locales/workspace-zh-TW.mjs';
import {formatDateTime} from './i18n.mjs';
import {mountRecipeMenu} from './recipe-menu.mjs';
export const workspaceCopy = c;
export const workspacePaths = Object.keys(c.titles);
export const workspaceUrl = (path, profile, extra={}) => {
  const query = new URLSearchParams(extra);
  if(profile)query.set('profile',profile);
  return path + (query.size?'?'+query:'');
};
const state=value=>{
  if(typeof value==='string')return c.states[value]||value;
  if(value&&typeof value==='object'&&!Array.isArray(value)&&Object.values(value).every(count=>Number.isInteger(count)&&count>=0))
    return Object.entries(value).map(([name,count])=>(c.states[name]||name)+' '+count).join(' · ')||c.unknown;
  return JSON.stringify(value??c.unknown);
};
const time=value=>{try{return value?formatDateTime(value):c.unknown;}catch{return String(value??c.unknown);}};
const json=value=>JSON.stringify(value,null,2);
const statusBadge=(value,e)=>{
  const tone=(value&&typeof value==='object'&&value.failed>0)||['failed','error','critical'].includes(value)?'danger':['partial','warning','blocked'].includes(value)?'warning':['success','done','resolved'].includes(value)?'success':'neutral';
  return `<span class="data-state data-state-${tone}">${e(state(value))}</span>`;
};
export function table(headers, rows, e) {
  return rows.length?`<div class="table-scroll"><table class="roadmap-table"><thead><tr>${headers.map(value=>`<th scope="col">${e(value)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(value=>`<td>${value}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:`<p role="status">${e(c.empty)}</p>`;
}
function objects(items,e) {
  return items.length?items.map(item=>`<article class="attention-row"><span class="priority">${e(state(item.severity||item.priority||'unknown'))}</span><div><h3>${e(item.title)}</h3><p>${statusBadge(item.status,e)} · ${e(item.source?.host_id||c.unknown)}</p><p>${e(item.body||'')}</p><small>${e(time(item.updated_at))}</small></div></article>`).join(''):`<p role="status">${e(c.empty)}</p>`;
}
export function renderData(path,data,{e,profile,recipeScope='all'}) {
  const link=(target,label,extra={})=>`<a href="${e(workspaceUrl(target,profile,extra))}">${e(label)}</a>`;
  let html=data.status!=='success'?`<p class="detail-note" role="status">${e(c.partial)}</p>`:'';
  if(path==='/workspace') {
    html+=`<section class="panel workspace-summary-panel"><div><h2>${e(c.hostCount)}</h2><strong class="workspace-host-count">${e(data.host_count)}</strong></div><p class="field-hint">${e(c.summaryNote)}</p></section><div class="roadmap-columns">`;
    for(const name of ['notifications','todos']) {
      const component=data.components[name];
      html+=`<section class="panel"><div class="panel-heading"><h2>${e(c[name])}${component.status==='success'?` (${e(component.total)})`:''}</h2>${link('/work',c.all)}</div>${component.status==='success'?objects(component.items,e):`<p role="status">${e(c.failed)}</p>`}</section>`;
    }
    return html+'</div><section class="entry-grid roadmap-section">'+['hosts','recipes','retention','logs'].map(key=>`<article class="entry-card">${link('/'+key,c.links[key])}</article>`).join('')+'</section>';
  }
  if(path==='/recipes') {
    html+=`<p class="field-hint">${e(c.catalogNote)}</p><details><summary>${e(c.sources)}</summary><pre class="log-content">${e(json(data.sources))}</pre></details>`;
    return html+table(c.recipeColumns,data.items.map(item=>[link(recipeScope==='bundle'?'/settings/bundle-recipes':recipeScope==='user'?'/settings/recipes':'/recipes',item.reference,{recipe:item.reference}),e(item.version??c.unknown),e(state(item.source)),statusBadge(item.status,e)]),e)+data.items.map(item=>`<details class="panel roadmap-section"><summary>${e(item.reference)} · ${e(item.title||item.id||'')}</summary><p>${e(item.description||'')}</p><h3>${e(c.recipeDetails)}</h3><pre class="log-content">${e(json(item))}</pre></details>`).join('');
  }
  if(path==='/work')return html+`<p class="field-hint">${e(c.serviceNote)}</p>`+table(c.workColumns,data.items.map(item=>[e(state(item.kind)),`<details><summary>${e(item.title)}</summary><p>${e(item.body||'')}</p><pre class="log-content">${e(json(item))}</pre></details>`,statusBadge(item.status,e),e(item.source?.host_id||c.unknown),e(time(item.updated_at))]),e);
  if(path==='/logs')return html+`<p class="field-hint">${e(c.logsNote)}</p>`+table(c.logColumns,data.items.map(item=>[e(time(item.time)),e(state(item.source)),`${item.source==='console'?link(item.url,c.history):link('/logs',item.title,{entry:item.id})}<details><summary>${e(item.title)}</summary>${(item.result_links||[]).length?`<h3>${e(c.resultCauses)}</h3><ul>${item.result_links.map(row=>`<li>${link('/logs',row.host_id+' · '+state(row.status)+' · '+c.diagnosis,{result:row.result_id})}</li>`).join('')}</ul>`:''}<pre class="log-content">${e(json(item.details))}</pre></details>`,statusBadge(item.status,e)]),e);
  return html+`<p class="field-hint">${e(c.retentionNote)}</p>`+table(c.retentionColumns,data.items.map(item=>[e(time(item.observed_at)),e(item.host_id),e(item.recipe_reference),e(item.kind),statusBadge(item.status,e)]),e);
}

export async function mountWorkspace(root,{path,e,siteName,search='',profiles=null,recipeScope='all',fetchImpl=fetch}) {
  if(path==='/recipes'&&recipeScope==='all')return mountRecipeMenu(root,{e,profiles,search,fetchImpl});
  const query=new URLSearchParams(search);
  let profile=query.get('profile')||profiles?.default_profile;
  const title=recipeScope==='bundle'?c.bundleRecipes:recipeScope==='user'?c.userRecipes:c.titles[path];
  root.innerHTML=`<div class="page-heading"><div><p class="eyebrow">${e(siteName)}</p><h1>${e(title)}</h1><p class="intro">${e(recipeScope==='bundle'?c.bundleNote:recipeScope==='user'?c.userNote:c.intros[path])}</p></div></div><div id="workspace-content" class="panel roadmap-section" role="status">${e(c.loading)}</div>`;
  const content=root.querySelector('#workspace-content');
  if(path==='/workspace')content.className='workspace-overview roadmap-section';
  const read=async url=>{
    const response=await fetchImpl(url);
    if(!response.ok)throw new Error(response.status===401?'unauthorized':'failed');
    return response.json();
  };
  try {
    if(recipeScope==='bundle'||recipeScope==='user'){
      const owner=recipeScope==='user'?profile:profiles?.default_profile;
      const target=owner?workspaceUrl('/settings/parameters',owner):'/settings/profiles';
      content.insertAdjacentHTML('beforebegin',`<p class="detail-note">${e(c.parametersLocation)} <a class="button" href="${e(target)}">${e(c.parametersAction)}${owner?' ('+e(owner)+')':''} →</a></p>`);
    }
    if(['/docs','/learn','/skills'].includes(path)) {
      const kind=path.slice(1), data=await read('/api/v1/library?kind='+kind);
      const doc=query.get('doc');
      if(doc){
        const selected=data.items.find(item=>item.path===doc);
        if(!selected){content.textContent=c.notFound;return;}
        const source=await read('/api/v1/library/content?'+new URLSearchParams({path:doc}));
        content.innerHTML=`<a href="${path}">← ${e(c.back)}</a><h2>${e(doc)}</h2><p>${e(c.libraryNote)}</p><pre class="document-source">${e(source.content)}</pre>`;
      }else{
        content.innerHTML=`<p>${e(c.libraryNote)}</p><label class="library-search">${e(c.search)}<input type="search" id="library-query"></label><div id="library-items" class="library-index"></div>`;
        const render=()=>{const needle=content.querySelector('#library-query').value.toLowerCase();content.querySelector('#library-items').innerHTML=data.items.filter(item=>[item.path,item.title||''].some(value=>value.toLowerCase().includes(needle))).map(item=>`<a class="library-entry" href="${e(workspaceUrl(path,null,{doc:item.path}))}"><strong>${e(item.title||item.path)}</strong><span>${e(item.path)}</span></a>`).join('')||`<p>${e(c.empty)}</p>`;};
        content.querySelector('#library-query').addEventListener('input',render);render();
      }
      return;
    }
    if(['/operations','/apps'].includes(path)) {
      const guides=path==='/operations'?[['/hosts',c.links.hosts],['/logs',c.links.logs],['/docs?doc=docs/console-agent.md',c.links.console]]:[['/docs?doc=docs/host-vault.md',c.links.vault],['/docs?doc=docs/retention.md',c.links.appGuide]];
      content.innerHTML=`<p>${e(path==='/operations'?c.operationsNote:c.appsNote)}</p>`+guides.map(([url,label])=>`<p><a href="${e(url)}">${e(label)} →</a></p>`).join('');return;
    }
    if(recipeScope!=='bundle'&&!profiles){const response=await read('/api/v1/profiles');profiles=response;profile=query.get('profile')||profiles.default_profile;}
    if(recipeScope!=='bundle'&&!profile){content.innerHTML=`<p>${e(c.noProfile)}</p><a href="/settings/profiles">${e(c.profiles)}</a>`;return;}
    if(recipeScope!=='bundle')content.insertAdjacentHTML('beforebegin',`<label class="workspace-profile">${e(c.profile)} <select id="workspace-profile">${profiles.profiles.map(item=>`<option value="${e(item.name)}" ${item.name===profile?'selected':''}>${e(item.name)}</option>`).join('')}</select></label>`);
    root.querySelector('#workspace-profile')?.addEventListener('change',event=>{location.href=workspaceUrl(recipeScope==='user'?'/settings/recipes':path,event.target.value);});
    if(path==='/logs'&&query.get('result')) {
      const loadDiagnosis=async(limit=5)=>{
        const data=await read('/api/v1/results/diagnosis?'+new URLSearchParams({profile,result_id:query.get('result'),limit:String(limit)}));
        content.innerHTML=renderDiagnosis(data,{e,profile});
        content.querySelector('#diagnosis-more')?.addEventListener('click',()=>loadDiagnosis(50).catch(()=>content.insertAdjacentHTML('beforeend',`<p role="alert">${e(c.failed)}</p>`)));
      };
      await loadDiagnosis();return;
    }
    const section={'/workspace':'summary','/recipes':'recipes','/work':'work','/logs':'logs','/retention':'retention','/recipes/data':'retention'}[path];
    if(section!=='summary') {
      content.insertAdjacentHTML('beforebegin',`<form id="workspace-filter" class="filter-bar"><label>${e(c.search)}<input name="q" type="search" maxlength="1000" value="${e(query.get('q')||'')}"></label>${section==='work'?`<label>${e(c.type)}<select name="kind"><option value="">${e(c.everything)}</option>${['todo','notification'].map(kind=>`<option value="${kind}" ${query.get('kind')===kind?'selected':''}>${e(c.states[kind])}</option>`).join('')}</select></label>`:''}<button type="submit" class="button">${e(c.apply)}</button></form>`);
      root.querySelector('#workspace-filter').addEventListener('submit',event=>{event.preventDefault();const values=Object.fromEntries([...new FormData(event.target)].filter(([,value])=>value));location.href=workspaceUrl(recipeScope==='bundle'?'/settings/bundle-recipes':recipeScope==='user'?'/settings/recipes':path,recipeScope==='bundle'?null:profile,values);});
    }
    const item=query.get(path==='/recipes'?'recipe':'entry');
    let accumulated=[], next=null;
    const load=async(offset=0)=>{
      const args={offset:String(offset)};
      if(recipeScope==='bundle')args.scope='bundle';
      else {args.profile=profile;if(recipeScope==='user')args.scope='user';}
      for(const name of ['q','kind'])if(query.get(name))args[name]=query.get(name);
      if(item)args.item_id=item;
      const data=await read('/api/v1/workspace/'+section+'?'+new URLSearchParams(args));
      accumulated.push(...(data.items||[]));next=data.next_offset;
      content.innerHTML=renderData(path,{...data,items:accumulated},{e,profile:recipeScope==='bundle'?null:profile,recipeScope})+`<p class="field-hint">${data.profile?e(c.profile)+': '+e(data.profile)+' · ':''}${e(c.readAt)}: ${e(time(data.read_at))} · ${e(c.timezone)}</p>`+(next!=null?`<button type="button" id="workspace-more" class="button">${e(c.more)}</button>`:'');
      content.querySelector('#workspace-more')?.addEventListener('click',async event=>{event.target.disabled=true;try{await load(next);}catch{event.target.disabled=false;content.insertAdjacentHTML('beforeend',`<p role="alert">${e(c.failed)}</p>`);}});
    };
    await load();
  }catch(error){content.innerHTML=`<p role="alert">${e(error.message==='unauthorized'?c.unauthorized:c.failed)}</p>${error.message==='unauthorized'?`<a href="/login">${e(c.login)}</a>`:''}`;}
}


export function renderDiagnosis(data,{e,profile}) {
  const reason=value=>c.reasons[value]||value||c.unknown;
  return `<a href="${e(workspaceUrl('/logs',profile))}">← ${e(c.back)}</a><h2>${e(c.diagnosis)} · ${e(data.host_id)}</h2><p>${e(c.status)}: ${e(state(data.status))} · ${e(data.reason_code||'')}</p><p>${e(c.missingFields)}: ${e(data.coverage_gap_count||0)} · ${e(c.commandIssues)}: ${e(data.issue_count)}</p>`+
    table(c.gapColumns,(data.coverage_gaps||[]).map(gap=>[e(gap.job),e(gap.properties.join(', ')),e(reason(gap.reason_code)),e(time(gap.observed_at))]),e)+
    (data.issues||[]).map(issue=>`<section class="panel roadmap-section"><h3>${e(reason(issue.reason_code))}</h3><p>${e(issue.stage)} · ${e(issue.error_type||'')}</p>${issue.command?`<pre class="log-content">${e(issue.command)}</pre>`:''}${['stderr','stdout'].map(name=>issue[name]?`<pre class="log-content">${e(issue[name].text)}</pre>`:'').join('')}</section>`).join('')+
    (data.omitted_count||data.omitted_coverage_groups?`<p>${e(c.boundedDiagnosis)}</p><button class="button" type="button" id="diagnosis-more">${e(c.more)}</button>`:'')+
    (data.notes||[]).map(note=>`<p class="field-hint">${e(note)}</p>`).join('');
}
