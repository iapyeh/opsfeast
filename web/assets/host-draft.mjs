import c from './locales/host-draft-zh-TW.mjs';
import {pinLogin,moveUser,chooseLogin,seedHost,recipeCatalog,hostRecords,hostLogUrl} from './host-model.mjs';
export const hostCopy=c;
const drafts=new Map();
export function hostUrl(id,view='summary',extra={}) {
  return '/hosts?'+new URLSearchParams({host:id,view,...extra});
}
export function hostRowsHtml(rows,e) {
  return rows.map(row=>`<tr><td><a class="record-time" href="${e(hostUrl(row[0]))}">${e(row[0])}</a></td><td>${e(row[1])}</td><td>${e(row[2])}</td><td class="host-ip">${e(row[3])}</td><td class="summary-cell">${e([!row[4]?c.disabled:'',row[5]].filter(Boolean).join('；'))}</td></tr>`).join('');
}
export function mountHostDraft(root,{query,e,heading,setBreadcrumb}) {
  const id=query.get('host'),row=c.rows.find(row=>row[0]===id),view=query.get('view')||'summary';
  const base=[{label:c.listTitle,url:'/hosts'},{label:id,url:hostUrl(id)}];
  if(!row||!c.tabs.some(([key])=>key===view)){
    setBreadcrumb([{label:c.listTitle,url:'/hosts'},{label:c.unavailable}]);root.innerHTML=heading(c.title,c.unavailable);return;
  }
  if(!drafts.has(id))drafts.set(id,seedHost(row));
  const state=drafts.get(id),label=c.tabs.find(([key])=>key===view)[1];
  const field=(name,label,value,extra='')=>`<label>${e(label)}<input name="${e(name)}" value="${e(value)}" ${extra}></label>`;
  const toggle=(name,label,checked,locked=false)=>`<label class="draft-toggle"><input name="${e(name)}" type="checkbox" ${checked?'checked':''} ${locked?'disabled':''}>${e(label)}</label>`;
  const disabled=labels=>`<div class="roadmap-actions">${labels.map(label=>`<button type="button" class="button" disabled>${e(label)}</button>`).join('')}</div>`;
  const nav=`<nav class="draft-tabs" aria-label="${e(c.title)}">${c.tabs.map(([key,label])=>`<a href="${e(hostUrl(id,key))}" ${view===key?'aria-current="page"':''}>${e(label)}</a>`).join('')}</nav>`;
  function route(extra,labelExtra){
    const url=hostUrl(id,view,extra);
    if(typeof history!=='undefined')history.replaceState(null,'',url);
    setBreadcrumb([...base,{label,...(labelExtra?{url:hostUrl(id,view)}:{})},...(labelExtra?[{label:labelExtra}]:[])]);
  }
  setBreadcrumb([...base,{label}]);
  root.innerHTML=heading(id,c.intro)+`<p class="detail-note">${e(c.draft)}</p>${nav}<div id="host-content" class="host-draft"></div>`;
  const content=root.querySelector('#host-content');
  const records=source=>{
    const rows=hostRecords(id).filter(record=>record.source===source);
    const cols=source==='recipe'?[c.time,c.recipe,c.status]:[c.time,c.summary];
    return `<p class="field-hint">${e(c.timezone)}</p><div class="table-scroll"><table class="roadmap-table"><thead><tr>${cols.map(x=>`<th scope="col">${e(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(record=>`<tr><td><a class="record-time" href="${e(hostLogUrl(record))}">${e(record.time)}</a></td>${source==='recipe'?`<td>${e(record.recipe)}</td><td>${e(record.status)}</td>`:`<td>${e(record.summary)}</td>`}</tr>`).join('')}</tbody></table></div>`;
  };
  if(view==='summary'){
    content.innerHTML=`<section class="panel roadmap-section"><h2>${e(c.summaryTitle)}</h2><p>${e(c.summaryNote)}</p>${row[3]?`<p>${e(c.sampleTime)}：2026-10-31 08:10:05 · Asia/Taipei</p><dl class="log-metadata">${[...c.summaryValues,row[3]].map((value,i)=>`<dt>${e(c.summaryLabels[i])}</dt><dd>${e(value)}</dd>`).join('')}</dl>`:`<p>${e(c.noInventory)}</p>`}</section>`;return;
  }
  if(view==='console'){
    if(query.get('session')==='new'){
      route({session:'new'},c.newConsole);
      content.innerHTML=`<section class="panel roadmap-section"><h2>${e(c.newSession)}</h2><p>${e(c.consoleNote)}</p><span class="subtle-tag">${e(c.notConnected)}</span><dl class="log-metadata"><dt>${e(c.target)}</dt><dd>${e(id)}.example.invalid:22</dd><dt>${e(c.identityLabel)}</dt><dd>${e(state.users.find(user=>user.login).name)}</dd></dl>${disabled([c.connect,c.disconnect,c.stop])}<pre class="log-content">${e(c.lines.join('\n'))}</pre><label>${e(c.command)}<input disabled placeholder="${e(c.placeholder)}"></label></section>`;
    }else content.innerHTML=`<section class="panel roadmap-section"><div class="panel-heading"><h2>${e(c.consoleHistory)}</h2><a class="button primary" href="${e(hostUrl(id,'console',{session:'new'}))}">${e(c.newConsole)}</a></div>${records('interactive')}</section>`;
    return;
  }
  if(view==='settings')renderSettings();
  if(view==='recipes')renderRecipes();
  function renderSettings(editor=null){
    content.innerHTML=`<section class="panel roadmap-section"><h2>${e(c.connection)}</h2><div class="draft-grid">${field('endpoint',c.endpoint,state.connection.endpoint)}${field('port',c.port,state.connection.port,'type="number" min="1" max="65535"')}${field('group',c.group,state.connection.group)}</div>${toggle('host_enabled',c.enable,state.connection.enabled)}${disabled([c.save,c.hostInit,c.connectionTest])}</section><section class="panel roadmap-section"><div class="panel-heading"><h2>${e(c.users)}</h2><button class="button" type="button" id="user-add">${e(c.add)}</button></div><p>${e(c.loginRule)}</p><div class="table-scroll"><table class="roadmap-table"><thead><tr>${[c.username,c.loginUser,'sudo',c.actions].map(label=>`<th>${e(label)}</th>`).join('')}</tr></thead><tbody>${state.users.map((user,index)=>`<tr><td>${e(user.name)}</td><td>${user.login?'✓':''}</td><td>${user.sudo?'✓':''}</td><td><div class="host-row-actions"><button type="button" class="button" data-user-edit="${e(user.id)}">${e(c.edit)}</button><button type="button" class="button" data-user-delete="${e(user.id)}" ${user.login?'disabled':''}>${e(c.remove)}</button><button type="button" class="button" data-user-up="${e(user.id)}" ${index<=1?'disabled':''}>${e(c.up)}</button><button type="button" class="button" data-user-down="${e(user.id)}" ${user.login||index===state.users.length-1?'disabled':''}>${e(c.down)}</button></div></td></tr>`).join('')}</tbody></table></div><div id="user-editor"></div></section>`;
    for(const key of ['endpoint','port','group'])content.querySelector(`[name="${key}"]`).oninput=event=>{state.connection[key]=event.target.value;};
    content.querySelector('[name="host_enabled"]').onchange=event=>{state.connection.enabled=event.target.checked;};
    content.querySelector('#user-add').onclick=()=>openUser(null);
    content.querySelectorAll('[data-user-edit]').forEach(button=>button.onclick=()=>openUser(button.dataset.userEdit));
    content.querySelectorAll('[data-user-delete]').forEach(button=>button.onclick=()=>{state.users=state.users.filter(user=>user.login||user.id!==button.dataset.userDelete);route({});renderSettings();});
    for(const [attribute,direction] of [['up',-1],['down',1]])content.querySelectorAll(`[data-user-${attribute}]`).forEach(button=>button.onclick=()=>{state.users=moveUser(state.users,button.dataset[attribute==='up'?'userUp':'userDown'],direction);route({});renderSettings();});
    if(editor)openUser(editor==='new'?null:editor,false);
  }
  function openUser(userId,update=true){
    const user=state.users.find(user=>user.id===userId)||{name:'',sudo:false,login:false};
    if(update)route({edit:userId||'new'},userId?c.userEdit:c.userAdd);
    const panel=content.querySelector('#user-editor');
    panel.innerHTML=`<form id="user-form" class="draft-editor"><h3>${e(userId?c.userEdit:c.userAdd)}</h3>${field('username',c.username,user.name,'required maxlength="64"')}${toggle('login',c.loginUser,user.login,user.login)}${toggle('sudo',c.sudoUser,user.sudo)}<label>${e(c.auth)}<select name="authentication">${c.authOptions.map((label,index)=>`<option value="${index}" ${String(user.authentication||0)===String(index)?'selected':''}>${e(label)}</option>`).join('')}</select></label>${field('key_source',c.key,user.key_source||'')}<p>${e(c.secrets)}</p>${disabled([c.suTest,c.sudoTest])}<p id="user-error" role="status"></p><div class="roadmap-actions"><button type="submit" class="button primary">${e(c.saveDraft)}</button><button type="button" class="button" id="user-cancel">${e(c.cancel)}</button></div></form>`;
    panel.querySelector('#user-cancel').onclick=()=>{route({});renderSettings();};
    panel.querySelector('#user-form').onsubmit=event=>{
      event.preventDefault();const form=event.currentTarget,name=form.elements.username.value.trim();
      if(!name||state.users.some(item=>item.id!==userId&&item.name===name)){panel.querySelector('#user-error').textContent=c.invalidUser;return;}
      const login=form.elements.login.checked||user.login,idNew=userId||'user-'+Date.now();
      const changed={id:idNew,name,sudo:form.elements.sudo.checked,login,authentication:form.elements.authentication.value,key_source:form.elements.key_source.value};
      state.users=userId?state.users.map(item=>item.id===userId?changed:item):[...state.users,changed];
      state.users=login?chooseLogin(state.users,idNew):pinLogin(state.users);
      route({});renderSettings();
    };
  }
  function renderRecipes(edit=null){
    content.innerHTML=`<section class="panel roadmap-section"><h2>${e(c.recipeHistory)}</h2>${records('recipe')}</section><section class="panel roadmap-section"><div class="panel-heading"><h2>${e(c.configured)}</h2><button class="button" type="button" id="recipe-add">${e(c.add)}</button></div><div id="configured-recipes">${state.recipes.map((recipe,index)=>`<article class="configured-recipe"><h3>${e(recipe.id)}</h3><p>${e(recipe.enabled?c.enabled:c.disabled)}</p><dl class="log-metadata">${Object.entries(recipe.values).map(([key,value])=>`<dt>${e(c.fields[key]||key)}</dt><dd>${e(value)}</dd>`).join('')}</dl><div class="roadmap-actions"><button class="button" type="button" data-recipe-edit="${index}">${e(c.edit)}</button><button class="button" type="button" data-recipe-delete="${index}">${e(c.remove)}</button></div></article>`).join('')||`<p>${e(c.noRecipes)}</p>`}</div><div id="recipe-editor"></div></section>`;
    content.querySelector('#recipe-add').onclick=()=>openRecipe(null);
    content.querySelectorAll('[data-recipe-edit]').forEach(button=>button.onclick=()=>openRecipe(Number(button.dataset.recipeEdit)));
    content.querySelectorAll('[data-recipe-delete]').forEach(button=>button.onclick=()=>{state.recipes.splice(Number(button.dataset.recipeDelete),1);route({});renderRecipes();});
    if(edit!==null)openRecipe(edit==='new'?null:Number(edit),false);
  }
  function openRecipe(index,update=true){
    const existing=index===null?null:state.recipes[index];
    if(index!==null&&!existing)return;
    if(update)route({edit:index===null?'new':String(index)},existing?c.editRecipe:c.addRecipe);
    const panel=content.querySelector('#recipe-editor');
    panel.innerHTML=`<form id="recipe-form" class="draft-editor"><h3>${e(existing?c.editRecipe:c.addRecipe)}</h3><label>${e(c.recipeSearch)}<input name="recipe" list="recipe-options" autocomplete="off" value="${e(existing?.id||'')}" ${existing?'readonly':''} required><datalist id="recipe-options">${recipeCatalog.map(recipe=>`<option value="${e(recipe.id)}"></option>`).join('')}</datalist></label><p>${e(c.recipeChoose)}</p><div id="recipe-fields"></div><p id="recipe-error" role="status"></p><div class="roadmap-actions"><button class="button primary" id="recipe-save" type="submit" disabled>${e(c.saveDraft)}</button><button class="button" id="recipe-cancel" type="button">${e(c.cancel)}</button></div></form>`;
    const form=panel.querySelector('#recipe-form');
    const fields=()=>{
      const definition=recipeCatalog.find(recipe=>recipe.id===form.elements.recipe.value);
      panel.querySelector('#recipe-save').disabled=!definition;
      panel.querySelector('#recipe-fields').innerHTML=definition?`<h3>${e(c.recipeParameters)}</h3><p>${e(c.recipeSchemaNote)}</p>${toggle('recipe_enabled',c.recipeEnable,existing?.enabled??true)}${definition.fields.map(([key,type,defaultValue])=>type==='checkbox'?toggle(key,c.fields[key],existing?.values[key]??defaultValue):field(key,c.fields[key],existing?.values[key]??defaultValue,`type="${type}" required`)).join('')}`:'';
    };
    form.elements.recipe.addEventListener('input',fields);fields();
    panel.querySelector('#recipe-cancel').onclick=()=>{route({});renderRecipes();};
    form.onsubmit=event=>{
      event.preventDefault();const definition=recipeCatalog.find(recipe=>recipe.id===form.elements.recipe.value);if(!definition)return;
      if(state.recipes.some((recipe,i)=>recipe.id===definition.id&&i!==index)){panel.querySelector('#recipe-error').textContent=c.recipeDuplicate;return;}
      const recipe={id:definition.id,enabled:form.elements.recipe_enabled.checked,values:Object.fromEntries(definition.fields.map(([key,type])=>[key,type==='checkbox'?form.elements[key].checked:form.elements[key].value]))};
      if(index===null)state.recipes.push(recipe);else state.recipes[index]=recipe;
      route({});renderRecipes();
    };
  }
  if(query.has('edit')){
    if(view==='settings'){openUser(query.get('edit')==='new'?null:query.get('edit'));}
    if(view==='recipes')openRecipe(query.get('edit')==='new'?null:Number(query.get('edit')));
  }
}
