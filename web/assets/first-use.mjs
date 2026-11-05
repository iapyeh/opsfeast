import {mountSiteSettings} from './site-settings.mjs';

export function setupPhase(state) {
  if(!state||state.schema_version!=='0.1.0'||['admin_configured','authenticated','agent_control_available'].some(key=>typeof state[key]!=='boolean'))return 'unavailable';
  if(state.admin_configured)return state.authenticated?'appearance':'login';
  return state.agent_control_available?'verify':'unavailable';
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
  function verify(){
    const prompt=l.agentPrompt.replace('{origin}',origin);
    panel('verify',l.verifyTitle,l.verifyIntro,`<div class="setup-help"><h3>${e(l.agentTitle)}</h3><p>${e(l.agentHint)}</p><textarea id="setup-agent-prompt" readonly aria-label="${e(l.copy)}">${e(prompt)}</textarea><button id="setup-copy" class="button" type="button">${e(l.copy)}</button><p id="setup-copy-status" role="status"></p></div><button id="setup-recheck" class="button primary" type="button">${e(l.reverify)}</button>`);
    container.querySelector('#setup-copy').addEventListener('click',async()=>{
      try{await navigator.clipboard.writeText(prompt);container.querySelector('#setup-copy-status').textContent=l.copied;}
      catch{container.querySelector('#setup-agent-prompt').select();container.querySelector('#setup-copy-status').textContent=l.copyFailed;}
    });
    container.querySelector('#setup-recheck').addEventListener('click',start);
  }
  async function start(){
    try{
      context=await request('/api/v1/setup');
      const phase=setupPhase(context);
      if(phase==='verify')verify();
      else if(phase==='appearance')await appearance();
      else if(phase==='login')panel('login',l.loginTitle,l.loginIntro,`<a class="button primary" href="/login?next=%2Fsetup">${e(l.loginContinue)} →</a>`);
      else throw new Error('setup_unavailable');
    }catch{
      panel('unavailable',context?.agent_control_available===false&&!context?.admin_configured?l.noUnlock:l.unavailable,'',`<button id="setup-retry" class="button" type="button">${e(l.retry)}</button>`);
      container.querySelector('#setup-retry').addEventListener('click',start);
    }
  }
  container.textContent=l.loading;
  await start();
}
