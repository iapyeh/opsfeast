import {hostRecords} from './host-model.mjs';
import {hostRowsHtml,mountHostDraft} from './host-draft.mjs';
import copy from './locales/roadmap-zh-TW.mjs';
export const roadmapCopy = copy;
export const roadmapPaths = ['/workspace','/hosts','/recipes','/recipes/data','/retention','/work','/logs','/skills'];
export function filterRows(rows, query='', category='', categoryIndex=2, searchColumns=[0]) {
  const needle=query.trim().toLowerCase();
  return rows.filter(row=>(!needle||searchColumns.some(index=>row[index].toLowerCase().includes(needle)))&&(!category||row[categoryIndex]===category));
}
export function mountRoadmap(root,{path,e,siteName,search="",setBreadcrumb=()=>{}}) {
  const c=copy;
  const query=new URLSearchParams(search);
  const pending=labels=>`<div class="roadmap-actions">${labels.map(label=>`<button class="button" type="button" disabled title="${e(c.pending)}">${e(label)} · ${e(c.pending)}</button>`).join('')}</div>`;
  const heading=(title,intro)=>`<div class="page-heading"><div><p class="eyebrow">${e(siteName)}</p><h1>${e(title)}</h1><p class="intro">${e(intro)}</p></div><span class="subtle-tag">${e(c.home.badge)}</span></div><p class="detail-note">${e(c.preview)}</p>`;
  const tabs=(labels,id)=>`<div class="roadmap-tabs" role="group" aria-label="${e(id)}">${labels.map((label,i)=>`<button type="button" data-tab="${i}" class="${i?'':'selected'}" aria-pressed="${!i}">${e(label)}</button>`).join('')}</div>`;
  const records=(rows,actions)=>rows.map(([priority,title,state,note])=>`<article class="attention-row"><span class="priority">${e(priority)}</span><div><h3>${e(title)}</h3><p>${e(state)}</p><small>${e(note)}</small>${actions?pending(actions):''}</div></article>`).join('');
  const lifecycle=()=>`<p class="field-hint">${e(c.actionsNote)}</p>`;
  const transfer=()=>`<section class="panel roadmap-section"><h2>${e(c.recipes.transfer)}</h2><p>${e(c.recipes.transferNote)}</p><p class="field-hint">${e(c.recipes.scope)}</p>${pending([c.export,c.import,c.archive,c.restore,c.remove])}${lifecycle()}</section>`;
  if(path==='/workspace') {
    root.innerHTML=heading(c.home.title,c.home.intro)+`<div class="roadmap-columns"><section class="panel"><div class="panel-heading"><h2>${e(c.home.notifications)}</h2><a href="/work">${e(c.home.more)} →</a></div>${records(c.notices)}<p class="field-hint">${e(c.home.context)}</p></section><section class="panel"><div class="panel-heading"><h2>${e(c.home.todos)}</h2><a href="/work">${e(c.home.more)} →</a></div>${records(c.todos)}</section></div><section class="entry-grid roadmap-section">${c.home.links.map(([url,title,text])=>`<a class="entry-card" href="${url}"><h3>${e(title)}</h3><p>${e(text)}</p><span class="entry-link">→</span></a>`).join('')}</section>`;
  } else if(path==='/hosts') {
    const d=c.hosts;
    if(query.has('host')){mountHostDraft(root,{query,e,heading,setBreadcrumb});return;}
    root.innerHTML=heading(d.title,d.intro)+`<section class="panel roadmap-section"><div class="filter-bar"><label>${e(d.search)}<input id="record-query" type="search" placeholder="demo-web"></label><label>${e(d.group)}<select id="record-category"><option value="">${e(c.all)}</option>${[...new Set(d.rows.map(row=>row[2]))].map(value=>`<option>${e(value)}</option>`).join('')}</select></label></div><div id="record-list"></div></section><p class="detail-note">${e(d.note)}</p>`;
    const render=()=>root.querySelector('#record-list').innerHTML=`<div class="table-scroll"><table class="roadmap-table"><thead><tr>${d.columns.map(label=>`<th scope="col">${e(label)}</th>`).join('')}</tr></thead><tbody>${hostRowsHtml(filterRows(d.rows,root.querySelector('#record-query').value,root.querySelector('#record-category').value),e)}</tbody></table></div>`;
    root.querySelector('#record-query').addEventListener('input',render);root.querySelector('#record-category').addEventListener('change',render);render();
  } else if(path==='/logs') {
    const d=c.logs, entry=query.get('entry');
    if(entry!==null){
      const selectedHost=query.get('host');
      const contextual=selectedHost&&c.hosts.rows.some(row=>row[0]===selectedHost)?hostRecords(selectedHost).find(record=>record.id===entry):null;
      if(selectedHost){
        if(!contextual){setBreadcrumb([{label:d.title,url:'/logs'},{label:c.notFound}]);root.innerHTML=heading(d.detail,c.notFound);return;}
        const source=contextual.source==='interactive'?d.rows[0][1]:d.rows[1][1];
        const parentView=contextual.source==='interactive'?'console':'recipes';
        setBreadcrumb([{label:c.hosts.title,url:'/hosts'},{label:selectedHost,url:'/hosts?'+new URLSearchParams({host:selectedHost,view:'summary'})},{label:parentView==='console'?c.hosts.tabs[2][1]:c.hosts.tabs[3][1],url:'/hosts?'+new URLSearchParams({host:selectedHost,view:parentView})},{label:contextual.time}]);
        const url='/logs?'+new URLSearchParams({host:selectedHost,entry});
        root.innerHTML=heading(d.detail,contextual.summary)+`<div class="roadmap-actions"><a class="button" href="${e(url)}" target="_blank" rel="noopener">${e(c.newWindow)} ↗</a></div><section class="panel roadmap-section"><dl class="log-metadata"><dt>${e(d.columns[0])}</dt><dd>${e(contextual.time)}</dd><dt>${e(d.columns[1])}</dt><dd>${e(source)}</dd></dl><p class="field-hint">${e(c.timezone)}</p><pre class="log-content">${e(contextual.lines.join('\n'))}</pre>${pending([c.export,c.archive,c.restore,c.remove])}</section>`;
        return;
      }
      const index=d.entries.findIndex(item=>item.id===entry);
      if(index<0){setBreadcrumb([{label:d.title,url:'/logs'},{label:c.notFound}]);root.innerHTML=heading(d.detail,c.notFound);return;}
      const row=d.rows[index],url=logUrl(index);
      setBreadcrumb([{label:d.title,url:'/logs'},{label:row[0]}]);
      root.innerHTML=heading(d.detail,row[2])+`<div class="roadmap-actions"><a class="button" href="${url}" target="_blank" rel="noopener">${e(c.newWindow)} ↗</a></div><section class="panel roadmap-section"><dl class="log-metadata"><dt>${e(d.columns[0])}</dt><dd>${e(row[0])}</dd><dt>${e(d.columns[1])}</dt><dd>${e(row[1])}</dd></dl><p class="field-hint">${e(c.timezone)}</p><h2>${e(d.content)}</h2><pre class="log-content">${e(d.entries[index].lines.join('\n'))}</pre>${pending([c.export,c.archive,c.restore,c.remove])}</section><p class="detail-note">${e(d.note)}</p>`;
      return;
    }
    root.innerHTML=heading(d.title,d.intro)+`<section class="panel roadmap-section"><div class="filter-bar"><label>${e(d.search)}<input id="record-query" type="search"></label><label>${e(d.source)}<select id="record-category"><option value="">${e(c.all)}</option>${[...new Set(d.rows.map(row=>row[1]))].map(value=>`<option>${e(value)}</option>`).join('')}</select></label></div><p class="field-hint">${e(c.timezone)}</p><div id="record-list"></div></section><p class="detail-note">${e(d.note)}</p>${pending([c.archive,c.restore,c.remove])}${lifecycle()}`;
    const render=()=>{const rows=filterRows(d.rows,root.querySelector('#record-query').value,root.querySelector('#record-category').value,1,[0,2]);root.querySelector('#record-list').innerHTML=`<div class="table-scroll"><table class="roadmap-table"><thead><tr>${d.columns.map(label=>`<th scope="col">${e(label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>{const index=d.rows.indexOf(row);return `<tr><td><a class="record-time" href="${logUrl(index)}">${e(row[0])}</a></td><td>${e(row[1])}</td><td class="summary-cell">${e(row[2])}</td></tr>`;}).join('')}</tbody></table>${rows.length?'':`<p role="status">${e(c.empty)}</p>`}</div>`;};
    root.querySelector('#record-query').addEventListener('input',render);root.querySelector('#record-category').addEventListener('change',render);render();
  } else if(path==='/work') {
    const d=c.work;
    root.innerHTML=heading(d.title,d.intro)+tabs(d.tabs,d.title)+`<section class="panel roadmap-section" id="work-list"></section><p class="detail-note">${e(d.lifecycle)}</p>${lifecycle()}`;
    const render=index=>{root.querySelector('#work-list').innerHTML=index===1?`<h2>${e(d.issueTitle)}</h2><p>${e(d.issueText)}</p><ol class="issue-timeline">${d.timeline.map(x=>`<li>${e(x)}</li>`).join('')}</ol>${pending([c.complete,c.archive,c.restore,c.remove])}`:records(index===0?c.todos:c.notices,index===0?[c.complete,c.archive,c.restore,c.remove]:[c.read,c.archive,c.restore,c.remove]);};
    const selectedTab=Math.max(0,Math.min(d.tabs.length-1,Math.trunc(Number(query.get('tab')))||0));
    bindTabs(root,index=>{render(index);navigateTab('/work',index,d.tabs[index],[{label:d.title,url:'/work'}],setBreadcrumb);});
    render(selectedTab);markTab(root,selectedTab);setBreadcrumb([{label:d.title,url:'/work'},{label:d.tabs[selectedTab]}]);
  } else if(path==='/skills') {
    const d=c.skills;
    root.innerHTML=heading(d.title,d.intro)+`<p class="detail-note">${e(d.availability)}</p>`+[d.mine,d.bundle].map((name,i)=>`<section class="panel roadmap-section"><h2>${e(name)}</h2>${d.rows.filter((_,index)=>i?index>0:index===0).map(([name,source,text])=>`<details class="skill-preview"><summary>${e(name)} <span class="subtle-tag">${e(source)}</span></summary><p>${e(d.example)}</p><pre>${e(text)}</pre><small>${e(d.metadata)}</small></details>`).join('')}</section>`).join('');
  } else if(path==='/recipes/data'||path==='/retention') {
    setBreadcrumb([{label:c.recipes.title,url:'/recipes'},{label:c.recipes.cross}]);
    root.innerHTML=heading(c.recipes.cross,c.recipes.dataNote)+`<section class="panel"><h2>${e(c.recipes.tabs[3])}</h2><p>${e(c.recipes.scope)}</p></section>`+transfer();
  } else if(path==='/recipes') {
    const d=c.recipes;
    root.innerHTML=heading(d.title,d.intro)+`<div class="roadmap-actions"><a class="button" href="/recipes/data">${e(d.cross)}</a>${pending([c.import,c.export])}</div><section id="recipe-browser"><div class="filter-bar"><label>${e(d.search)}<input type="search" id="recipe-query"></label></div><div id="recipe-list"></div></section><section id="recipe-detail" hidden></section>`+transfer();
    const render=()=>{
      const needle=root.querySelector('#recipe-query').value.trim().toLowerCase();
      root.querySelector('#recipe-list').innerHTML=[d.mine,d.bundle].map((title,group)=>`<section class="panel roadmap-section"><h2>${e(title)}</h2><div class="recipe-records">${d.rows.map((row,index)=>({row,index})).filter(({row,index})=>(group?index>=2:index<2)&&row.join(' ').toLowerCase().includes(needle)).map(({row,index})=>`<article><div><strong>${e(row[0])}</strong><p>${e(row[1])} · ${e(row[2])}</p></div><a class="button" href="${recipeUrl(index)}">${e(d.open)} →</a></article>`).join('')||`<p>${e(c.empty)}</p>`}</div></section>`).join('');

    };
    const openRecipe=index=>{
      root.querySelector('#recipe-browser').hidden=true;
      setBreadcrumb([{label:d.title,url:'/recipes'},{label:d.rows[index][0]}]);
      root.querySelector('.page-heading h1').textContent=d.rows[index][0];
      root.querySelector('.page-heading .intro').textContent=d.rows[index][1];
      root.querySelector('.roadmap-actions').hidden=true;
      const detail=root.querySelector('#recipe-detail');detail.hidden=false;
      detail.innerHTML=`<p>${e(d.rows[index][1])} · ${e(d.selected)}</p>${observationHistory(index,e)}${tabs(d.tabs,d.selected)}<section class="panel roadmap-section" id="recipe-tab-content"></section>`;
      const renderTab=tab=>{if(tab===2){detail.querySelector("#recipe-tab-content").innerHTML=`<h3>${e(c.history.title)}</h3><p>${e(c.history.note)}</p>`;return;}detail.querySelector('#recipe-tab-content').innerHTML=`<h3>${e(d.tabs[tab])}</h3><p>${e(tab===0?d.description:tab===1?c.logs.note:d.dataNote)}</p>`+(tab===0?pending([d.run]):tab===1?`<a class="button" href="/logs">${e(c.logs.title)} →</a>`:pending([c.export,c.import,c.archive,c.restore,c.remove]));};
      const selectedTab=Math.max(0,Math.min(d.tabs.length-1,Math.trunc(Number(query.get('tab')))||0));
      bindTabs(detail,tab=>{renderTab(tab);navigateTab(recipeUrl(index),tab,d.tabs[tab],[{label:d.title,url:'/recipes'},{label:d.rows[index][0],url:recipeUrl(index)}],setBreadcrumb);});
      renderTab(selectedTab);markTab(detail,selectedTab);
      setBreadcrumb([{label:d.title,url:'/recipes'},{label:d.rows[index][0],url:recipeUrl(index)},{label:d.tabs[selectedTab]}]);

    };
    root.querySelector('#recipe-query').addEventListener('input',render);render();
    const selected=query.get('recipe');
    if(selected!==null){const index=d.rows.findIndex(row=>row[0]===selected);if(index>=0)openRecipe(index);else root.querySelector('#recipe-detail').insertAdjacentHTML('afterend',`<p role="status">${e(c.notFound)}</p>`);}
  }
}
export const recipeUrl=index=>'/recipes?recipe='+encodeURIComponent(copy.recipes.rows[index][0]);
export const logUrl=index=>'/logs?entry='+encodeURIComponent(copy.logs.entries[index].id);
export function observationHistory(index,e) {
  const d=copy.history;
  return `<section class="panel roadmap-section observation-history"><h2>${e(d.title)}</h2><p>${e(d.note)}</p><p class="field-hint">${e(copy.timezone)}</p><div class="table-scroll"><table class="roadmap-table"><thead><tr>${d.columns.map(label=>`<th scope="col">${e(label)}</th>`).join('')}</tr></thead><tbody>${d.states.map((state,i)=>`<tr><td>${e(`2026-10-${31-i} 08:${String(10+index).padStart(2,'0')}:05`)}</td><td>${e(state)}</td><td>${i===2?'—':index+1}</td><td>${e(i===2?d.notSaved:d.saved)}</td></tr>`).join('')}</tbody></table></div></section>`;
}
function markTab(root,index){
  root.querySelectorAll('[data-tab]').forEach(button=>{button.classList.toggle('selected',Number(button.dataset.tab)===index);button.setAttribute('aria-pressed',String(Number(button.dataset.tab)===index));});
}
function navigateTab(url,index,label,ancestors,setBreadcrumb){
  const target=new URL(url,location.origin);target.searchParams.set('tab',String(index));
  history.replaceState(null,'',target.pathname+target.search);
  setBreadcrumb([...ancestors,{label}]);
}
function bindTabs(root,render) {
  root.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
    root.querySelectorAll('[data-tab]').forEach(item=>{item.classList.toggle('selected',item===button);item.setAttribute('aria-pressed',String(item===button));});
    render(Number(button.dataset.tab));
  }));
}
export function versionPreview(e) {
  const d=copy.versions;
  return `<section class="panel roadmap-section"><div class="panel-heading"><h2>${e(d.title)}</h2><span class="subtle-tag">${e(copy.pending)}</span></div><p>${e(d.intro)}</p><div class="version-grid">${['OpsFeast','SSHScript'].map(name=>`<div><strong>${name}</strong><p>${e(d.current)}：${e(d.unavailable)}</p></div>`).join('')}</div><div class="roadmap-actions"><button class="button" disabled>${e(d.check)} · ${e(copy.pending)}</button><button class="button" disabled>${e(d.upgrade)} · ${e(copy.pending)}</button></div><p class="field-hint">${e(d.note)}</p></section>`;
}
