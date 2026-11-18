import {workspaceUrl} from './workspace-url.mjs';
import {formatDateTime} from './i18n.mjs';
import {roles,blockerLabels,fieldLabels} from './locales/recipe-content-zh-TW.mjs';
const mounts=new WeakMap();
const time=value=>{try{return value?formatDateTime(value):'';}catch{return value||'';}};
const field=(definition,path)=>path.split('.').reduce((value,key)=>value&&typeof value==='object'?value[key]:undefined,definition);
const json=value=>typeof value==='string'?value:JSON.stringify(value,null,2);
export function renderContent(content,e,{section='all'}={}) {
 if(!content)return '';
 const definition=content.definition||{},components=content.components||[],resources=content.resources||{};
 const state=component=>({missing:'未提供',provided:'文字資源已提供',file_present:'檔案已提供',declared:'已宣告'}[component.state]||component.state);
 const componentBody=component=>{
  const role=roles[component.id]||roles.assets;
  const declared=(component.fields||[]).map(path=>[path,field(definition,path)]).filter(([,value])=>value!==undefined&&value!==''&&value!==null&&!(typeof value==='object'&&!Object.keys(value).length));
  return `<section class="recipe-component" id="recipe-component-${e(component.id)}"><h3>${e(role.title)}</h3><p class="field-hint">${e(role.description)}</p>
  ${declared.length?`<details data-content-section="${e(component.id)}-declaration"><summary>查看宣告</summary><dl>${declared.map(([path,value])=>`<dt>${e(fieldLabels[path]||path)}</dt><dd><pre>${e(json(value))}</pre></dd>`).join('')}</dl></details>`:''}
  ${component.files?.length?`<p class="field-hint">已存在的 ${e(role.title)} 檔案：</p><ul>${component.files.map(name=>`<li><code>${e(name)}</code></li>`).join('')}</ul>`:''}
  ${(component.resources||[]).map((resource,index)=>`<details data-recipe-resource="${e(resource.path)}" ${component.id==='plan'?'open':''}><summary>${e(resource.title||role.title+(component.resources.length>1?' '+(index+1):''))}</summary><p class="field-hint">來源：<code>${e(resource.path)}</code></p><pre class="document-source">${e(resources[resource.path]||'')}</pre></details>`).join('')}</section>`;
 };
 const purpose=`<header class="page-heading recipe-purpose"><div><h1>${e(content.title||content.reference)}</h1><p class="intro">${e(content.description||'')}</p></div></header>`;
 const metadata=`<section class="panel recipe-definition-meta" aria-labelledby="recipe-definition-heading"><h2 id="recipe-definition-heading">定義資訊</h2><dl>
 <dt>路徑（Reference）</dt><dd><code>${e(content.reference)}</code></dd><dt>Recipe ID</dt><dd>${e(definition.id||'')}</dd>
 <dt>版本</dt><dd>${e(content.version||'')}</dd><dt>狀態</dt><dd><strong>${content.runnable?'可執行':'不可執行'}</strong></dd>
 <dt>最近修改</dt><dd>${e(time(content.updated_at))}</dd><dt>修改次數</dt><dd>${content.change_number?e(content.change_number):''}</dd></dl>
 ${content.summary?`<details data-content-section="change-summary"><summary>最近修改說明</summary><p>${e(content.summary)}</p></details>`:''}
 <p role="status" data-content-status>每 3 秒檢查內容更新。</p></section>`;
 const agent=content.launch?.mode==='agent';
 const readiness=`<section class="panel recipe-readiness"><h2>${agent?'透過 Agent 執行':'執行條件'}</h2>
 ${content.runnable?(agent?'<p>這道 Recipe 需要 agent 協助。請將以下建議 prompt 貼到對話，讓 agent 安排瀏覽器等必要工具後開始。</p>':'<p>目前可加入執行餐盤。</p>'):`<p>目前不可執行，還需要完成：</p><ul>${(content.execution_blockers||[]).map(blocker=>`<li>${e(blockerLabels[blocker.code]||'尚有執行條件未完成')}</li>`).join('')}</ul>`}
 ${agent?`<div class="recipe-agent-prompt"><div class="recipe-agent-prompt-heading"><label for="recipe-agent-prompt">建議 prompt</label><button type="button" class="button" data-copy-agent-prompt>複製建議 prompt</button></div><textarea id="recipe-agent-prompt" data-agent-prompt readonly rows="9">${e(content.launch.prompt||'')}</textarea><p role="status" data-agent-prompt-status></p></div><p class="field-hint">複製不會啟動執行或通知 agent；請在對話中確認本次標的、參數及副作用。</p>`:`<p class="field-hint">加入餐盤後，再確認本次主機、參數與執行授權。</p>${content.runnable?`<a class="button" href="${e(workspaceUrl('/recipe-plate',content.profile,{add:content.reference}))}">加入執行餐盤</a>`:''}`}</section>`;
 const protocol=`<section class="panel"><details data-content-section="execution-protocol"><summary>執行契約與檢查細節</summary><pre class="document-source">${e(json({runner:content.runner||{},requirements:content.execution_blockers||[]}))}</pre></details></section>`;
 const composition=`<section class="panel recipe-composition"><h2>Recipe 構成</h2><p class="field-hint">「執行必要」項目影響目前執行契約；其他項目依需求選用。文字資源已提供，不等於實作或驗證已完成。</p>
 <div class="table-scroll"><table class="roadmap-table"><thead><tr><th scope="col">構成</th><th scope="col">提供情況</th><th scope="col">用途</th></tr></thead><tbody>${components.map(component=>{const role=roles[component.id]||roles.assets;return `<tr><th scope="row">${component.state==='missing'?e(role.title):`<a href="#recipe-component-${e(component.id)}">${e(role.title)}</a>`}<small class="recipe-component-requirement">${component.required_for_execution?'執行必要':'選用'}</small></th><td>${e(state(component))}</td><td>${e(role.description)}</td></tr>`;}).join('')}</tbody></table></div>
 ${components.filter(component=>component.state!=='missing').map(componentBody).join('')}</section>`;
 const parts={purpose,readiness,technical:metadata+protocol+composition};
 return section==='all'?purpose+readiness+parts.technical:parts[section]||'';
}

