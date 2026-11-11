import {states} from './locales/recipe-menu-zh-TW.mjs';
const url=(path,profile,extra={})=>path+'?'+new URLSearchParams({profile,...extra});
const time=value=>value?new Date(value).toLocaleString('zh-TW'):'—';
const label=value=>states[value]||value||'未回報';
const reasons={value_not_reported:'來源未提供數值',platform_unsupported:'平台不支援',not_supported:'不支援',not_attempted:'未採集',command_failed:'採集命令失敗',permission_denied:'權限不足',root_unavailable:'無法取得所需權限',worker_deadline:'執行逾時',stop_requested:'已停止',worker_output_limit:'結果超過大小限制',invalid_worker_output:'結果格式無法讀取',routine_meal_with_gaps:'部分採集未完成'};
const reason=value=>reasons[value]||value||'未提供原因';
const endedProblems=new Set(['partial','failed','unsupported','skipped','stopped','interrupted']);
export function taskIssues(task) {
 const issues=[];
 if(endedProblems.has(task.state))issues.push(label(task.state));
 if(task.result?.status&&endedProblems.has(task.result.status)&&task.result.status!==task.state)issues.push('採集：'+label(task.result.status));
 for(const [field,title] of [['retention','保存'],['content_update','後續呈現／通知']]){
  if(['failed','partial'].includes(task.result?.[field]?.status))issues.push(title+'：'+label(task.result[field].status));
 }
 if(Array.isArray(task.result?.collection_gaps)&&task.result.collection_gaps.length&&!issues.length)issues.push('採集欄位未齊全');
 if(issues.length&&(task.reason_code||task.result?.reason_code))issues.push(reason(task.reason_code||task.result.reason_code));
 return issues;
}
export function taskResultId(task) {
 if(task.kind==='report')return null;
 if(typeof task.result?.result_id==='string')return task.result.result_id;
 return typeof task.result?.result_path==='string'?task.result.result_path.split('/').slice(-2).join('/'):null;
}
export function sharedProgress(tasks) {
 const blocks=new Map();
 for(const task of tasks){
  if(!task.progress)continue;
  const key=JSON.stringify([task.host_id,task.progress]);
  if(!blocks.has(key))blocks.set(key,{host:task.host_id||'本機報告',references:[],text:task.progress});
  const block=blocks.get(key);if(!block.references.includes(task.reference))block.references.push(task.reference);
 }
 const text=[...blocks.values()].map(b=>`${b.host} · ${b.references.join('、')}\n${b.text}`).join('\n\n');
 return {text:text.slice(-131072),truncated:text.length>131072||tasks.some(t=>t.progress_truncated)};
}
function gaps(task,diagnosis,e) {
 const rows=diagnosis?.data?.coverage_gaps||task.result?.collection_gaps||[];
 const table=Array.isArray(rows)&&rows.length?`<table><thead><tr><th>未完成欄位</th><th>原因</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${e((row.properties||[]).join('、')||row.property||'未列出欄位')}</td><td>${e(reason(row.reason_code))}</td></tr>`).join('')}</tbody></table>`:'';
 const issues=(diagnosis?.data?.issues||[]).map(i=>`<li>${e(i.stage||'採集')}：${e(reason(i.reason_code))}${i.error_type?' · '+e(i.error_type):''}</li>`).join('');
 return `<section class="recipe-task-gaps"><h4>未完成欄位與原因</h4>${table}${issues?`<ul>${issues}</ul>`:''}${diagnosis?.loading?'<p role="status">正在讀取已保存的欄位明細…</p>':diagnosis?.error?'<p role="alert">無法讀取已保存的明細，請重新整理後再試。</p>':!table&&!issues?`<p>${diagnosis?.data?'原結果沒有記錄可辨識的未完成欄位；請參閱回執與原因。':taskResultId(task)?'展開此任務後讀取已保存的未完成明細。':'此任務沒有可讀取的已保存欄位明細。'}</p>`:''}${(diagnosis?.data?.notes||[]).map(note=>`<p class="field-hint">${e(note)}</p>`).join('')}${diagnosis?.data?.omitted_coverage_groups||diagnosis?.data?.omitted_count?'<p>明細超過顯示範圍，完整資料仍保留在原結果中。</p>':''}</section>`;
}
export function renderRun(run,e,{diagnoses={}}={}) {
 const tasks=run.tasks||[],problems=tasks.map((task,index)=>({task,index,issues:taskIssues(task)})).filter(row=>row.issues.length);
 const active=['running','stopping'].includes(run.state),progress=sharedProgress(tasks);
 const hostLink=task=>task.host_id?`<a target="_blank" rel="noopener" href="${e(url('/hosts',run.profile,{host:task.host_id}))}">${e(task.host_id)}</a>`:'本機報告';
 const running=tasks.filter(t=>t.state==='running').length,queued=tasks.filter(t=>t.state==='queued').length;
 return `<div class="page-heading"><div><h2>本次執行 · ${e(label(run.state))}</h2><p>${e(time(run.created_at))} · ${run.threads?`${e(run.threads)} threads · `:''}${tasks.length} 項工作</p></div>${active?'<button class="button danger-button" id="recipe-stop">停止本次選擇</button>':''}</div><p><a href="${e(url('/recipes',run.profile))}">← Recipes</a> · <a href="${e(url('/recipes',run.profile,{history:'1'}))}">執行紀錄</a></p><p class="field-hint">Web 服務持續運作時，關閉瀏覽器不會停止執行；可從 Recipes → 執行紀錄回到本頁。</p><section class="panel recipe-shared-river"><h3>共用執行進度 <small>${running} 項執行中 · ${queued} 項等待</small></h3><pre class="recipe-progress" id="recipe-shared-progress" tabindex="0">${e(progress.text||'尚無 runner 進度輸出。')}</pre><p class="field-hint">依主機與任務彙整${progress.truncated?'；僅顯示保留範圍內的最近輸出':''}。</p></section>${problems.length?`<section class="panel recipe-run-problems"><h3>未完成項目 · ${problems.length} 個任務</h3><ul>${problems.map(({task,index,issues})=>`<li><button class="text-button" type="button" data-open-task="${index}">${e(task.host_id||'本機報告')} · ${e(task.reference)}</button>：${e(issues.join('；'))}</li>`).join('')}</ul></section>`:run.state==='completed_with_gaps'?'<p role="status">執行回報含未完成項目，但任務回執未提供明確原因。</p>':''}<p class="field-hint">遠端清理：${e(run.remote_cleanup==='unknown'?'未知':run.remote_cleanup==='not_applicable'?'尚無強制中斷':run.remote_cleanup||'未回報')}。停止請求、本機終止與遠端清理分別記錄。${run.recovery?'服務重啟後沒有重試此工作。':''}</p>${tasks.map((task,index)=>{
  const issues=taskIssues(task),id=taskResultId(task),result=task.result;
  const state=task.state==='running'?'<span class="recipe-task-spinner" aria-label="執行中"></span> 執行中':task.state==='success'?'完成':task.state==='partial'?'完成 · 部分完成':task.state==='queued'?'等待':`已結束 · ${label(task.state)}`;
  return `<details class="panel recipe-task" data-task-index="${index}" id="recipe-task-${index}"><summary><span>${hostLink(task)} · ${e(task.reference)}</span><span class="recipe-task-status">${task.state==='running'?state:e(state)}</span></summary><p>${e(time(task.started_at))} → ${e(time(task.completed_at))}</p>${task.reason_code?`<p>${e(reason(task.reason_code))}</p>`:''}${task.local_termination?`<p>本機 worker 終止：${e(task.local_termination)}；遠端清理未知。</p>`:''}${issues.length?gaps(task,diagnoses[id],e):''}${result?`<p>操作結果：${e(label(result.status))} · 保存：${task.kind==='report'?'離線成果檔':e(label(result.retention?.status))} · 後續呈現／通知：${e(label(result.content_update?.status))}</p>${result.artifacts?.length?`<a class="button" target="_blank" rel="noopener" href="${e(url('/recipes',run.profile,{report:result.result_id||result.result_path.split('/').slice(-3).join('/')}))}">開啟報告成果 →</a>`:''}${result.children?.length?`<ul>${result.children.map(c=>`<li>${e(c.recipe?.reference||'未知 recipe')} · ${e(label(c.status))}</li>`).join('')}</ul>`:''}<details><summary>詳細回執與來源證據</summary><pre>${e(JSON.stringify(result,null,2))}</pre></details>`:''}</details>`;
 }).join('')}`;
}

export async function mountRecipeRun(root,{profile,id,e,api,setTimer=setTimeout}) {
 let run,diagnoses={};const key=Symbol('run');root.recipeRunView=key;
 const alive=()=>root.recipeRunView===key&&root.isConnected!==false;
 const render=()=>{
  const open=new Set([...root.querySelectorAll('details[data-task-index][open]')].map(node=>node.dataset.taskIndex));
  const previous=root.querySelector('#recipe-shared-progress'),scroll=previous?.scrollTop||0,atEnd=!previous||previous.scrollHeight-previous.clientHeight-scroll<32;
  root.innerHTML=renderRun(run,e,{diagnoses});
  const river=root.querySelector('#recipe-shared-progress');if(river)river.scrollTop=atEnd?river.scrollHeight:scroll;
  root.querySelector('#recipe-stop')?.addEventListener('click',async()=>{await api('/api/v1/recipe-runs/'+id+'/stop',{profile});await load();});
  root.querySelectorAll('details[data-task-index]').forEach(node=>{
   if(open.has(node.dataset.taskIndex))node.open=true;
   node.addEventListener('toggle',()=>{
    if(!node.open)return;const task=run.tasks[Number(node.dataset.taskIndex)],resultId=taskResultId(task);
    if(!taskIssues(task).length||!resultId||Object.hasOwn(diagnoses,resultId))return;
    diagnoses[resultId]={loading:true};render();
    api('/api/v1/results/diagnosis?'+new URLSearchParams({profile,result_id:resultId,limit:'50'})).then(data=>{diagnoses[resultId]={data};if(alive())render();}).catch(()=>{diagnoses[resultId]={error:true};if(alive())render();});
   });
  });
  root.querySelectorAll('[data-open-task]').forEach(button=>button.addEventListener('click',()=>{const node=root.querySelector('#recipe-task-'+button.dataset.openTask);node.open=true;node.scrollIntoView?.({block:'nearest'});}));
 };
 let timer=null;
 const load=async()=>{
  const current=await api('/api/v1/recipe-runs/'+id+'?'+new URLSearchParams({profile}));
  if(!alive())return;run=current;render();
  if(['running','stopping'].includes(run.state)&&timer===null)timer=setTimer(()=>{timer=null;if(alive())load().catch(error=>{root.querySelector('#recipe-shared-progress').textContent=error.message;});},1500);
 };
 await load();
}
export async function mountRecipeRunHistory(root,{profile,e,api}) {
 const data=await api('/api/v1/recipe-runs?'+new URLSearchParams({profile}));
 root.innerHTML=`<h2>執行紀錄</h2><p><a href="${e(url('/recipes',profile))}">← Recipes</a></p><p class="field-hint">關閉瀏覽器後可由此重新開啟執行中或已結束的餐盤；查看紀錄不會重新執行。</p>${data.items.length?`<ul class="recipe-run-history">${data.items.map(row=>`<li><a href="${e(url('/recipes',profile,{run:row.id}))}">${e(time(row.created_at))} · ${e(label(row.state))} →</a></li>`).join('')}</ul>`:'<p>尚無執行紀錄。</p>'}${data.total>data.items.length?'<p>目前顯示最近 100 筆執行紀錄。</p>':''}`;
}
