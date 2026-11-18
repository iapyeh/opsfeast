// Only explicitly supported local destinations may follow a successful login.
export function loginDestination(search) {
  const next=new URLSearchParams(search).get('next');
  if(['/settings/profiles','/settings/site','/setup','/hosts'].includes(next))return next;
  const uuid='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
  if(typeof next==='string'&&new RegExp('^/console/'+uuid+'(?:/history)?(?:/blocks/'+uuid+')?(?:\\?[^#]*)?$').test(next)){
    const target=new URL(next,'http://local.invalid'),keys=[...target.searchParams.keys()];
    if(keys.every(key=>['profile','host_id'].includes(key))&&new Set(keys).size===keys.length)return next;
  }
  if(next==='/interactive'||(typeof next==='string'&&new RegExp('^/interactive\\?work='+uuid+'$').test(next)))return next;
  if(typeof next==='string'&&next.startsWith('/note-attachments?')){
    const target=new URL(next,'http://local.invalid'),keys=[...target.searchParams.keys()];
    if(!target.hash&&target.origin==='http://local.invalid'&&target.pathname==='/note-attachments'&&keys.length===4&&new Set(keys).size===4&&keys.every(key=>['profile','host_id','note_uuid','bundle_uuid'].includes(key)))return next;
  }
  if(typeof next==='string'&&next.startsWith('/hosts?')){
    const target=new URL(next,'http://local.invalid');
    if(target.origin==='http://local.invalid'&&target.pathname==='/hosts'&&
       [...target.searchParams.keys()].every(key=>['profile','host','view','new'].includes(key)))return target.pathname+target.search;
  }
  if(typeof next==='string'&&(next==='/logs'||next.startsWith('/logs?')||next==='/recipes'||next.startsWith('/recipes?')||next==='/recipe-plate'||next.startsWith('/recipe-plate?'))){
    const target=new URL(next,'http://local.invalid'), keys=[...target.searchParams.keys()];
    const allowed=target.pathname==='/recipes'?['profile','recipe','meal','q','source','status','category','kind']:target.pathname==='/recipe-plate'?['profile','add','meal','run','history','report','artifact']:['profile','entry','result'];
    if(target.origin==='http://local.invalid'&&['/logs','/recipes','/recipe-plate'].includes(target.pathname)&&!target.hash&&
       keys.every(key=>allowed.includes(key))&&new Set(keys).size===keys.length)return target.pathname+target.search;
  }
  return '/workspace';
}