export function mountContent(root,initial,{profile,reference,e,api,targets={all:root}}) {
 let current=initial;const token={};mounts.set(root,token);
 root.addEventListener?.('click',async event=>{
  if(mounts.get(root)!==token||!event.target.closest?.('[data-copy-agent-prompt]'))return;
  const prompt=root.querySelector('[data-agent-prompt]'),status=root.querySelector('[data-agent-prompt-status]');
  try{await navigator.clipboard.writeText(prompt.value);status.textContent='已複製；請貼到 agent 對話。';}
  catch{prompt.focus();prompt.select();status.textContent='無法自動複製，請複製已選取的文字。';}
 });
 const active=()=>root.isConnected&&mounts.get(root)===token&&root.querySelector('[data-content-status]');
 const poll=async()=>{
  if(!active())return;
  try{
   const next=await api('/api/v1/recipe-content?'+new URLSearchParams({profile,reference}));
   if(!active())return;
   if(next.view_revision!==current.view_revision){
    const open=new Set([...root.querySelectorAll('[data-recipe-resource][open]')].map(el=>el.dataset.recipeResource));
    const sections=new Set([...root.querySelectorAll('[data-content-section][open]')].map(el=>el.dataset.contentSection));
    const scroll=window.scrollY;
    for(const [section,target] of Object.entries(targets))target.innerHTML=renderContent(next,e,{section});
    root.querySelectorAll('[data-recipe-resource]').forEach(el=>{el.open=open.has(el.dataset.recipeResource);});
    root.querySelectorAll('[data-content-section]').forEach(el=>{el.open=sections.has(el.dataset.contentSection);});
    window.scrollTo(window.scrollX,scroll);current=next;
    root.querySelector('[data-content-status]').textContent='內容已同步；若要修改共用選項，請重新整理以載入最新設定。';
   }
  }catch(error){const status=root.querySelector('[data-content-status]');if(status)status.textContent='更新暫停：'+error.message+'；保留上次內容，稍後重試。';}
  if(active())setTimeout(poll,3000);
 };
 setTimeout(poll,3000);
}
