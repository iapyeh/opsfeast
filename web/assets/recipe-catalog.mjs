import {mountRecipeDetail} from './recipe-detail.mjs';
import {recipeDomains} from './recipe-menu-layout.mjs';
import {domains,renderCategoryEditor} from './locales/recipe-menu-zh-TW.mjs';
import {workspaceUrl} from './workspace-url.mjs';
import {mealEntries,mountMealDetail} from './recipe-meals.mjs';

export function filterRecipes(items,{q='',source='',status='',category='',kind=''}={}) {
 const needle=q.trim().toLocaleLowerCase();
 return items.filter(item=>(!source||item.source===source)&&(!kind||(item.entry_kind||'recipe')===kind)&&
  (!status||(status==='runnable'?item.runnable:status==='unavailable'?!item.runnable:false))&&
  (!category||recipeDomains(item).includes(category))&&
  (!needle||[item.title,item.reference,item.purpose,item.version].some(value=>String(value||'').toLocaleLowerCase().includes(needle))));
}

export function renderRecipeCatalog(items,{e,profile,categories=[]}) {
 if(!items.length)return '<p role="status">沒有符合條件的 Recipes 或套餐。</p>';
 return `<div class="table-scroll"><table class="roadmap-table"><thead><tr><th scope="col">名稱</th><th scope="col">類型</th><th scope="col">狀態</th><th scope="col">來源</th><th scope="col">用途</th></tr></thead><tbody>${items.map(item=>`<tr><td><a href="${e(workspaceUrl('/recipes',profile,{[item.entry_kind==='meal'?'meal':'recipe']:item.reference}))}">${e(item.title)}</a><br><small class="field-hint">${e(item.reference)}</small></td><td>${item.entry_kind==='meal'?'套餐':'Recipe'}</td><td>${item.runnable?'可執行':'不可執行'}</td><td>${e(item.source==='repository'?'Bundle':item.source==='profile'?'Profile 自訂':item.source)}</td><td>${e(item.purpose||'')}</td></tr>`).join('')}</tbody></table></div>`;
}

