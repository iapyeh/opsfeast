import {agentMeal} from './recipe-launch.mjs';
import {mealTree,renderSetEditor,renderSetDelete} from './locales/recipe-menu-zh-TW.mjs';
import {readScopeEditors} from './recipe-menu-layout.mjs';
import {workspaceUrl} from './workspace-url.mjs';

export function mealEntries(data) {
 const meals=[...(data.sets||[]),...(data.user_sets||[])],byId=new Map(meals.map(m=>[m.id,m]));
 const items=new Map(data.items.map(i=>[i.reference,i]));
 const cache=new Map();
 const ready=(id,path=new Set())=>{
  if(cache.has(id))return cache.get(id);
  const meal=byId.get(id);if(!meal||path.has(id))return false;
  const refs=meal.recipes||meal.references||[],children=meal.meals||[];
  const result=!!(refs.length+children.length)&&refs.every(ref=>items.get(ref)?.runnable)&&children.every(child=>ready(child,new Set([...path,id])));
  cache.set(id,result);return result;
 };
 return meals.map(m=>({...m,reference:m.id,entry_kind:'meal',purpose:m.description,
  source:m.id.startsWith('bundle:')?'repository':'profile',status:'success',runnable:ready(m.id)}));
}

export function renderMealDetail(meal,data,{e,profile}) {
 const parents=(data.user_sets||[]).filter(m=>m.meals.includes(meal.id));
 const editable=!meal.id.startsWith('bundle:');
 return `<a href="${e(workspaceUrl('/recipes',profile))}">← Recipes 與套餐清單</a><article class="panel"><h1>${e(meal.title)}</h1><p>${e(meal.description)}</p>
 <p>套餐 · ${editable?'Profile 自訂':'Bundle'} · ${meal.runnable?'可執行':'不可執行'}</p><code>${e(meal.id)}</code>
 <div class="recipe-actions">${editable?'<button class="button" id="meal-edit">修改套餐</button><button class="button" id="meal-delete">刪除套餐</button>':'<p>Bundle 套餐為唯讀；可建立使用者套餐引用它。</p>'}
 ${meal.runnable&&!agentMeal(meal,data)&&profile?`<a class="button" href="${e(workspaceUrl('/recipe-plate',profile,{meal:meal.id}))}">加入執行餐盤</a>`:''}</div>
 ${agentMeal(meal,data)?'<p>此套餐包含需要 agent 協助的 Recipe；請開啟下方各 Recipe 專頁，複製建議 prompt 到對話。</p>':''}<h2>套餐內容</h2><ul>${mealTree(meal,data,e,profile)}</ul>
 ${parents.length?`<h2>引用此套餐的套餐</h2><ul>${parents.map(m=>`<li><a href="${e(workspaceUrl('/recipes',profile,{meal:m.id}))}">${e(m.title)}</a></li>`).join('')}</ul>`:''}
 <p class="field-hint">修改會影響之後引用此套餐的執行；主機屬於執行餐盤，已保存的執行紀錄不變。可執行表示靜態內容可展開，不是 enabled 設定或主機可用性保證。</p>
 <p role="status" id="meal-notice"></p></article><div id="meal-editor"></div><dialog id="meal-delete-dialog"><div id="meal-delete-content"></div></dialog>`;
}

export function readMealForm(form) {
 const values=new FormData(form),recipes=[...form.querySelectorAll('[data-set-recipe]:checked')].map(i=>i.value);
 return {title:values.get('title').trim(),description:values.get('description'),recipes,
  meals:[...form.querySelectorAll('[data-set-meal]:checked')].map(i=>i.value),selections:readScopeEditors(form,recipes)};
}

export function mountMealDetail(root,{data,id,profile,e,api,onDeleted=()=>{location.href=workspaceUrl('/recipes',profile);},onCreated=identifier=>{window.history.replaceState(null,'',workspaceUrl('/recipes',profile,{meal:identifier}));}}) {
 if(!profile){root.innerHTML='<p role="status">請先設定預設 Profile，再管理套餐。</p>';return;}
 const apply=preferences=>{data.preferences=preferences;data.user_sets=preferences.sets;};
 const mutate=(action,changes)=>api('/api/v1/recipe-menu/preferences',{profile,expected_revision:data.preferences.revision,action,changes});
 const showEditor=(saved,editing=false)=>{
  const content=root.querySelector('#meal-editor');
  content.innerHTML=renderSetEditor(data,saved,e,{heading:editing?'修改套餐':'建立套餐'});
  const form=content.querySelector('#menu-set-form');
  form.querySelectorAll('[data-set-recipe]').forEach(input=>input.addEventListener('change',()=>{
   form.querySelectorAll('[data-set-scope]').forEach(section=>{if(section.dataset.setScope===input.value)section.hidden=!input.checked;});
  }));
  form.querySelector('[data-editor-cancel]').addEventListener('click',()=>editing?render():onDeleted());
  form.addEventListener('submit',async event=>{
   event.preventDefault();const button=event.submitter;button.disabled=true;
   try {
    const changes=readMealForm(form),before=new Set(data.user_sets.map(m=>m.id));
    const preferences=await mutate(editing?'set.update':'set.create',editing?{id:saved.id,...changes}:changes);
    apply(preferences);
    if(!editing){id=preferences.sets.find(m=>!before.has(m.id)).id;onCreated(id);}
    render();root.querySelector('#meal-notice').textContent='已儲存套餐；不會啟動執行。';
   }catch(error){content.querySelector('#menu-editor-error').textContent=error.message==='cyclic_meal_reference'?'套餐不能互相循環引用。':error.message;button.disabled=false;}
  });
 };
 const render=()=>{
  if(id==='new'){
   root.innerHTML=`<a href="${e(workspaceUrl('/recipes',profile))}">← Recipes 與套餐清單</a><div id="meal-editor"></div>`;
   let saved={title:'',description:'',recipes:[],meals:[],selections:{}};
   try{const key='opsfeast-meal-prefill:'+data.preferences.scope_id,raw=sessionStorage.getItem(key);sessionStorage.removeItem(key);if(raw)saved={...saved,...JSON.parse(raw)};}catch{}
   showEditor(saved);return;
  }
  const meal=mealEntries(data).find(m=>m.id===id);
  if(!meal){root.innerHTML='<p role="alert">找不到此套餐。</p>';return;}
  root.innerHTML=renderMealDetail(meal,data,{profile,e});
  root.querySelector('#meal-edit')?.addEventListener('click',()=>showEditor(meal,true));
  root.querySelector('#meal-delete')?.addEventListener('click',()=>{
   const dialog=root.querySelector('#meal-delete-dialog'),content=root.querySelector('#meal-delete-content');
   content.innerHTML=renderSetDelete(meal,e,data);content.querySelector('[data-editor-cancel]').addEventListener('click',()=>dialog.close());
   content.querySelector('#menu-delete-confirm').addEventListener('click',async event=>{
    event.target.disabled=true;
    try{apply(await mutate('set.delete',{id:meal.id}));dialog.close();onDeleted();}
    catch(error){content.querySelector('#menu-editor-error').textContent=error.message;event.target.disabled=false;}
   });dialog.showModal();
  });
 };
 render();
}
