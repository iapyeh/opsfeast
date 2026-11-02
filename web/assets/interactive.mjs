import {consumeEvent,nextAction,canApprove} from './interactive-state.mjs';
const $=id=>document.getElementById(id),api='/api/v1/interactive';
let credential='',snapshot=null,streamController=null,busy=false;
const labels={draft:'草稿',awaiting_plan:'等待計畫確認',queued:'已核准，等待執行',connecting:'正在連線',ready:'等待新計畫',running:'執行中',paused:'到達確認點／已停止，等待回饋',awaiting_step:'等待下一步確認',failed_step:'步驟失敗，請檢視後提出新計畫',stop_requested:'停止已請求，尚未確認結束',closing:'正在關閉',closed:'已關閉',interrupted:'Server 重啟，工作已中斷；不自動續跑',failed:'失敗，清理情況待確認'};
function headers(){return credential?{Authorization:'Bearer '+credential}:{};}
async function request(path='',body){
  const response=await fetch(api+path,{method:body?'POST':'GET',headers:{...headers(),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
  const data=await response.json();if(!response.ok)throw Error(data.detail||String(response.status));return data;
}
function message(text){$('status').textContent=text;}
function run(callback){return async()=>{if(busy)return;busy=true;try{await callback();}catch(error){message('未完成：'+(error.message==='command_must_be_single_line'?'每個步驟只能有一行命令；請分成多個步驟。printf 的換行請使用字面上的反斜線 n，不要直接換行。':error.message));}finally{busy=false;render();}};}
async function load(){
  const info=await request();
  $('target').replaceChildren(...info.targets.map(target=>{const option=document.createElement('option');option.value=JSON.stringify(target);option.textContent=target.profile+' / '+target.host_id;return option;}));
  $('works').replaceChildren(...info.works.map(work=>{const option=document.createElement('option');option.value=work.work_id;option.textContent=work.created_at+' · '+work.host_id+' · '+(labels[work.status]||work.status)+' · '+work.goal;return option;}));
  $('target').disabled=false;$('create').disabled=info.role!=='operator';$('restore').disabled=false;
  $('access').open=false;message('已解鎖；執行前請核對完整計畫。');
}
async function restore(id){
  streamController?.abort();snapshot=await request('/'+id);
  history.replaceState(null,'','/interactive?work='+encodeURIComponent(id));$('chooser').open=false;render();listen(id);
}
async function listen(id){
  const controller=new AbortController();streamController=controller;
  try{
    const response=await fetch(`${api}/${id}/events?after=${snapshot.seq}`,{headers:headers(),signal:controller.signal});
    if(!response.ok)throw Error('stream_auth_or_server_error');
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let end;
      while((end=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,end);buffer=buffer.slice(end+2);const data=block.split('\n').find(line=>line.startsWith('data: '));if(data){snapshot=consumeEvent(snapshot,JSON.parse(data.slice(6)));render();}}
    }
    if(!controller.signal.aborted)throw Error('stream_disconnected');
  }catch(error){if(!controller.signal.aborted){message('串流中斷；正在從已保存狀態恢復。');setTimeout(async()=>{if(streamController!==controller||controller.signal.aborted)return;try{await restore(id);}catch(e){message('無法恢復：'+e.message+'；請重新解鎖。');}},1500);}}
}
function addText(parent,tag,text,className){const element=document.createElement(tag);element.textContent=text;if(className)element.className=className;parent.append(element);return element;}
function renderStep(parent,step){
  const article=document.createElement('article');article.className='interactive-step';
  addText(article,'h3',`Step ${step.index} · ${step.purpose}`);addText(article,'p',step.status+' · exitcode: '+(step.exitcode??'—'));
  addText(article,'pre',step.command,'log-content');addText(article,'pre',step.stdout||'（尚無 stdout）','log-content');if(step.stderr)addText(article,'pre',step.stderr,'log-content');
  if(step.error_type)addText(article,'p','錯誤類型：'+step.error_type+'；未取得 exitcode 時，不代表命令已成功或已確認終止。');
  if(step.output_truncated)addText(article,'p','輸出超過此工作 2 MiB 上限，部分內容未保存；已請求停止。');
  if(step.stop_requested)addText(article,'p','此步驟曾請求停止；命令結束不保證所有遠端子程序已終止。');parent.append(article);
}
function render(){
  if(!snapshot)return;
  const s=snapshot.state;$('work').hidden=false;
  $('next-action').textContent=nextAction(s);$('next-action').hidden=!$('next-action').textContent;
  $('identity').replaceChildren();
  for(const [key,value] of Object.entries({'工作 ID':s.work_id,'目標':s.profile+' / '+s.host_id,'目的':s.goal,'Namespace':s.target?.namespace||'—','設定登入帳號':s.target?.username||'—','設定目標':s.target?.hostname||'—','狀態':labels[s.status]||s.status,'最後事件序號':snapshot.seq,'實際身分':s.identity?JSON.stringify(s.identity):'尚未連線／未驗證','清理':s.cleanup,'錯誤類型':s.last_error?JSON.stringify(s.last_error):'—'})){
    addText($('identity'),'dt',key);addText($('identity'),'dd',String(value));
  }
  const waiting=canApprove(s);
  $('approve').disabled=busy||!waiting;$('reject').disabled=busy||!waiting;
  $('approve').hidden=!waiting;$('reject').hidden=!waiting;
  $('propose').disabled=busy||!['draft','awaiting_plan','ready','paused','failed_step'].includes(s.status);
  $('stop').disabled=busy||!['running','queued','connecting'].includes(s.status);
  $('close').disabled=busy||['closed','failed','interrupted','closing'].includes(s.status);
  $('send-feedback').disabled=busy;
  $('plan').replaceChildren();
  if(s.plan){
    addText($('plan'),'h3',s.plan.title);
    addText($('plan'),'p',s.plan.approval_mode==='each'?'確認方式：每個命令前確認':'確認方式：依整份明確計畫執行，到里程碑暫停');
    s.plan.steps.forEach((step,index)=>{const article=document.createElement('article');article.className='interactive-step';addText(article,'h3',`Step ${index+1} · ${step.purpose}`);addText(article,'pre',step.command,'log-content');addText(article,'p',`${step.timeout} 秒期限 · ${step.checkpoint?'完成後停下等待確認':'依計畫繼續'}`);$('plan').append(article);});
    const details=document.createElement('details');addText(details,'summary','計畫識別與技術資料');addText(details,'pre',JSON.stringify(s.plan,null,2),'log-content');$('plan').append(details);
  }else addText($('plan'),'p','尚未提出計畫；建立工作不會連線。');
  $('history').replaceChildren();for(const step of s.history)renderStep($('history'),step);
  $('current').replaceChildren();if(s.current)renderStep($('current'),s.current);
  $('feedback-list').replaceChildren();for(const item of s.feedback)addText($('feedback-list'),'p',item.at+' · '+item.actor+'：'+item.text);
  $('analyses').replaceChildren();
  for(const item of s.analyses){addText($('analyses'),'p',item.at+' · '+item.actor+' 分析（非即時狀態）');const c=item.content;if(c.kind==='text')addText($('analyses'),'p',c.text);else{
    const table=document.createElement('table'),head=document.createElement('tr');for(const column of c.columns)addText(head,'th',column);table.append(head);
    for(const row of c.rows){const tr=document.createElement('tr');for(const value of row)addText(tr,'td',String(value??''));table.append(tr);}$('analyses').append(table);
  }}
  $('agent-prompt').value=`請協助 OpsFeast 互動工作 ${s.work_id}。目標 ${s.profile}/${s.host_id}。目的：${s.goal}\n先閱讀 docs/interactive-console.md 與 skills/opsfeast-interactive/SKILL.md。API ${location.origin}${api}/${s.work_id}。\n使用 installation data 內 .opsfeast-interactive-agent-8740.token，只提交計畫、分析及讀取事件，不代替人類核准。不要輸出憑證。全部操作經本服務，不另開 SSH。`;
}
$('unlock').onclick=run(async()=>{credential=$('token').value;$('token').value='';await load();const id=new URLSearchParams(location.search).get('work');if(id)await restore(id);});
$('create').onclick=run(async()=>{const target=JSON.parse($('target').value);const created=await request('',{...target,goal:$('goal').value});await restore(created.state.work_id);});
$('restore').onclick=run(async()=>{if($('works').value)await restore($('works').value);});
async function action(name,body={}){const id=snapshot.state.work_id;await request(`/${id}/${name}`,{request_id:crypto.randomUUID(),...body});snapshot=await request('/'+id);}
$('propose').onclick=run(async()=>{const steps=$('steps').value.trim()?JSON.parse($('steps').value):[{command:$('command').value,purpose:$('purpose').value,checkpoint:true,timeout:30}];await action('plan',{title:$('purpose').value,steps,approval_mode:$('approval-mode').value});});
$('approve').onclick=run(async()=>{await action('approve',{plan_id:snapshot.state.plan.plan_id});});
$('reject').onclick=run(()=>action('reject'));
$('stop').onclick=run(()=>action('stop'));
$('close').onclick=run(()=>action('close'));
$('send-feedback').onclick=run(async()=>{await action('feedback',{text:$('feedback').value});$('feedback').value='';});
window.addEventListener('pagehide',()=>streamController?.abort());
message('請先解鎖。尚未連線；關閉本頁不會發送停止。');
// Browser users use their administrator session directly; capabilities remain API tools.
load().then(async()=>{$('access').hidden=true;const id=new URLSearchParams(location.search).get('work');if(id)await restore(id);}).catch(error=>{if(error.message==='interactive_credential_required')location.assign('/login?next='+encodeURIComponent(location.pathname+location.search));else message('無法載入：'+error.message);});
