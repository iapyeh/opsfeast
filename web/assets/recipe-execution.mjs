import {renderReview} from './locales/recipe-menu-zh-TW.mjs';

export function draftReview(profile,selection,catalog) {
 const items=new Map((catalog?.items||[]).map(item=>[item.reference,item]));
 const meals=new Map([...(catalog?.sets||[]),...(catalog?.user_sets||[])].map(meal=>[meal.id,meal]));
 const references=new Set((selection.recipes||[]).map(choice=>choice.reference)),visited=new Set();
 const visit=id=>{
  if(visited.has(id))return;visited.add(id);
  const meal=meals.get(id);if(!meal)return;
  for(const ref of meal.recipes||meal.references||[])references.add(ref);
  for(const child of meal.meals||[])visit(child);
 };
 for(const id of selection.meals||[])visit(id);
 const pairs=[];
 for(const reference of references){
  const item=items.get(reference)||{};
  for(const host_id of item.kind==='report'?[null]:selection.hosts||[]){
   pairs.push({reference,host_id,kind:item.kind,access_mode:item.access_mode,identity:{}});
  }
 }
 return {profile,pairs,timeout:30,pending:true};
}

export async function reviewPlate(root,{profile,selection,e,api,onEdit,onStarted,catalog=null}) {
 const request=Symbol('recipe-review');root.recipeReviewRequest=request;
 let runtimeThreads=8,typedThreads=false;
 const draw=plan=>{
  root.innerHTML=renderReview({...plan,threads:runtimeThreads},e,catalog);
  const confirm=root.querySelector('#recipe-confirm'),start=root.querySelector('#recipe-start'),threads=root.querySelector('#recipe-threads');
  const valid=()=>Number.isSafeInteger(Number(runtimeThreads))&&Number(runtimeThreads)>0;
  confirm.checked=false;confirm.disabled=!!plan.pending;start.disabled=true;
  root.querySelector('#recipe-preview-status').textContent=plan.pending?'正在背景驗證參數與執行計畫，你可以先檢閱或調整同時執行數。':'驗證完成，請確認後再執行。';
  threads.addEventListener('input',()=>{
   runtimeThreads=threads.value;typedThreads=true;
   start.disabled=!!plan.pending||!confirm.checked||!valid();
   root.querySelector('#recipe-threads-notice').textContent=valid()?'僅用於這次執行，不會儲存到餐盤或套餐。':'請輸入大於零的整數。';
  });
  confirm.addEventListener('change',()=>{start.disabled=!!plan.pending||!confirm.checked||!valid();});
  root.querySelector('#recipe-edit').addEventListener('click',()=>{root.recipeReviewRequest=null;onEdit();});
  start.addEventListener('click',async()=>{
   if(plan.pending||!valid()||!confirm.checked||root.recipeReviewRequest!==request)return;start.disabled=true;
   try{const run=await api('/api/v1/recipe-runs',{preview_id:plan.preview_id,confirmed:true,threads:Number(runtimeThreads)});onStarted(run);}catch(error){root.querySelector('#recipe-execution-error').textContent=error.message;start.disabled=false;}
  });
 };
 draw(draftReview(profile,selection,catalog));
 Promise.resolve().then(()=>api('/api/v1/recipe-execution/settings')).then(defaults=>{
  if(root.recipeReviewRequest!==request||typedThreads||root.querySelector('#recipe-confirm').checked)return;
  if(Number.isSafeInteger(defaults.threads)&&defaults.threads>0){
   runtimeThreads=defaults.threads;root.querySelector('#recipe-threads').value=runtimeThreads;
   root.querySelector('#recipe-threads-notice').textContent=`設定預設值：${runtimeThreads}。`;
  }
 }).catch(()=>{ /* The displayed system default remains a one-time execution choice. */ });
 try {
  const plan=await api('/api/v1/recipe-runs/preview',{profile,...selection,timeout:30});
  if(root.recipeReviewRequest===request)draw(plan);
 }catch(error){
  if(root.recipeReviewRequest!==request)return;
  root.querySelector('#recipe-preview-status').textContent='驗證未完成，不能執行。';
  root.querySelector('#recipe-execution-error').textContent=error.message;
 }
}
