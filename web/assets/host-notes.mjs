// Plain-text host notes: no Markdown/HTML execution or remote operations.
export function formatNoteTimestamp(value) {
  const date=new Date(value);
  if(!Number.isFinite(date.getTime()))return value;
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(date).map(p=>[p.type,p.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}+08:00`;
}
export function noteMatches(note,{query='',recipe='',tags=[],includeGeneral=false}={}) {
  const canonical=value=>value.startsWith('bundle:')?value.slice(7):value;
  const refs=note.recipe_references||[],labels=note.tags||[];
  return (!query||(note.title+'\n'+note.content+'\n'+refs.join('\n')+'\n'+labels.join('\n')).toLocaleLowerCase().includes(query.toLocaleLowerCase())) &&
    (!recipe||refs.includes(canonical(recipe))||(includeGeneral&&!refs.length)) &&
    tags.every(tag=>labels.includes(tag.toLocaleLowerCase()));
}
export function noteMarkup(note,e) {
  return `<article class="panel roadmap-section"><h3>${e(note.title)}</h3><p class="field-hint">來源：${e(note.source)} · ${e(formatNoteTimestamp(note.timestamp))}</p><p class="field-hint">Recipes：${(note.recipe_references||[]).map(e).join('、')||'未指定（一般主機經驗）'}</p><p class="field-hint">Tags：${(note.tags||[]).map(e).join('、')||'無'}</p><div class="host-note-content" style="white-space:pre-wrap;overflow-wrap:anywhere">${e(note.content)}</div><details><summary>紀錄識別</summary><code>${e(note.uuid)}</code></details><div class="setup-actions"><button type="button" class="button" data-note-edit="${e(note.uuid)}">編輯</button><button type="button" class="button danger" data-note-delete="${e(note.uuid)}">刪除</button></div></article>`;
}
export async function mountHostNotes(root,{profile,host_id,e,request}) {
  let snapshot,busy=false;
  const endpoint='/api/v1/host-notes';
  const scope={profile,host_id};
  const errorText=error=>error.code==='note_revision_conflict'?'筆記已被其他人更新。請保留草稿，重新載入並核對後再修改。':'操作未完成或結果尚未確認。請保留草稿，重新載入核對；不要直接重送。';
  async function load(){
    root.innerHTML='<p role="status">正在讀取主機筆記…</p>';
    try{snapshot=await request(endpoint+'?'+new URLSearchParams(scope));render();}
    catch{root.innerHTML='<p role="status">無法讀取主機筆記。</p><button class="button" id="notes-retry">重新載入</button>';root.querySelector('#notes-retry').onclick=load;}
  }
  function render(){
    root.innerHTML=`<section class="panel managed-host-form"><div class="panel-heading"><h2>主機筆記</h2><button class="button primary" id="note-add">新增筆記</button></div><p>累積這台主機的經驗與注意事項。每次儲存取代原內容，不保留編輯歷程；刪除無法復原。</p><label>搜尋筆記<input type="search" id="note-search"></label><label>Recipe reference（完整比對）<input id="note-recipe-filter" placeholder="system/inventory/overview"></label><label>Tags（全部符合，以逗號分隔）<input id="note-tags-filter"></label><label><input type="checkbox" id="note-general-filter" checked> 同時顯示未關聯 Recipe 的一般主機經驗</label></section><div id="note-editor"></div><div id="notes-list"></div><dialog id="note-delete-dialog" class="host-confirm-dialog"><form id="note-delete-form"><h2>刪除主機筆記</h2><p id="note-delete-title"></p><p>刪除後無法復原。</p><p role="status" id="note-delete-status"></p><div class="setup-actions"><button class="button danger" type="submit">確定刪除</button><button class="button" type="button" id="note-delete-cancel">取消</button></div></form></dialog>`;
    const list=root.querySelector('#notes-list');
    function show(){
      const needle=root.querySelector('#note-search').value.trim().toLocaleLowerCase();
      const notes=snapshot.notes.filter(n=>noteMatches(n,{query:needle,recipe:root.querySelector('#note-recipe-filter').value.trim(),tags:root.querySelector('#note-tags-filter').value.split(',').map(x=>x.trim()).filter(Boolean),includeGeneral:root.querySelector('#note-general-filter').checked}));
      list.innerHTML=notes.length?notes.map(n=>noteMarkup(n,e)).join(''):'<p>目前沒有符合條件的筆記。</p>';
      list.querySelectorAll('[data-note-edit]').forEach(button=>button.onclick=()=>edit(snapshot.notes.find(n=>n.uuid===button.dataset.noteEdit)));
      list.querySelectorAll('[data-note-delete]').forEach(button=>button.onclick=()=>remove(snapshot.notes.find(n=>n.uuid===button.dataset.noteDelete)));
    }
    for(const id of ['#note-search','#note-recipe-filter','#note-tags-filter'])root.querySelector(id).oninput=show;root.querySelector('#note-general-filter').onchange=show;show();root.querySelector('#note-add').onclick=()=>edit(null);
  }
  function edit(note){
    if(busy)return;
    const target=root.querySelector('#note-editor');
    target.innerHTML=`<form class="panel roadmap-section managed-host-form" id="note-form"><h3>${note?'編輯':'新增'}筆記</h3><label>標題<input name="title" required maxlength="200" value="${e(note?.title||'')}"></label><label>內容<textarea name="content" required maxlength="32000" rows="9">${e(note?.content||'')}</textarea></label><label>Recipe references（每行一個，最多 32 個）<textarea name="recipe_references" rows="3" placeholder="system/inventory/overview">${e((note?.recipe_references||[]).join('\n'))}</textarea></label><label>Tags（以逗號分隔，最多 32 個）<input name="tags" value="${e((note?.tags||[]).join(', '))}"></label><p>留白表示一般主機經驗；清空可移除關聯或標籤。關聯不會執行 Recipe，也不代表額外授權。</p><p>儲存後來源為 user，並更新最後修改時間。</p><p id="note-status" role="status"></p><div class="setup-actions"><button class="button primary" type="submit">儲存筆記</button><button class="button" id="note-cancel" type="button">取消</button></div></form>`;
    const form=target.querySelector('form');form.elements.recipe_references.value=(note?.recipe_references||[]).join('\n');form.elements.tags.value=(note?.tags||[]).join(', ');form.elements.title.focus();
    target.querySelector('#note-cancel').onclick=()=>{if(!busy)target.innerHTML='';};
    form.onsubmit=async event=>{
      event.preventDefault();if(busy)return;busy=true;
      const controls=target.querySelectorAll('button');controls.forEach(b=>b.disabled=true);
      target.querySelector('#note-status').textContent='正在儲存…';
      try{
        await request(endpoint,{method:note?'PATCH':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...scope,expected_revision:snapshot.revision,...(note?{note_uuid:note.uuid}:{}),changes:{title:form.elements.title.value,content:form.elements.content.value,source:'user',recipe_references:form.elements.recipe_references.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean),tags:form.elements.tags.value.split(',').map(x=>x.trim()).filter(Boolean)}})});
        busy=false;await load();
      }catch(error){target.querySelector('#note-status').textContent=errorText(error);busy=false;controls.forEach(b=>b.disabled=false);}
    };
  }
  function remove(note){
    if(busy)return;
    const dialog=root.querySelector('#note-delete-dialog'),form=dialog.querySelector('form');
    root.querySelector('#note-delete-title').textContent=note.title;root.querySelector('#note-delete-status').textContent='';
    root.querySelector('#note-delete-cancel').onclick=()=>{if(!busy)dialog.close();};
    dialog.oncancel=event=>{if(busy)event.preventDefault();};dialog.showModal();
    form.onsubmit=async event=>{
      event.preventDefault();if(busy)return;busy=true;form.querySelectorAll('button').forEach(b=>b.disabled=true);
      try{await request(endpoint,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({...scope,note_uuid:note.uuid,expected_revision:snapshot.revision,confirmation:note.uuid})});dialog.close();busy=false;await load();}
      catch(error){root.querySelector('#note-delete-status').textContent=errorText(error);busy=false;form.querySelectorAll('button').forEach(b=>b.disabled=false);}
    };
  }
  await load();
}
