export async function mountExecutionSettings(root,{e,fetchImpl=fetch}) {
 root.innerHTML='<p role="status">正在讀取執行設定…</p>';
 const request=async(options={})=>{
  const response=await fetchImpl('/api/v1/recipe-execution/settings',options);
  const body=await response.json();
  if(!response.ok)throw new Error(response.status===409?'設定已被其他頁面修改，請重新載入後再儲存。':response.status===401?'請先登入管理帳號。':'無法讀取或儲存執行設定。');
  return body;
 };
 try{
  let current=await request();
  root.innerHTML=`<form class="panel" id="execution-settings-form"><label for="execution-default-threads">預設同時執行數（threads）</label><input id="execution-default-threads" type="number" min="1" step="1" required value="${e(current.threads)}"><p class="field-hint">預設 8。最多同時處理這個數量的主機；同一主機內的 recipes 依序執行。主機台數不限，超出的工作會排隊。</p><p class="field-hint">每次檢閱餐盤時可以臨時調整，不會改變這裡的預設值。儲存設定不會啟動任何工作。</p><button class="button primary" type="submit">儲存預設值</button><p id="execution-settings-status" role="status"></p></form>`;
  const form=root.querySelector('form'),input=root.querySelector('#execution-default-threads'),status=root.querySelector('#execution-settings-status');
  form.addEventListener('submit',async event=>{
   event.preventDefault();const threads=Number(input.value);
   if(!Number.isSafeInteger(threads)||threads<1){status.textContent='請輸入大於零的整數。';return;}
   const button=form.querySelector('button');button.disabled=true;
   try{current=await request({method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({threads,expected_revision:current.revision})});input.value=current.threads;status.textContent='已儲存，之後的新餐盤會使用此預設值。';}catch(error){status.textContent=error.message;}finally{button.disabled=false;}
  });
 }catch(error){root.innerHTML=`<p role="alert">${e(error.message)}</p>`;}
}
