export function applyDelta(previous,delta) {
  const state=structuredClone(previous);
  for(const op of delta){
    if(!Array.isArray(op.path)||!op.path.length||op.path.length>8||op.path.some(key=>typeof key!=='string'||['__proto__','prototype','constructor'].includes(key)))throw Error('invalid_delta_path');
    let target=state;
    for(const key of op.path.slice(0,-1))target=target[key];
    const key=op.path.at(-1);
    if(op.op==='set')target[key]=structuredClone(op.value);
    else if(op.op==='append_text')target[key]+=op.value;
    else if(op.op==='append')target[key].push(structuredClone(op.value));
    else throw Error('invalid_delta_operation');
  }
  return state;
}
export function consumeEvent(snapshot,event){
  if(event.work_id!==snapshot.state.work_id)throw Error('wrong_work');
  if(event.seq<=snapshot.seq)return snapshot;
  if(event.seq!==snapshot.seq+1)throw Error('event_gap');
  return {...snapshot,seq:event.seq,state:applyDelta(snapshot.state,event.delta)};
}

export function canApprove(state){
  return ['awaiting_plan','awaiting_step','paused'].includes(state.status)&&!!state.plan&&state.plan.next<state.plan.steps.length;
}

export function nextAction(state){
  if(['failed','interrupted','closed'].includes(state.status))return '此工作已停止，不會自動重試。請檢閱下方歷程與分析；需要繼續時，展開「建立／恢復互動工作」建立新工作，再提交計畫並確認。清理狀態請分開核對。';
  if(state.status==='failed_step')return '此步驟失敗，後續步驟已暫停。請檢閱輸出，由 agent 提出修正計畫後再確認，不會自動重跑。';
  if(['paused','ready'].includes(state.status)&&state.plan&&state.plan.next>=state.plan.steps.length)return '本階段計畫已執行完畢，沒有待執行的下一步，不必再次確認。請檢閱輸出並告訴聊天中的 agent「讀取結果」；後續檢查需先提出新計畫。';
  if(['awaiting_plan','awaiting_step','paused'].includes(state.status))return '請檢閱計畫與已完成的輸出，再按「確認並執行／繼續」。若要變更命令，先請 agent 提交新計畫。';
  return '';
}
