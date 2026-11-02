export function consume(snapshot,event){
  if(event.session_id!==snapshot.session.session_id)throw Error('wrong_session');
  if(event.seq<=snapshot.seq)return snapshot;
  if(event.seq!==snapshot.seq+1)throw Error('event_gap');
  const blocks=snapshot.blocks.slice(),index=blocks.findIndex(b=>b.id===event.block.id);
  if(index<0)blocks.push(event.block);else blocks[index]=event.block;
  return {...snapshot,seq:event.seq,blocks};
}
export function displayText(raw){return raw.replace(/\r\n/g,'\n').split('\n').map(line=>line.split('\r').at(-1)).join('\n').replace(/\x1b\[[0-?]*[ -/]*[@-~]/g,'');}
export function preview(block,compact=false){
  const head=block.head.split('\n').slice(0,5).join('\n').slice(0,600);
  if(!block.tail&&head===block.head)return head;
  const tail=(block.tail||block.head).split('\n').slice(-5).join('\n').slice(-600);
  return head+(compact?'\n⋯\n':'\n⋯（預覽；完整內容請展開或另開）⋯\n')+tail;
}

export function visibleInRiver(block){return block.kind!=='identity';}
export function identityLabel(block){
  if(!block)return '尚無身分回報';
  try{const env=JSON.parse(block.head);if(typeof env.host==='string'&&typeof env.effective_user==='string')return `${env.host} · 登入 ${env.connection_user??'未知'} · 目前 ${env.effective_user} · ${env.identity_verified?'身分已核對':'身分未核對'}`;}catch{}
  return '已有身分回報（詳情保留於紀錄）';
}
