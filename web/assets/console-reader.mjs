import {formatDateTime,formatTime} from './i18n.mjs';
import {hostList,hostPresentation,focusedIdentity,mountHostTabs} from './console-host-focus.mjs';
import {consume,displayText,preview,blockDisplayText,readBlockText,visibleInRiver,identityLabel,activityState} from './console-reader-state.mjs';
import {readerLocation,readerLink,readerScope,contentWindow} from './console-navigation.mjs';
import {mountSecretInput} from './console-secret-input.mjs';
const $=id=>document.getElementById(id),{sid,bid,history}=readerLocation(location.pathname),api='/api/v1/console-sessions/'+encodeURIComponent(sid);
const labels={command:'輸入',stdout:'輸出',stderr:'錯誤輸出',identity:'身分回報',analysis:'分析',authorization:'授權回報',error:'錯誤',status:'狀態回報',form:'等待你的回覆'};
const statuses={streaming:'接收中',completed:'完成',failed:'失敗',interrupted:'中斷',cancelled:'已取消',waiting:'等待回覆',answered:'已回覆'};
let snapshot=null,controller=null,follow=!bid,closedHosts=new Set(),readerAnnounced=false;
const cards=new Map(),drafts=new Map(),blockClosed=new Map();
const tabsRoot=document.createElement('nav');tabsRoot.id='host-tabs';$('toolbar').append(tabsRoot);
const hostTabs=mountHostTabs(tabsRoot,target=>{
  if(target===null){closedHosts.clear();blockClosed.clear();}else{const closing=tabStates().get(target);if(closing)closedHosts.add(target);else closedHosts.delete(target);for(const b of snapshot.blocks)if(b.target_id===target)blockClosed.delete(b.id);}const top=$('transcript').scrollTop;
  for(const block of snapshot.blocks)update(block);
  meta();$('transcript').scrollTop=top;
});
function isClosed(block){
  const waiting=!history&&block.kind==='form'&&block.status==='waiting'&&!block.response&&!block.expired;
  return !bid&&!waiting&&(blockClosed.get(block.id)??closedHosts.has(block.target_id));
}
function tabStates(){
  const blocks=snapshot.blocks.filter(visibleInRiver),states=new Map();
  for(const host of hostList(snapshot.session)){
    const own=blocks.filter(block=>block.target_id===host.id);
    states.set(host.id,own.length?own.every(block=>!isClosed(block)):!closedHosts.has(host.id));
  }
  states.set(null,blocks.every(block=>!isClosed(block))&&[...states.values()].every(Boolean));
  return states;
}
function sourceView(card,block){
  const p=hostPresentation(snapshot.session,block,closedHosts);
  const waiting=!history&&block.kind==='form'&&block.status==='waiting'&&!block.response&&!block.expired;
  const closed=isClosed(block);
  card.source.hidden=!!bid&&!hostList(snapshot.session).length;
  card.sourceLabel.textContent=p.host?p.label:(hostList(snapshot.session).length?p.label:snapshot.session.host_id);
  card.sourceSuffix.textContent=displayText(block.head??'').split(/\r?\n/).find(line=>line.trim())??block.title;
  card.sourceSuffix.hidden=!closed;card.sourceTime.hidden=false;
  card.sourceTime.textContent=formatTime(block.created_at);
  card.el.classList.toggle('block-closed',closed);
  card.source.setAttribute('aria-expanded',String(!closed));
  card.source.setAttribute('aria-label',closed?'展開區塊':'閉合區塊');
  if(p.tone!==null)card.el.dataset.hostTone=String(p.tone);else delete card.el.dataset.hostTone;
  card.link.hidden=!!bid||closed;card.blockToggle.hidden=!!bid;card.blockToggle.disabled=waiting;card.blockToggle.textContent=closed?'↓':'↑';card.blockToggle.title=closed?'展開此區塊':'閉合此區塊';card.blockToggle.setAttribute('aria-label',card.blockToggle.title);card.blockToggle.setAttribute('aria-expanded',String(!closed));
  card.link.setAttribute('aria-label',p.host?`${p.host.host_id}：另開完整內容`:'另開完整內容');
  card.toggle=()=>{if(bid||waiting)return;blockClosed.set(block.id,!closed);sourceView(card,block);hostTabs.render(snapshot.session,closedHosts,tabStates());};
}

