import {copy as c,renderDetail,renderRecords} from './locales/recipe-detail-zh-TW.mjs';
import {domains} from './locales/recipe-menu-zh-TW.mjs';
import {recipeDomains} from './recipe-menu-layout.mjs';
import {mountContent} from './recipe-content.mjs';
export {renderDetail,renderRecords};
export function defaultChanges(root,variables) {
 const changes={},remove=[];
 for(const variable of variables){
  if(!variable.editable)continue;
  const row=[...root.querySelectorAll('[data-option]')].find(el=>el.dataset.option===variable.name);
  if(!row.querySelector('[data-override]').checked){if(variable.configured)remove.push(variable.name);continue;}
  const raw=row.querySelector('[data-option-value]').value;
  changes[variable.name]=variable.definition.type==='string'?raw:JSON.parse(raw);
 }
 return {changes,remove};
}
export async function mountRecipeDetail(root,{profile,reference,e,api}) {
 root.innerHTML=`<p role="status">${e(c.loading)}</p>`;
 if(!profile){root.textContent=c.profileRequired;return;}
 let data,host='';
 const load=async()=>{
  data=await api('/api/v1/recipe-detail?'+new URLSearchParams({profile,reference,...(host?{host}:{})}));
  data.automatic_categories=recipeDomains(data.recipe);data.selected_host=host;
  const categories=[...Object.entries(domains).map(([id,title])=>({id,title})),...data.preferences.categories];
  root.innerHTML=renderDetail(data,categories,e);
  if(data.content)mountContent(root,data.content,{profile,reference,e,api,targets:{purpose:root.querySelector('#recipe-content'),readiness:root.querySelector('#recipe-readiness-content'),technical:root.querySelector('#recipe-technical-content')}});
  const execute=(selector,action,savedStatus='#recipe-detail-notice')=>root.querySelector(selector)?.addEventListener('submit',async event=>{
   event.preventDefault();const button=event.submitter||event.target.querySelector('[type=submit]');if(button)button.disabled=true;
   try{await action(event.target);await load();root.querySelector(savedStatus).textContent=c.saved;}catch(error){event.target.querySelector('[role="status"]').textContent=error.message||c.error;if(button)button.disabled=false;}
  });
  root.querySelectorAll('[data-option]').forEach(row=>row.querySelector('[data-override]').addEventListener('change',event=>{const value=row.querySelector('[data-option-value]');if(value)value.disabled=!event.target.checked;}));
  execute('#recipe-default-form',()=>api('/api/v1/recipe-detail/defaults',{profile,reference,expected_revision:data.defaults.revision,...defaultChanges(root,data.defaults.variables)}),'#recipe-default-status');
  const preference=(action,changes)=>api('/api/v1/recipe-menu/preferences',{profile,expected_revision:data.preferences.revision,action,changes});
  execute('#recipe-category-form',form=>preference('recipe.categories',{reference,categories:new FormData(form).getAll('categories')}));
  root.querySelector('#recipe-category-reset')?.addEventListener('click',async()=>{try{await preference('recipe.categories',{reference,categories:null});await load();}catch(error){root.querySelector('#recipe-category-status').textContent=error.message;}});
  root.querySelector('#recipe-record-host').addEventListener('change',event=>{host=event.target.value;void load();});
  wireRecords();
 };
 const wireRecords=()=>{
  root.querySelectorAll('[data-record]:not([data-wired])').forEach(details=>{details.dataset.wired='true';details.addEventListener('toggle',async()=>{
   if(!details.open)return;const content=details.querySelector('pre');content.textContent=c.recordLoading;
   try{const record=await api('/api/v1/recipe-detail/record?'+new URLSearchParams({profile,reference,record_id:details.dataset.record}));content.textContent=JSON.stringify(record,null,2);}catch(error){content.textContent=error.message;}
  },{once:true});});
  root.querySelector('[data-records-more]')?.addEventListener('click',async event=>{
   event.target.disabled=true;
   try{const next=await api('/api/v1/recipe-detail?'+new URLSearchParams({profile,reference,offset:event.target.dataset.recordsMore,...(host?{host}:{})}));event.target.remove();root.querySelector('#recipe-records').insertAdjacentHTML('beforeend',renderRecords(next.saved,e,profile,reference));wireRecords();}catch(error){event.target.textContent=error.message;event.target.disabled=false;}
  });
 };
 try{await load();}catch(error){root.innerHTML=`<p role="alert">${e(error.message||c.error)}</p>`;}
}
