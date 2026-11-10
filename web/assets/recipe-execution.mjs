import {renderReview} from './locales/recipe-menu-zh-TW.mjs';
export async function reviewPlate(root,{profile,selection,e,api,onEdit,onStarted}) {
 root.innerHTML='<p role="status">正在驗證餐盤與共用連線計畫…</p>';
 try {
  const plan=await api('/api/v1/recipe-runs/preview',{profile,...selection,timeout:30});
  root.innerHTML=renderReview(plan,e);
  const confirm=root.querySelector('#recipe-confirm'),start=root.querySelector('#recipe-start');
  confirm.addEventListener('change',()=>{start.disabled=!confirm.checked;});
  root.querySelector('#recipe-edit').addEventListener('click',onEdit);
  start.addEventListener('click',async()=>{
   if(!confirm.checked)return;start.disabled=true;
   try{const run=await api('/api/v1/recipe-runs',{preview_id:plan.preview_id,confirmed:true});onStarted(run);}catch(error){root.querySelector('#recipe-execution-error').textContent=error.message;start.disabled=false;}
  });
 }catch(error){root.innerHTML=`<p role="alert">${e(error.message)}</p><button class="button" id="recipe-edit">返回選菜</button>`;root.querySelector('#recipe-edit').addEventListener('click',onEdit);}
}