function add(parent,tag,text,cls){const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;parent.append(el);return el;}
async function request(path='',body){const response=await fetch(api+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},...(body?{body:JSON.stringify(body)}:{})});if(response.status===401){location.assign('/login?next='+encodeURIComponent(location.pathname+location.search));throw Error('請先登入');}const data=await response.json();if(!response.ok)throw Error(data.detail||'讀取失敗');return data;}
function navigation(){
  const session=snapshot.session,scope=readerScope(session,location.search),crumb=$('breadcrumb');
  const mode=history?'Console 紀錄（唯讀）':'互動河道';
  document.title=`${mode} · ${session.host_id} · ${session.title} · ${sid.slice(0,8)}`;
  crumb.replaceChildren();add(crumb,'a','工作空間').href='/workspace';add(crumb,'span',' / ');
  const hosts=add(crumb,'a','主機');hosts.href='/hosts';
  if(scope){hosts.href='/hosts?'+new URLSearchParams({profile:scope.profile});add(crumb,'span',' / ');add(crumb,'a',scope.profile+' / '+scope.host_id+' · Console 紀錄').href='/hosts?'+new URLSearchParams({profile:scope.profile,host:scope.host_id,view:'console'});}
  else add(crumb,'span',' / '+session.host_id);
  add(crumb,'span',' / ');const river=add(crumb,bid?'a':'span',`${session.title}（${sid.slice(0,8)}） · ${mode}`);if(bid){river.id='river';river.href=readerLink(sid,{history,scope});add(crumb,'span',' / 區塊內容');}
  $('mode').textContent=history?'唯讀紀錄：顯示本次載入時已保存的內容，不自動接收更新，也不提供表單回覆。重新整理頁面可讀取較新的紀錄。':'即時檢視：只接收此 session 的命令、輸出與回覆。開啟頁面不會自動連線、重新執行或接管其他 Console；尚未接上停止控制。';
  $('new-window').href=readerLink(sid,{history,bid,scope});
  $('history-view').hidden=history;$('history-view').href=readerLink(sid,{history:true,scope});
}
function bottom(){const secret=$('secret-input');if(follow&&!secret?.contains(document.activeElement))$('transcript').scrollTop=$('transcript').scrollHeight;}
function meta(){const s=snapshot.session;navigation();$('title').textContent=s.title;$('target').textContent=s.host_id+' · '+s.session_id;$('cursor').textContent=`${snapshot.blocks.length} 個區塊 · 更新 #${snapshot.seq}`;hostTabs.render(s,closedHosts,tabStates());if(bid)tabsRoot.hidden=true;const identity=focusedIdentity(snapshot.blocks,null);const identities=hostList(s).length?hostList(s).map(t=>t.profile+' / '+t.host_id+'：'+identityLabel(focusedIdentity(snapshot.blocks,t.id))).join(' ｜ '):identityLabel(identity);$('identity').textContent=history?'歷史身分回報：'+identities.replaceAll(' · 目前 ',' · 當時 '):identities;updateActivity();const state=snapshot.blocks.filter(b=>b.kind==='status').at(-1);$('state').textContent=state?'來源最後回報：'+state.head:'紀錄服務已就緒';$('toolbar').hidden=false;}
function updateActivity(){if(!snapshot)return;if(history){$('activity').hidden=true;return;}const state=activityState(snapshot);if($('activity').textContent!==state.label)$('activity').textContent=state.label;$('activity').classList.toggle('processing',state.busy);$('activity').classList.toggle('thinking',state.thinking);$('activity').hidden=!state.label;}
function responseUI(card,block){
  if(block.kind!=='form')return;
  if(history){card.form.replaceChildren();const r=block.response;add(card.form,'p',r?`已記錄回覆：${r.choice} · ${r.actor} · ${formatDateTime(r.received_at)}`:'紀錄中的表單（唯讀，不提供回覆）。');if(r)add(card.form,'pre',JSON.stringify(r.values,null,2));return;}
  if(block.response||block.status!=='waiting'||block.expired){card.form.replaceChildren();const r=block.response;add(card.form,'p',r?`已回覆：${r.choice} · ${r.actor} · ${formatDateTime(r.received_at)}`:block.expired?'表單已逾期，不能再提交。':'此請求已取消。');if(r)add(card.form,'pre',JSON.stringify(r.values,null,2));return;}
  if(card.form.childNodes.length)return;
  const form=document.createElement('form'),inputs=new Map();
  for(const field of block.form.fields){const label=document.createElement('label');add(label,'span',field.label);const input=document.createElement(field.type==='select'?'select':field.type==='textarea'?'textarea':'input');if(field.type==='checkbox')input.type='checkbox';else if(input.tagName==='INPUT')input.type='text';if(field.type==='select')for(const option of field.options){const opt=add(input,'option',option);opt.value=option;}input.name=field.name;input.required=field.required;input.maxLength=1000;label.append(input);form.append(label);inputs.set(field.name,input);const saved=drafts.get(block.id)?.[field.name];if(saved!==undefined){if(field.type==='checkbox')input.checked=saved;else input.value=saved;}input.addEventListener('input',()=>{const values={};for(const [name,el] of inputs)values[name]=el.type==='checkbox'?el.checked:el.value;drafts.set(block.id,values);});}
  const notice=add(form,'p','回覆只會保存並交給 agent，不會直接執行遠端命令。','note');const buttons=[];
  for(const choice of block.form.choices){const button=add(form,'button',choice.label);button.type='submit';button.value=choice.id;buttons.push(button);}
  let pending=null;
  form.onsubmit=async event=>{event.preventDefault();if(buttons.some(b=>b.disabled))return;const values={};for(const [name,input] of inputs)values[name]=input.type==='checkbox'?input.checked:input.value;const choice=event.submitter?.value;if(!choice)return;pending??={event_id:crypto.randomUUID(),revision:block.revision,choice,values};buttons.forEach(b=>b.disabled=true);inputs.forEach(el=>el.disabled=true);notice.textContent='正在保存回覆…';try{await request('/blocks/'+block.id+'/responses',pending);drafts.delete(block.id);await refresh();}catch(error){notice.textContent='尚未確認保存：'+error.message+'。可重新載入核對；再次提交將使用相同請求。';buttons.forEach(b=>{b.disabled=b.value!==pending.choice;if(!b.disabled)b.textContent='重試相同回覆';});} };
  card.form.append(form);
}
async function copyBlock(card,block){
  const button=card.copy;
  if(button.disabled)return;
  button.disabled=true;
  try{
    const text=readBlockText(block,(offset,limit)=>request('/blocks/'+block.id+'/content?offset='+offset+'&limit='+limit));
    if(typeof ClipboardItem==='function'&&navigator.clipboard?.write){
      try{
        await navigator.clipboard.write([new ClipboardItem({'text/plain':text.then(value=>new Blob([value],{type:'text/plain'}))})]);
      }catch{
        await navigator.clipboard.writeText(await text);
      }
    }else{
      await navigator.clipboard.writeText(await text);
    }
    $('connection').textContent='已複製完整區塊內容。';
  }catch{
    $('connection').textContent='無法複製。可選取區塊文字後手動複製。';
  }finally{
    button.disabled=false;
  }
}
function update(block){
  if(bid&&block.id!==bid)return;
  if(!bid&&!visibleInRiver(block))return;
  let card=cards.get(block.id);
  if(!card){const compact=!bid&&!['analysis','form'].includes(block.kind);const el=document.createElement('article');el.className='event '+block.kind+(compact?' terminal-block':'');el.dataset.blockId=block.id;const source=add(el,'div','','source-line'),sourceTime=add(source,'time','','source-time'),sourceLabel=add(source,'span','','source-label'),sourceSuffix=add(source,'span','','source-suffix');const head=add(el,'header',''),title=add(el,'h2',block.title),stats=add(el,'p','','block-stats'),pre=add(el,'pre','');const progress=add(el,'p','','operation-progress');progress.setAttribute('role','status');progress.setAttribute('aria-live','polite');const actions=add(el,'div','','actions'),expand=add(actions,'button',bid?'讀取內容':'展開內容'),link=add(actions,'a','另開完整內容');link.href=readerLink(sid,{history,bid:block.id,scope:readerScope(snapshot.session,location.search)});link.target='_blank';link.rel='noopener';if(bid||block.kind==='analysis')link.hidden=true;const full=add(el,'pre','','full-content');full.hidden=true;const more=add(actions,'button','載入下一段'),collapse=add(actions,'button','收合'),copy=add(actions,'button','複製','text-control block-copy');copy.type='button';copy.title='複製區塊原文';more.hidden=true;collapse.hidden=true;const blockToggle=add(actions,'button','↑','text-control block-toggle');blockToggle.type='button';blockToggle.hidden=true;blockToggle.onclick=()=>card.toggle();const form=add(el,'div','','reply-form');head.hidden=!bid;stats.hidden=!bid;title.hidden=compact||(!bid&&block.kind==='analysis');if(!bid){for(const [control,label,arrow] of [[expand,'展開內容','▸'],[more,'載入下一段','↓'],[collapse,'收合','▴'],[link,'另開完整內容','↗']]){control.classList.add('text-control');control.setAttribute('aria-label',label);control.title=label;control.textContent=arrow;}}card={el,head,title,stats,pre,progress,expand,full,more,collapse,copy,form,compact,source,sourceLabel,sourceSuffix,sourceTime,link,blockToggle,offset:0,loaded:false,loading:false};if(!bid){source.setAttribute('role','button');source.tabIndex=0;source.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();card.toggle();}});source.addEventListener('click',()=>{if(!window.getSelection()?.toString())card.toggle();});}cards.set(block.id,card);$('transcript').insertBefore(el,$('secret-input')||$('activity'));
    async function load(){if(card.loading||block.size===0)return;card.loading=true;expand.disabled=true;more.disabled=true;try{const limit=contentWindow(block,card.offset,history);const page=limit?await request('/blocks/'+block.id+'/content?offset='+card.offset+'&limit='+limit):{text:'',next_offset:card.offset,total_bytes:block.size};const total=history?block.size:page.total_bytes;if(!card.loaded){full.textContent='';card.loaded=true;}full.textContent+=displayText(page.text);card.offset=page.next_offset;full.hidden=false;pre.hidden=true;collapse.hidden=!!bid;expand.hidden=true;more.hidden=card.offset>=total;const progress=`載入下一段（已讀 ${card.offset.toLocaleString()} / ${total.toLocaleString()} bytes）`;more.title=progress;if(bid)more.textContent=progress;bottom();}catch(error){$('connection').textContent='無法讀取區塊：'+error.message;}finally{card.loading=false;expand.disabled=false;more.disabled=false;}}
    card.load=load;expand.onclick=load;more.onclick=load;collapse.onclick=()=>{card.loaded=false;card.offset=0;full.textContent='';full.hidden=true;pre.hidden=false;expand.hidden=!card.truncated;more.hidden=true;collapse.hidden=true;};
  }
  card.head.textContent=`#${block.position} · ${labels[block.kind]||block.kind} · ${formatDateTime(block.created_at)}`;card.title.textContent=block.title;card.stats.textContent=`${statuses[block.status]||block.status} · ${block.size.toLocaleString()} bytes · ${block.lines} 個換行 · v${block.revision}${block.expired?' · 已逾期':''}`;const shown=preview(block,!bid);card.truncated=!!block.tail||shown!==block.head;card.pre.textContent=blockDisplayText(block,shown);card.copy.hidden=block.size===0;card.copy.onclick=()=>copyBlock(card,block);if(!bid&&!card.loaded)card.expand.hidden=!card.truncated;if(card.loaded)card.more.hidden=card.offset>=block.size;const processing=!history&&['command','analysis','status'].includes(block.kind)&&block.status==='streaming';card.progress.hidden=!processing;card.progress.textContent=processing?'處理中…':'';card.progress.classList.toggle('processing',processing);card.el.setAttribute('aria-busy',String(processing));responseUI(card,block);sourceView(card,block);
}
async function refresh(){const data=await request();snapshot=data;meta();if(bid&&!snapshot.blocks.some(b=>b.id===bid))throw Error('找不到此區塊');for(const b of snapshot.blocks)update(b);if(bid){const card=cards.get(bid);if(!card.loaded)await card.load();}bottom();}
function announceReader(){
  if(readerAnnounced)return;readerAnnounced=true;
  // A readiness notice is ephemeral metadata, not a durable form or host action.
  void fetch(api+'/reader-events',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({view:history?(bid?'history_block':'history'):(bid?'block':'live'),block_id:bid||null,seen_seq:snapshot.seq})})
    .catch(()=>{});
}
async function restore(){controller?.abort();const c=new AbortController();controller=c;try{await refresh();if(c.signal.aborted)return;announceReader();$('connection').textContent=history?`唯讀紀錄已載入 · 保存進度 #${snapshot.seq}；不自動更新。`:'已載入此 session；持續接收區塊更新。';if(!history)await listen(c);}catch(error){if(!c.signal.aborted)$('connection').textContent=error.message;}}
async function listen(c){try{const response=await fetch(api+'/stream?after='+snapshot.seq,{signal:c.signal});if(response.status===401){location.assign('/login?next='+encodeURIComponent(location.pathname+location.search));return;}if(!response.ok)throw Error('stream_failed');const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';while(true){const {value,done}=await reader.read();if(done)throw Error('stream_closed');buffer+=decoder.decode(value,{stream:true});let end;while((end=buffer.indexOf('\n\n'))>=0){const raw=buffer.slice(0,end);buffer=buffer.slice(end+2);const line=raw.split('\n').find(l=>l.startsWith('data: '));if(!line)continue;const event=JSON.parse(line.slice(6)),next=consume(snapshot,event);if(next!==snapshot){snapshot=next;if(event.block)update(event.block);meta();bottom();}}}}catch(error){if(c.signal.aborted)return;$('connection').textContent='更新中斷，正在補回保存的狀態…';setTimeout(()=>{if(controller===c&&!c.signal.aborted)restore();},1500);}}
$('transcript').addEventListener('scroll',()=>{const el=$('transcript');follow=el.scrollHeight-el.scrollTop-el.clientHeight<45;$('follow').textContent=follow?'跟隨最新內容':'已暫停自動捲動';});
$('latest').onclick=()=>{follow=true;bottom();$('follow').textContent='跟隨最新內容';};
if(bid)$('follow').textContent='逐頁閱讀';
const activityTimer=history?null:setInterval(updateActivity,1000);
// Historical readers never enumerate or submit live secrets.
const secretRoot=document.createElement('section');secretRoot.id='secret-input';secretRoot.className='reply-form';secretRoot.setAttribute('aria-label','安全輸入');
if(!history)$('transcript').insertBefore(secretRoot,$('activity'));
const stopSecrets=history?()=>{}:mountSecretInput(secretRoot,{api,onChange:bottom,onError:error=>{secretRoot.textContent=error.message;}});
window.addEventListener('pagehide',()=>{controller?.abort();clearInterval(activityTimer);stopSecrets();});
restore();
