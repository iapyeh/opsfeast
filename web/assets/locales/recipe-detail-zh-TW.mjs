import {formatDateTime} from '../i18n.mjs';
const json=value=>JSON.stringify(value,null,2);
const time=value=>{try{return value?formatDateTime(value):'未知';}catch{return '未知';}};
export const copy={loading:'正在讀取 Recipe 專頁…',profileRequired:'請先選擇 Profile，再開啟 Recipe 專頁。',saved:'已儲存；不會啟動採集或改變目前執行中的工作。',error:'無法完成操作；請檢查設定，若版本衝突請重新載入。',recordLoading:'正在讀取完整保存資料…'};
export function declaredFields(declarations) {
 const retention=declarations.retention||{};
 if(retention.fields)return Object.entries(retention.fields).map(([id,spec])=>({id,...spec}));
 const fields=[];
 const walk=(schema,prefix='',depth=0)=>{
  if(!schema||depth>12||fields.length>=500)return;
  for(const [key,spec] of Object.entries(schema.properties||{})){
   const id=prefix?prefix+'.'+key:key;fields.push({id,type:spec.type||'',description:spec.description||''});
   walk(spec,id,depth+1);if(spec.items)walk(spec.items,id+'[]',depth+1);
  }
 };
 walk(retention.data_schema);return fields;
}
export function declarationFields(declarations) {
 return declarations.inventory?Object.entries(declarations.inventory.properties).map(([id,p])=>({id,...p})):declaredFields(declarations);
}
export function fieldTree(fields) {
 const roots=new Map();
 for(const field of fields){
  let siblings=roots,prefix='';
  for(const part of field.id.split('.')){
   prefix=prefix?prefix+'.'+part:part;
   const key=part.replace(/\[\]$/,'');
   if(!siblings.has(key))siblings.set(key,{name:key,id:prefix,field:null,children:new Map()});
   const node=siblings.get(key);if(prefix===field.id){node.field=field;node.id=field.id;}siblings=node.children;
  }
 }
 return [...roots.values()];
}
export function renderOption(v,e) {
 return `<fieldset class="recipe-default-row" data-option="${e(v.name)}"><legend>${e(v.name)} · ${e(v.definition.type)}</legend><p>Recipe／來源預設：<code>${e(v.base_present?json(v.base_value):'未設定')}</code></p><label><input type="checkbox" data-override ${v.configured?'checked':''} ${v.editable?'':'disabled'}> 使用此 Profile 的覆寫值</label>${v.editable?`<textarea aria-label="${e(v.name)} 的 Profile 預設值" data-option-value rows="${['object','array'].includes(v.definition.type)?4:1}" ${v.configured?'':'disabled'}>${e(v.value_present?(v.definition.type==='string'?v.value:json(v.value)):'')}</textarea>`:`<p class="field-hint">此值包含敏感設定或 Recipe 尚未通過靜態驗證，這個頁面不提供編輯。</p>`}</fieldset>`;
}
export function renderDeclarations(declarations,e,variables=[]) {
 const fields=declarationFields(declarations),options=new Map(variables.map(v=>[v.name,v]));
 const metadata=field=>field?`<p class="recipe-field-description">${e(field.description||field.type||'')}${field.unit?' · '+e(field.unit):''}</p>`:'';
 const nodeHtml=node=>{
  const option=options.has(node.id)?renderOption(options.get(node.id),e):'';
  if(!node.children.size)return `<li class="recipe-field-leaf" data-field="${e(node.id)}"><strong>${e(node.name)}</strong><small>${e(node.id)}</small>${metadata(node.field)}${option}</li>`;
  return `<li data-field="${e(node.id)}"><details class="recipe-field-branch"><summary><strong>${e(node.name)}</strong></summary>${metadata(node.field)}${option}<ul>${[...node.children.values()].map(nodeHtml).join('')}</ul></details></li>`;
 };
 return `${fields.length?`<ul class="recipe-field-tree">${fieldTree(fields).map(nodeHtml).join('')}</ul>`:'<p>這道 Recipe 尚未宣告可列出的資料欄位，請參考完整契約。</p>'}<details class="recipe-declaration-data"><summary>完整的資料與保存契約</summary><pre>${e(json(declarations.inventory||declarations.retention||declarations.output))}</pre></details>`;
}
export function renderDetail(data,categories,e) {
 const item=data.recipe,settings=data.defaults;
 const fieldIds=new Set(declarationFields(data.declarations).map(f=>f.id));
 const common=settings.variables.filter(v=>!fieldIds.has(v.name));
 return `<a href="/recipes?${e(new URLSearchParams({profile:data.profile}))}">← 回到菜單與餐盤</a><div class="page-heading"><div><h1>${e(item.title)}</h1><p>${e(item.reference)} · ${e(item.version)}</p></div></div><p id="recipe-detail-notice" role="status"></p><p>${e(item.purpose)}</p><p class="detail-note">${e(item.limitation)}</p><form id="recipe-default-form"><section class="panel menu-stage"><h2>這道 Recipe 蒐集什麼？</h2><p class="field-hint">展開類別查看欄位；有對應輸入選項的項目可直接在該處設定。</p>${renderDeclarations(data.declarations,e,settings.variables)}<p class="field-hint">宣告內容不代表每台主機都取得完整資料；下方顯示實際保存結果與原始時間。</p></section><section class="panel menu-stage"><h2>共用選項與儲存</h2><p>欄位專屬選項放在上方對應項目內；以下是其餘共用選項。這裡修改所選 Profile 的預設輸入值，不修改 Bundle 原始檔。群組、主機與單次執行覆寫仍優先；儲存不代表執行。</p>${common.map(v=>renderOption(v,e)).join('')||'<p>沒有額外的共用選項。</p>'}<p id="recipe-default-status" role="status"></p>${settings.variables.some(v=>v.editable)?'<button class="button" type="submit">儲存預設選項</button>':''}</section></form><section class="panel menu-stage"><h2>分類</h2>${item.source==='repository'?'<p>Bundle 類別固定。你自己的 recipes 可使用相同類別或自訂類別。</p>':`<form id="recipe-category-form"><div class="menu-editor-checks">${categories.map(c=>`<label><input type="checkbox" name="categories" value="${e(c.id)}" ${(item.category_ids||data.automatic_categories||[]).includes(c.id)?'checked':''}> ${e(c.title)}</label>`).join('')}</div><p>可選多個類別；全部取消表示放入「其他／未分類」。</p><p id="recipe-category-status" role="status"></p><div class="recipe-actions"><button type="submit" class="button">儲存分類</button><button type="button" class="button" id="recipe-category-reset">恢復自動分類</button></div></form>`}<p><a href="/recipes?${e(new URLSearchParams({profile:data.profile}))}">前往 Recipes 管理自訂分類</a></p></section><section class="panel menu-stage"><h2>近期採集／執行狀態</h2><p>最新嘗試與保存資料分開呈現；較早成功的資料不代表最近一次採集成功。</p>${data.attempts?.status!=='success'?'<p role="status">部分執行紀錄無法讀取。</p>':''}${(data.attempts?.items||[]).map(r=>`<article><p><a href="/logs?${e(new URLSearchParams({profile:data.profile,result:r.result_id}))}">${e(time(r.started_at))} · ${e(r.host_id)} · ${e(r.status)}</a></p><p>原因：${e(r.reason_code||'未知')} · 保存：${e(r.retention?.status||'未回報')} · 呈現：${e(r.content_update?.status||'未回報')}</p></article>`).join('')||'<p>尚無這道 Recipe 的執行紀錄。</p>'}</section><section class="panel menu-stage"><h2>實際保存的資料</h2><p class="field-hint">這是 retention 的歷史資料；開啟本頁不會連線或重新採集。不同主機、版本與來源時間分開呈現。</p><label>主機 <select id="recipe-record-host"><option value="">全部</option>${data.saved.hosts.map(h=>`<option value="${e(h)}" ${data.selected_host===h?'selected':''}>${e(h)}</option>`).join('')}</select></label><div id="recipe-records">${renderRecords(data.saved,e,data.profile,item.reference)}</div></section>${data.reports.items.length?`<section class="panel menu-stage"><h2>已產生的報告成果</h2>${data.reports.items.map(r=>`<p><a href="/recipes?${e(new URLSearchParams({profile:data.profile,report:r.result_id}))}">${e(time(r.started_at))} · ${e(r.status)}</a></p>`).join('')}</section>`:''}`;
}
export function renderRecords(saved,e,profile,reference) {
 if(saved.status!=='success')return `<p role="status">保存資料目前無法讀取（${e(saved.reason_code)}）；不代表沒有採集紀錄。</p>`;
 return (saved.items.length?saved.items.map(row=>`<article class="recipe-saved-record"><h3>${e(row.host_id)} · ${e(row.status)}</h3><p>原始採樣時間：${e(time(row.observed_at))} · Namespace：${e(row.namespace)}${row.recipe_version?' · 版本 '+e(row.recipe_version):''}</p><small>${e(row.record_id)}</small><pre>${e(row.data_preview)}</pre>${row.data_truncated?'<p>目前為截短預覽，可展開完整資料或下載保存紀錄。</p>':''}<details data-record="${e(row.record_id)}"><summary>展開完整保存資料</summary><pre></pre></details><a href="/api/v1/recipe-detail/record?${e(new URLSearchParams({profile,reference,record_id:row.record_id,download:'true'}))}" download>下載保存紀錄 JSON</a></article>`).join(''):'<p>尚無這道 Recipe 的保存資料。</p>')+(saved.next_offset!=null?`<button type="button" class="button" data-records-more="${e(saved.next_offset)}">載入更多資料</button>`:'');
}
