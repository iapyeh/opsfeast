import {domains,renderLayout,renderPlate,renderSetEditor,renderCategoryEditor,renderSetDelete,renderScopeEditor,copy as c} from './locales/recipe-menu-zh-TW.mjs';

const pathDomains={hardware:'hardware',storage:'storage',software:'software',network:'network',account:'identity',access:'identity',logging:'observability',time:'workloads',process:'workloads',service:'workloads',services:'workloads',database:'workloads',observability:'observability',analysis:'analysis'};
export function recipeDomains(item) {
  if(Object.hasOwn(item,'category_ids'))return item.category_ids.length?[...item.category_ids]:['custom'];
  if(item.kind==='report')return ['reports'];
  const found=new Set((item.capabilities||[]).map(id=>id.split('.')[0]).filter(id=>Object.hasOwn(domains,id)));
  if(item.domain&&item.domain!=='custom'&&Object.hasOwn(domains,item.domain))found.add(item.domain);
  if(!found.size){
    const path=item.reference.slice(item.reference.indexOf(':')+1).split('/');
    const inferred=pathDomains[path[0]]||(path[0]==='system'?pathDomains[path[1]]:null);
    if(inferred)found.add(inferred);
  }
  return found.size?[...found]:['custom'];
}
export function groupRecipes(data) {
  const grouped=Object.entries(domains).map(([id,title])=>({id,title,capabilities:(data.blueprint?.capabilities||[]).filter(c=>c.domain===id),bundle:[],user:[]}));
  for(const category of data.custom_categories||[])grouped.push({...category,capabilities:[],bundle:[],user:[],user_defined:true});
  for(const item of data.items.filter(i=>!i.is_meal))for(const domain of recipeDomains(item)){
    const group=grouped.find(g=>g.id===domain);
    if(group)group[item.source==='repository'?'bundle':'user'].push(item);
  }
  return grouped.filter(g=>!['reports','custom'].includes(g.id)||g.bundle.length||g.user.length);
}
export function hostSelection(data,selected,kind,id,checked) {
  const enabled=new Set(data.hosts.filter(h=>h.enabled!==false).map(h=>h.host_id));
  const names=kind==='all'?[...enabled]:kind==='group'?(data.groups||[]).find(g=>g.id===id)?.host_ids.filter(h=>enabled.has(h))||[]:[id];
  const known=new Set(data.hosts.map(h=>h.host_id));
  const next=new Set(selected);
  for(const name of names)if(known.has(name))checked?next.add(name):next.delete(name);
  return next;
}
export function selectionMark(names,selected) {
  const count=names.filter(name=>selected.has(name)).length;
  return {checked:names.length>0&&count===names.length,indeterminate:count>0&&count<names.length};
}
export function applyUserSet(data,saved) {
 const knownRecipes=new Set(data.items.filter(i=>i.runnable).map(i=>i.reference)),knownHosts=new Set(data.hosts.map(h=>h.host_id));
 return {recipes:new Set(saved.recipes.filter(ref=>knownRecipes.has(ref))),hosts:new Set((saved.hosts||[]).filter(id=>knownHosts.has(id))),meals:new Set(saved.meals||[])};
}
export function readScopeEditors(root,allowed=null) {
 const selections={};
 for(const section of root.querySelectorAll('[data-scope-ref]')){
  if(allowed&&!allowed.includes(section.dataset.scopeRef))continue;
  if(section.querySelector('[data-scope-mode]').value!=='properties')continue;
  const properties=[...section.querySelectorAll('[data-scope-property]:checked')].map(i=>i.value);
  if(!properties.length)throw new Error('請至少選擇一個採集欄位。');
  selections[section.dataset.scopeRef]={properties};
 }return selections;
}
export function mountMenuLayout(root,{data,profiles,profile,initialRecipe,e,onProfile,api,onExecute,storage=typeof sessionStorage==='undefined'?null:sessionStorage}) {
 let selectedRecipes=new Set(),selectedHosts=new Set(),selectedMeals=new Set(),scopes={};
 const key='opsfeast-menu-draft-v2:'+ (data.preferences?.scope_id||profile||'bundle');
 try {
  const draft=JSON.parse(storage?.getItem(key)||'null');
  if(draft&&Array.isArray(draft.recipes)&&Array.isArray(draft.hosts)){
   const restored=applyUserSet(data,draft);selectedRecipes=restored.recipes;selectedHosts=restored.hosts;selectedMeals=restored.meals;scopes=draft.scopes||{};
  }
 }catch{}
 if(initialRecipe&&data.items.some(i=>i.reference===initialRecipe&&i.runnable))selectedRecipes.add(initialRecipe);
 const refresh=preferences=>{
  selectedMeals=new Set([...selectedMeals].filter(id=>data.sets.some(s=>s.id===id)||preferences.sets.some(s=>s.id===id)));
  data={...data,preferences,custom_categories:preferences.categories,user_sets:preferences.sets,items:data.items.map(i=>{const next={...i};delete next.category_ids;if(Object.hasOwn(preferences.assignments,i.reference))next.category_ids=preferences.assignments[i.reference];return next;})};render();
 };
 const mutation=(action,changes)=>api('/api/v1/recipe-menu/preferences',{profile,expected_revision:data.preferences.revision,action,changes});
 const render=()=>{
  root.innerHTML=renderLayout(data,groupRecipes(data),profiles,profile,e);
  const update=()=>{
   root.querySelectorAll('[data-dish]').forEach(input=>{input.checked=selectedRecipes.has(input.dataset.dish);input.closest('.menu-recipe').classList.toggle('is-selected',input.checked);});
   root.querySelectorAll('[data-host]').forEach(input=>{input.checked=selectedHosts.has(input.dataset.host);});
   const enabled=new Set(data.hosts.filter(h=>h.enabled!==false).map(h=>h.host_id));
   const all=root.querySelector('[data-all-hosts]');if(all)Object.assign(all,selectionMark([...enabled],selectedHosts));
   root.querySelectorAll('[data-group]').forEach(input=>{const group=(data.groups||[]).find(g=>g.id===input.dataset.group);Object.assign(input,selectionMark(group.host_ids.filter(id=>enabled.has(id)),selectedHosts));});
   root.querySelector('#recipe-plate-content').innerHTML=renderPlate(data,selectedHosts,selectedRecipes,e,scopes,selectedMeals,profile);
   root.querySelectorAll('[data-remove-meal]').forEach(button=>button.addEventListener('click',()=>{selectedMeals.delete(button.dataset.removeMeal);update();}));
   root.querySelectorAll('[data-scope]').forEach(button=>button.addEventListener('click',()=>{
    const item=data.items.find(i=>i.reference===button.dataset.scope),dialog=root.querySelector('#menu-editor-dialog'),content=root.querySelector('#menu-editor-content');
    content.innerHTML=`<form id="menu-scope-form"><h2>${e(item.title)} · 採集欄位</h2>${renderScopeEditor(item,scopes[item.reference],e)}<p role="alert" id="menu-editor-error"></p><button class="button" type="submit">套用欄位選擇</button><button class="button" type="button" data-editor-cancel>取消</button></form>`;
    content.querySelector('[data-editor-cancel]').addEventListener('click',()=>dialog.close());
    content.querySelector('form').addEventListener('submit',event=>{event.preventDefault();try{const selection=readScopeEditors(content);delete scopes[item.reference];Object.assign(scopes,selection);dialog.close();update();}catch(error){content.querySelector('#menu-editor-error').textContent=error.message;}});dialog.showModal();
   }));
   try{storage?.setItem(key,JSON.stringify({recipes:[...selectedRecipes],hosts:[...selectedHosts],meals:[...selectedMeals],scopes}));}catch{}
  };
  root.querySelectorAll('[data-dish]').forEach(input=>input.addEventListener('change',()=>{input.checked?selectedRecipes.add(input.dataset.dish):selectedRecipes.delete(input.dataset.dish);update();}));
  root.querySelectorAll('[data-set]').forEach(button=>button.addEventListener('click',()=>{selectedMeals.add(button.dataset.set);update();}));
  root.querySelectorAll('[data-host], [data-group], [data-all-hosts]').forEach(input=>input.addEventListener('change',()=>{selectedHosts=hostSelection(data,selectedHosts,input.hasAttribute('data-all-hosts')?'all':input.hasAttribute('data-group')?'group':'host',input.dataset.group||input.dataset.host,input.checked);update();}));
  root.querySelector('#recipe-preview')?.addEventListener('click',()=>onExecute?.({meals:[...selectedMeals],hosts:[...selectedHosts],recipes:[...selectedRecipes].map(reference=>({reference,vars:{},inputs:[],...(scopes[reference]?{inventory_selection:scopes[reference]}:{})}))}));
  root.querySelector('#recipe-profile')?.addEventListener('change',event=>onProfile(event.target.value));
  if(api&&profile){
   const dialog=root.querySelector('#menu-editor-dialog'),content=root.querySelector('#menu-editor-content');
   const open=html=>{content.innerHTML=html;content.querySelector('[data-editor-cancel]').addEventListener('click',()=>dialog.close());dialog.showModal();};
   const submit=handler=>async event=>{event.preventDefault();const button=event.submitter||event.target;button.disabled=true;try{const preferences=await handler();dialog.close();refresh(preferences);}catch(error){content.querySelector('#menu-editor-error').textContent=error.message;button.disabled=false;}};
   const editSet=saved=>{
    open(renderSetEditor(data,saved,e));
    content.querySelectorAll('[data-set-recipe]').forEach(input=>input.addEventListener('change',()=>{content.querySelectorAll('[data-set-scope]').forEach(section=>{if(section.dataset.setScope===input.value)section.hidden=!input.checked;});}));
    content.querySelector('#menu-set-form').addEventListener('submit',submit(()=>{
     const form=content.querySelector('#menu-set-form'),values=new FormData(form);
     return mutation('set.create',{title:values.get('title').trim(),description:values.get('description'),recipes:[...content.querySelectorAll('[data-set-recipe]:checked')].map(i=>i.value),meals:[...content.querySelectorAll('[data-set-meal]:checked')].map(i=>i.value),selections:Object.fromEntries(Object.entries(readScopeEditors(content,[...content.querySelectorAll('[data-set-recipe]:checked')].map(i=>i.value))).filter(([ref])=>[...content.querySelectorAll('[data-set-recipe]:checked')].some(i=>i.value===ref)))});
    }));
   };
   root.querySelector('#menu-save-plate')?.addEventListener('click',()=>editSet({title:'',description:'',recipes:[...selectedRecipes],meals:[...selectedMeals],selections:scopes}));
   root.querySelectorAll('[data-delete-set]').forEach(button=>button.addEventListener('click',()=>{const saved=data.user_sets.find(s=>s.id===button.dataset.deleteSet);open(renderSetDelete(saved,e,data));content.querySelector('#menu-delete-confirm').addEventListener('click',submit(()=>mutation('set.delete',{id:saved.id})));}));
   root.querySelector('#menu-categories')?.addEventListener('click',()=>{
    open(renderCategoryEditor(data.custom_categories||[],e));const form=content.querySelector('#menu-category-form');
    form.elements.namedItem('id').addEventListener('change',()=>{const category=data.custom_categories.find(c=>c.id===form.elements.namedItem('id').value);form.elements.namedItem('title').value=category?.title||'';form.elements.namedItem('description').value=category?.description||'';});
    form.addEventListener('submit',submit(()=>{const values=new FormData(form),id=values.get('id');return mutation(id?'category.update':'category.create',{...(id?{id}:{}),title:values.get('title').trim(),description:values.get('description')});}));
   });
  }
  update();
 };
 render();
}