export async function mountRecipeCatalog(root,{e,profiles=null,search='',fetchImpl=fetch}) {
 const api=async(path,body)=>{
  const response=await fetchImpl(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok)throw new Error(response.status===401?'請先登入管理帳號。':data.detail||'無法讀取 Recipes。');
  return data;
 };
 root.innerHTML='<p role="status">正在讀取 Recipes…</p>';
 try {
  if(!profiles)profiles=await api('/api/v1/profiles');
  const profile=profiles.default_profile,query=new URLSearchParams(search);
  if(query.get('recipe'))return mountRecipeDetail(root,{profile,reference:query.get('recipe'),e,api});
  const data=await api('/api/v1/recipe-menu'+(profile?'?'+new URLSearchParams({profile}):''));
  if(query.get('meal'))return mountMealDetail(root,{data,id:query.get('meal'),profile,e,api});
  let preferences=data.preferences;
  root.innerHTML=`<div class="page-heading"><div><h1>Recipes</h1><p class="intro">瀏覽 Recipes 與套餐；點名稱進入專頁檢閱與操作。</p></div><a class="button" href="${e(workspaceUrl('/recipe-plate',profile))}">前往執行餐盤 →</a></div>
  ${data.status!=='success'?'<p role="status">部分來源無法讀取；以下保留可用項目與檢查結果。</p>':''}
  <section class="panel"><label>搜尋 Recipes<input aria-label="搜尋 Recipes" type="search" id="recipe-catalog-query" value="${e(query.get('q')||'')}" placeholder="名稱、用途或 reference"></label>
  <div class="recipe-actions"><label>來源<select aria-label="來源" id="recipe-catalog-source"><option value="">全部來源</option>${(data.sources||[]).map(s=>`<option value="${e(s.name)}">${e(s.name==='repository'?'Bundle':s.name==='profile'?'Profile 自訂':s.name)}${s.status!=='available'?' · '+e(s.status):''}</option>`).join('')}</select></label>
  <label>類型<select aria-label="類型" id="recipe-catalog-kind"><option value="">Recipes 與套餐</option><option value="recipe">Recipe</option><option value="meal">套餐</option></select></label><label>狀態<select aria-label="狀態" id="recipe-catalog-status"><option value="">全部狀態</option><option value="runnable">可執行</option><option value="unavailable">不可執行</option></select></label>
  <label>分類<select aria-label="分類" id="recipe-catalog-category"></select></label>
  <button class="button" id="recipe-catalog-refresh">重新讀取清單</button>${profile?`<a class="button" href="${e(workspaceUrl('/recipes',profile,{meal:'new'}))}">建立套餐</a><button class="button" id="recipe-catalog-categories">管理自訂分類</button>`:''}</div>
  <p class="field-hint">可執行／不可執行表示靜態檢查結果，與 enabled／disabled 設定不同；主機條件與執行授權須在餐盤檢閱。</p><p role="status" id="recipe-catalog-count"></p></section>
  <div id="recipe-catalog-items"></div><dialog id="catalog-editor"><div id="catalog-editor-content"></div></dialog>`;
  const categoryChoices=()=>{
   const select=root.querySelector('#recipe-catalog-category'),previous=select.value;
   select.innerHTML='<option value="">全部分類</option>'+[...Object.entries(domains).map(([id,title])=>({id,title})),...(preferences?.categories||[])].map(c=>`<option value="${e(c.id)}">${e(c.title)}</option>`).join('');select.value=previous||'';
  };
  categoryChoices();
  for(const key of ['source','status','category','kind'])root.querySelector('#recipe-catalog-'+key).value=query.get(key)||'';
  const render=()=>{
   const filters={q:root.querySelector('#recipe-catalog-query').value,...Object.fromEntries(['source','status','category','kind'].map(key=>[key,root.querySelector('#recipe-catalog-'+key).value]))};
   const items=filterRecipes([...data.items,...mealEntries(data)],filters);
   root.querySelector('#recipe-catalog-items').innerHTML=renderRecipeCatalog(items,{e,profile,categories:preferences?.categories||[]});
   root.querySelector('#recipe-catalog-count').textContent=`顯示 ${items.length} ／ 共 ${data.items.length+mealEntries(data).length} 個項目`;
  };
  for(const key of ['query','source','status','category','kind'])root.querySelector('#recipe-catalog-'+key).addEventListener(key==='query'?'input':'change',render);
  root.querySelector('#recipe-catalog-refresh').addEventListener('click',async event=>{
   event.target.disabled=true;
   try{const fresh=await api('/api/v1/recipe-menu'+(profile?'?'+new URLSearchParams({profile}):''));Object.assign(data,fresh);preferences=data.preferences;categoryChoices();render();}
   catch(error){root.querySelector('#recipe-catalog-count').textContent='讀取失敗：'+error.message+'；保留先前清單。';}
   finally{event.target.disabled=false;}
  });
  root.querySelector('#recipe-catalog-categories')?.addEventListener('click',()=>{
   const dialog=root.querySelector('#catalog-editor'),content=root.querySelector('#catalog-editor-content');
   content.innerHTML=renderCategoryEditor(preferences?.categories||[],e);
   content.querySelector('[data-editor-cancel]').addEventListener('click',()=>dialog.close());
   const form=content.querySelector('#menu-category-form');
   form.elements.namedItem('id').addEventListener('change',()=>{const current=preferences.categories.find(c=>c.id===form.elements.namedItem('id').value);form.elements.namedItem('title').value=current?.title||'';form.elements.namedItem('description').value=current?.description||'';});
   form.addEventListener('submit',async event=>{
    event.preventDefault();const button=event.submitter;button.disabled=true;
    try{const values=Object.fromEntries(new FormData(form));preferences=await api('/api/v1/recipe-menu/preferences',{profile,expected_revision:preferences.revision,action:values.id?'category.update':'category.create',changes:values.id?values:{title:values.title,description:values.description}});categoryChoices();render();dialog.close();}
    catch(error){content.querySelector('#menu-editor-error').textContent=error.message;button.disabled=false;}
   });dialog.showModal();
  });
  render();
 }catch(error){root.innerHTML=`<p role="alert">${e(error.message)}</p>`;}
}
