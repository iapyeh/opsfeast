// Volatile input only: never use drafts, localStorage, Console forms or analytics.
export function mountSecretInput(root,{api,fetcher=fetch,document:doc=document,onError=()=>{},onChange=()=>{}}){
  let stopped=false,timer=null,active=null,form=null;
  const add=(parent,tag,text)=>{const el=doc.createElement(tag);el.textContent=text;parent.append(el);return el;};
  async function call(path,body){
    const response=await fetcher(api+'/secret-requests'+path,{method:body===undefined?'GET':'POST',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
    if(!response.ok)throw Error('安全輸入服務無法使用（'+response.status+'）');
    return response.json();
  }
  function clear(){if(form)for(const input of form.querySelectorAll('input'))input.value='';root.replaceChildren();form=null;active=null;}
  function render(item){
    if(!item){clear();return;}
    if(active===item.request_id&&form){if(item.state!=='waiting'){clear();add(root,'p','密碼已送出或請求已取消；等待執行工具確認。');}return;}
    clear();active=item.request_id;
    if(item.state!=='waiting'){add(root,'p','等待執行工具確認安全輸入。');return;}
    form=doc.createElement('form');form.autocomplete='off';
    add(form,'h2','安全輸入');
    const label=add(form,'label',item.label),input=doc.createElement('input');
    input.type='password';input.autocomplete='off';input.maxLength=4096;
    input.setAttribute('aria-label',item.label);input.setAttribute('data-secret-input','');label.append(input);
    const notice=add(form,'p','密碼只交給本次執行工具，不保存於河道或歷史紀錄。逾期後將丟棄。');notice.setAttribute('role','status');
    const submit=add(form,'button','送出密碼');submit.type='submit';
    const cancel=add(form,'button','取消');cancel.type='button';
    cancel.onclick=async()=>{input.value='';submit.disabled=cancel.disabled=true;try{await call('/'+item.request_id+'/cancel',{});clear();}catch{notice.textContent='取消結果尚未確認，請重新整理核對。';}};
    form.onsubmit=async event=>{
      event.preventDefault();if(submit.disabled)return;
      submit.disabled=cancel.disabled=input.disabled=true;
      let value=input.value;input.value='';
      notice.textContent='正在交給執行工具…';
      try{const pending=call('/'+item.request_id+'/submit',{value});value=null;await pending;clear();add(root,'p','密碼已送出；等待執行工具確認。');}
      catch{value=null;notice.textContent='送出結果尚未確認；不會自動重送。請重新整理核對。';}
    };
    root.append(form);
  }
  async function poll(){
    try{const data=await call('');if(!stopped){render(data.requests.find(r=>r.state==='waiting')||data.requests[0]);onChange();}}
    catch(error){if(!stopped){clear();onError(error);}}
    finally{if(!stopped)timer=setTimeout(poll,1000);}
  }
  poll();
  return ()=>{stopped=true;clearTimeout(timer);clear();};
}
