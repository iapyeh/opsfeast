import {mountAdminSettings} from './admin-settings.mjs';
import {mountSiteSettings} from './site-settings.mjs';

export function setupPhase(state) {
  if(!state||state.schema_version!=='0.1.0'||['admin_configured','authenticated','edit_unlocked','local_unlock_available'].some(key=>typeof state[key]!=='boolean'))return 'unavailable';
  if(state.admin_configured)return state.authenticated||state.edit_unlocked?'appearance':'login';
  if(state.edit_unlocked)return 'account';
  return state.local_unlock_available?'verify':'unavailable';
}
export function setupTokenFilename(port) {
  return `.opsfeast-web-edit-${/^\d+$/.test(String(port))&&+port>0&&+port<65536?+port:8740}.token`;
}
export function setupProgress(l,phase,e) {
  const active={verify:0,account:1,appearance:2,done:3,login:2,unavailable:0}[phase];
  return `<ol class="setup-progress" aria-label="${e(l.title)}">${l.steps.map((name,index)=>`<li${index===active?' aria-current="step"':''} class="${index<active?'complete':''}"><span>${index<active?'✓':index+1}</span><div>${e(name)}${index===2?`<small>${e(l.optional)}</small>`:''}</div></li>`).join('')}</ol>`;
}
export async function mountFirstUse(container,{m,e,origin,port}) {
  const l=m.firstUse;
  let context;
  const request=async(path,options={})=>{
    const response=await fetch(path,options);
    if(!response.ok){const error=new Error('setup_request_failed');error.status=response.status;throw error;}
    return response.json();
  };
  const panel=(phase,title,intro,content)=>{
    container.innerHTML=setupProgress(l,phase,e)+`<section class="setup-panel panel"><h2 tabindex="-1">${e(title)}</h2><p class="setup-intro">${e(intro)}</p>${content}</section><p class="setup-privacy">${e(l.privacy)}</p>`;
    container.querySelector('h2').focus();
  };
  const status=(node,text)=>{node.textContent=text;node.focus();};
  const finish=()=>panel('done',l.doneTitle,l.doneIntro,`<a class="button primary" href="${context.authenticated?'/workspace':'/login'}">${e(context.authenticated?l.openWorkspace:l.signIn)} →</a>`);
  async function appearance(){
    panel('appearance',l.appearanceTitle,l.appearanceIntro,'<div id="setup-appearance"></div>'+`<div class="setup-actions"><button id="setup-skip" class="button" type="button">${e(l.skip)}</button><button id="setup-reverify" class="text-button" type="button">${e(l.reverify)}</button></div>`);
    container.querySelector('#setup-skip').addEventListener('click',finish);
    container.querySelector('#setup-reverify').addEventListener('click',verify);
    try{
      const site=await request('/api/v1/site');
      const editor=container.querySelector('#setup-appearance');
      mountSiteSettings(editor,{m,e,site,siteName:site.site_name||m.site.defaultName,authState:{configured:true,authenticated:context.authenticated},appearanceOnly:true,onSaved:finish});
      editor.querySelector('#save-site').textContent=l.finish;
      editor.querySelector('.site-save-bar .field-hint').textContent=l.appearanceSaveHint;
    }catch{panel('unavailable',l.unavailable,'',`<button id="setup-retry" class="button" type="button">${e(l.retry)}</button>`);container.querySelector('#setup-retry').addEventListener('click',start);}
  }
  async function account(){
    panel('account',l.accountTitle,l.accountIntro,`<p class="field-hint">${e(l.accountNext)}</p><div id="setup-account"></div><button id="setup-end" class="text-button" type="button">${e(l.endVerification)}</button>`);
    container.querySelector('#setup-end').addEventListener('click',async()=>{await request('/api/v1/site/lock',{method:'POST'});await start();});
    await mountAdminSettings(container.querySelector('#setup-account'),{m,e,request,onSaved:start});
  }
  function verify(){
    const filename=setupTokenFilename(port);
    const prompt=l.agentPrompt.replace('{origin}',origin).replace('{filename}',filename);
    panel('verify',l.verifyTitle,l.verifyIntro,`<div class="setup-help"><h3>${e(l.agentTitle)}</h3><p>${e(l.agentHint)}</p><textarea id="setup-agent-prompt" readonly aria-label="${e(l.copy)}">${e(prompt)}</textarea><button id="setup-copy" class="button" type="button">${e(l.copy)}</button><p id="setup-copy-status" role="status"></p></div><details class="setup-manual"><summary>${e(l.manual)}</summary><ol>${l.manualSteps.map(step=>`<li>${e(step)}</li>`).join('')}</ol><code>${e(filename)}</code></details><form id="setup-verify-form"><label for="setup-token">${e(l.tokenLabel)}</label><input id="setup-token" type="password" autocomplete="off" required><button class="button primary" id="setup-verify" type="submit">${e(l.verify)} →</button><p id="setup-status" class="admin-result" role="status" tabindex="-1"></p></form>`);
    container.querySelector('#setup-copy').addEventListener('click',async()=>{
      try{await navigator.clipboard.writeText(prompt);container.querySelector('#setup-copy-status').textContent=l.copied;}
      catch{container.querySelector('#setup-agent-prompt').select();container.querySelector('#setup-copy-status').textContent=l.copyFailed;}
    });
    container.querySelector('#setup-verify-form').addEventListener('submit',async event=>{
      event.preventDefault();
      const input=container.querySelector('#setup-token'),button=container.querySelector('#setup-verify'),message=container.querySelector('#setup-status');
      if(!input.value.trim()){status(message,l.tokenMissing);return;}
      button.disabled=true;button.textContent=l.verifying;
      try{
        const authorization='Bearer '+input.value.trim();input.value='';
        await request('/api/v1/site/unlock',{method:'POST',headers:{Authorization:authorization}});
        await start();
      }catch(error){status(message,error.status===401||error.status===403?l.invalidToken:l.unavailable);button.disabled=false;button.textContent=l.verify;}
    });
  }
  async function start(){
    try{
      context=await request('/api/v1/setup');
      const phase=setupPhase(context);
      if(phase==='verify')verify();
      else if(phase==='account')await account();
      else if(phase==='appearance')await appearance();
      else if(phase==='login')panel('login',l.loginTitle,l.loginIntro,`<a class="button primary" href="/login?next=%2Fsetup">${e(l.loginContinue)} →</a>`);
      else throw new Error('setup_unavailable');
    }catch{
      panel('unavailable',context?.local_unlock_available===false&&!context?.admin_configured?l.noUnlock:l.unavailable,'',`<button id="setup-retry" class="button" type="button">${e(l.retry)}</button>`);
      container.querySelector('#setup-retry').addEventListener('click',start);
    }
  }
  container.textContent=l.loading;
  await start();
}
