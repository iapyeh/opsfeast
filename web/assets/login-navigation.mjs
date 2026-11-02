// Only explicitly supported local destinations may follow a successful login.
export function loginDestination(search) {
  const next=new URLSearchParams(search).get('next');
  if(['/settings/profiles','/settings/site','/setup','/hosts'].includes(next))return next;
  const uuid='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
  if(typeof next==='string'&&new RegExp('^/console/'+uuid+'(?:/blocks/'+uuid+')?$').test(next))return next;
  if(next==='/interactive'||(typeof next==='string'&&new RegExp('^/interactive\\?work='+uuid+'$').test(next)))return next;
  if(typeof next==='string'&&next.startsWith('/hosts?')){
    const target=new URL(next,'http://local.invalid');
    if(target.origin==='http://local.invalid'&&target.pathname==='/hosts'&&
       [...target.searchParams.keys()].every(key=>['profile','host','view','new'].includes(key)))return target.pathname+target.search;
  }
  return '/workspace';
}
