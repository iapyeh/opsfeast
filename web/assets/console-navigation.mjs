// Reader identity comes from the URL's session, never a global current Console.
export function readerLocation(pathname){
  const parts=pathname.split('/'),history=parts[3]==='history';
  const index=history?4:3;
  return {sid:decodeURIComponent(parts[2]),history,bid:parts[index]==='blocks'?decodeURIComponent(parts[index+1]):null};
}
export function readerLink(sid,{history=false,bid=null,scope=null}={}){
  const query=scope?'?'+new URLSearchParams(scope):'';
  return '/console/'+encodeURIComponent(sid)+(history?'/history':'')+(bid?'/blocks/'+encodeURIComponent(bid):'')+query;
}
export function readerScope(session,search){
  const query=new URLSearchParams(search),profile=query.get('profile'),host_id=query.get('host_id');
  // Context is a navigation hint only. Reject mismatches instead of relabelling evidence.
  return profile&&host_id&&session.host_id===profile+' / '+host_id?{profile,host_id}:null;
}
export function contentWindow(block,offset,history){
  return history?Math.max(0,Math.min(16384,block.size-offset)):16384;
}
