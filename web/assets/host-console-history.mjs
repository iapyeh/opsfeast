// Read saved Console records; this surface never connects or executes commands.
import {formatNoteTimestamp as formatTimestamp} from './host-notes.mjs';
import {readerLink} from './console-navigation.mjs';

export function consoleHistoryMarkup(session,e,scope=null) {
  const states=session.block_states||{};
  const labels=[];
  if(states.streaming)labels.push(`未結束區塊 ${states.streaming}`);
  if(states.waiting)labels.push(`待回覆表單 ${states.waiting}`);
  if(states.failed)labels.push(`失敗區塊 ${states.failed}`);
  if(states.interrupted)labels.push(`中斷區塊 ${states.interrupted}`);
  if(states.cancelled)labels.push(`已取消區塊 ${states.cancelled}`);
  if(!labels.length)labels.push(session.block_count?'內容已記錄':'尚無內容');
  // Derive the URL from the opaque ID, never from writer-supplied link text.
  const url=readerLink(session.session_id,{history:true,scope});
  return `<tr><td><a class="record-time" href="${e(url)}" target="_blank" rel="noopener">${e(session.title)}</a></td><td>${e(formatTimestamp(session.created_at))}</td><td>${e(formatTimestamp(session.updated_at))}</td><td>${e(session.block_count)}</td><td>${e(labels.join('；'))}</td><td><a class="button" href="${e(url)}" target="_blank" rel="noopener">檢視紀錄</a></td></tr>`;
}

export async function mountHostConsoleHistory(root,{profile,host_id,e,request}) {
  let sessions=[],cursor=null,busy=false,failed=false;
  function render(){
    root.innerHTML=`<section class="panel roadmap-section"><div class="panel-heading"><h2>Console 紀錄</h2><button class="button" id="console-refresh" type="button" ${busy?'disabled':''}>重新整理</button></div><p>查看這台主機已保存的指令、輸出與分析，包含人類逐步指示與 agent 主導的作業。紀錄會另開唯讀頁籤，不會取代正在操作的河道，也不會連線主機或重新執行指令。</p><p class="field-hint">區塊狀態描述已保存的紀錄，不代表目前仍有連線，亦不代表遠端工作已成功或結束。時間顯示為 Asia/Taipei（+08:00）。</p><p role="status">${busy?'正在讀取 Console 紀錄…':failed?'無法讀取 Console 紀錄，請重新整理後再試。':!sessions.length?'目前沒有這台主機的 Console 紀錄。':''}</p>${sessions.length?`<div class="table-scroll"><table class="roadmap-table"><thead><tr><th>標題</th><th>建立時間</th><th>最後紀錄時間</th><th>區塊數</th><th>紀錄狀態</th><th>內容</th></tr></thead><tbody>${sessions.map(s=>consoleHistoryMarkup(s,e,{profile,host_id})).join('')}</tbody></table></div>`:''}${cursor?`<button class="button" type="button" id="console-more" ${busy?'disabled':''}>載入較早紀錄</button>`:''}</section>`;
    root.querySelector('#console-refresh').onclick=()=>load(true);
    if(cursor)root.querySelector('#console-more').onclick=()=>load(false);
  }
  async function load(reset){
    if(busy)return;
    busy=true;failed=false;render();
    const query=new URLSearchParams({profile,host_id,limit:'25'});
    if(!reset&&cursor)query.set('before',cursor);
    try{
      const page=await request('/api/v1/console-sessions?'+query);
      sessions=reset?page.sessions:[...sessions,...page.sessions];
      cursor=page.next_cursor;
    }catch{failed=true;}
    finally{busy=false;render();}
  }
  await load(true);
}
