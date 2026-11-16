// Settings may inspect other owners; daily work is pinned to the saved default.
export function operationalSearch(path,search,defaultProfile) {
  if(path.startsWith('/settings')||!defaultProfile)return search;
  const query=new URLSearchParams(search),requested=query.get('profile');
  if(requested&&requested!==defaultProfile)return '';
  query.delete('profile');return query.size?'?'+query:'';
}
export function pinnedFetch(fetchImpl,profile,{origin,onChanged=()=>{}}) {
  return async(input,options={})=>{
    const target=new URL(typeof input==='string'?input:input.url,origin);
    if(target.origin!==origin||!target.pathname.startsWith('/api/v1/'))return fetchImpl(input,options);
    const headers=new Headers(options.headers||(typeof input==='object'?input.headers:undefined));
    headers.set('X-OpsFeast-Default-Profile',encodeURIComponent(profile));
    const response=await fetchImpl(input,{...options,headers});
    if(response.status===409){
      try{if((await response.clone().json()).detail==='default_profile_changed_reload')onChanged();}catch{}
    }
    return response;
  };
}
