export function consume(snapshot,event){
  if(event.session_id!==snapshot.session.session_id)throw Error('wrong_session');
  if(event.seq<=snapshot.seq)return snapshot;
  if(event.seq!==snapshot.seq+1)throw Error('event_gap');
  let session=Object.hasOwn(event,'activity')?{...snapshot.session,activity:event.activity}:snapshot.session;
  if(Object.hasOwn(event,'target_activities'))session={...session,target_activities:event.target_activities};
  if(event.type==='activity.updated')return {...snapshot,session,seq:event.seq};
  const blocks=snapshot.blocks.slice(),index=blocks.findIndex(b=>b.id===event.block.id);
  if(index<0)blocks.push(event.block);else blocks[index]=event.block;
  return {...snapshot,session,seq:event.seq,blocks};
}
export function displayText(raw){return raw.replace(/\r\n/g,'\n').split('\n').map(line=>line.split('\r').at(-1)).join('\n').replace(/\x1b\[[0-?]*[ -/]*[@-~]/g,'');}
export function preview(block,compact=false){
  const head=block.head.split('\n').slice(0,5).join('\n').slice(0,600);
  if(!block.tail&&head===block.head)return head;
  const tail=(block.tail||block.head).split('\n').slice(-5).join('\n').slice(-600);
  return head+(compact?'\n⋯\n':'\n⋯（預覽；完整內容請展開或另開）⋯\n')+tail;
}

export function blockDisplayText(block,shown){
  if(block.size===0&&block.status==='completed'&&['stdout','stderr'].includes(block.kind)){
    return `${block.kind}：沒有輸出。`;
  }
  if(block.kind==='status'&&shown===block.head&&!block.tail&&/^[a-z][a-z0-9-]{0,39}$/.test(block.title)){
    try{
      const result=JSON.parse(shown);
      const outcomes={success:'成功',partial:'部分完成',failed:'失敗',unknown:'結果不明'};
      if(Object.hasOwn(outcomes,result.status)&&Object.keys(result).length===2&&
         Object.keys(result.output).length===1&&Number.isInteger(result.output.exit_code)){
        return `Recipe runner：${outcomes[result.status]}（runner 退出碼 ${result.output.exit_code}）`;
      }
    }catch{}
  }
  return displayText(shown);
}

export async function readBlockText(block,readPage){
  const encoder=new TextEncoder();
  if(!block.tail&&encoder.encode(block.head).length===block.size)return block.head;
  const chunks=[];
  for(let offset=0;offset<block.size;){
    const limit=Math.max(256,Math.min(16384,block.size-offset));
    const page=await readPage(offset,limit);
    if(page.next_offset<=offset)throw Error('incomplete_block_content');
    chunks.push(page.next_offset>block.size
      ?new TextDecoder().decode(encoder.encode(page.text).subarray(0,block.size-offset))
      :page.text);
    offset=page.next_offset;
  }
  return chunks.join('');
}

export function visibleInRiver(block){return block.kind!=='identity';}
export function processingState(blocks){
  const busy=blocks.some(b=>['command','analysis','status'].includes(b.kind)&&b.status==='streaming');
  return {busy,label:busy?'處理中…':'目前沒有進行中的操作回報'};
}
export function activityState(snapshot,now=Date.now()){
  const work=processingState(snapshot.blocks),activities=[snapshot.session.activity,...Object.values(snapshot.session.target_activities??{})];
  const activity=activities.find(a=>a?.state==='thinking'&&Date.parse(a.expires_at)>now)??snapshot.session.activity;
  if(work.busy||activity?.state!=='thinking')return {...work,thinking:false};
  const expires=Date.parse(activity.expires_at);
  if(!Number.isFinite(expires)||expires<=now)return {busy:false,thinking:false,label:'Agent 狀態未更新'};
  return {busy:false,thinking:true,label:'Agent 思考中…'};
}
export function identityLabel(block){
  if(!block)return '尚無身分回報';
  try{const env=JSON.parse(block.head);if(typeof env.host==='string'&&typeof env.effective_user==='string')return `${env.host} · 登入 ${env.connection_user??'未知'} · 目前 ${env.effective_user} · ${env.identity_verified?'身分已核對':'身分未核對'}`;}catch{}
  return '已有身分回報（詳情保留於紀錄）';
}
