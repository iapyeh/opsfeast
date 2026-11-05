// Host folding changes presentation only. Block order and execution targets stay fixed.
export function hostList(session){return session.targets??[];}
export function hostPresentation(session,block,closed=new Set()){
  const hosts=hostList(session),index=hosts.findIndex(h=>h.id===block.target_id),host=hosts[index];
  return {host:host??null,tone:index<0?null:index%6,muted:!!host&&closed.has(host.id),
    label:host?`${host.icon} ${host.host_id}${new Set(hosts.map(h=>h.profile)).size>1?' · '+host.profile:''}`:'共同分析／任務訊息'};
}
export function focusedIdentity(blocks,selected){
  return blocks.filter(b=>b.kind==='identity'&&(!selected||b.target_id===selected)).at(-1);
}
export function mountHostTabs(root,onSelect){
  let key='';
  root.setAttribute('role','group');root.setAttribute('aria-label','開啟或閉合主機區塊');
  function render(session,closed=new Set(),states=null){
    const hosts=hostList(session);root.hidden=hosts.length===0;
    const next=JSON.stringify(hosts);
    if(next!==key){
      key=next;root.replaceChildren();
      for(const host of [null,...hosts]){
        const button=document.createElement('button');button.type='button';
        button.setAttribute('aria-controls','transcript');button.dataset.targetId=host?.id??'';button.textContent=host?`${host.icon} ${host.host_id}`:'全部';
        button.addEventListener('click',()=>onSelect(host?.id??null));
        button.addEventListener('keydown',event=>{
          const buttons=[...root.children],index=buttons.indexOf(button);
          let nextIndex;if(event.key==='ArrowRight')nextIndex=(index+1)%buttons.length;
          else if(event.key==='ArrowLeft')nextIndex=(index+buttons.length-1)%buttons.length;
          else if(event.key==='Home')nextIndex=0;else if(event.key==='End')nextIndex=buttons.length-1;else return;
          event.preventDefault();buttons[nextIndex].focus();
        });
        root.append(button);
      }
    }
    for(const button of root.children){const id=button.dataset.targetId||null,active=states?.get(id)??(id?!closed.has(id):closed.size===0);button.setAttribute('aria-pressed',String(active));button.tabIndex=0;}
  }
  return {render};
}
