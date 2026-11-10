import {copy as c} from './locales/report-viewer-zh-TW.mjs';
import {formatDateTime} from './i18n.mjs';
const url=(path,args)=>path+'?'+new URLSearchParams(args);
const time=value=>{try{return value?formatDateTime(value):c.unknown;}catch{return c.unknown;}};
export function artifactUrl(profile,result_id,name,mode='text') {return url('/api/v1/reports/artifact',{profile,result_id,name,mode});}
export function renderReportList(data,{e,profile}) {
 return (data.status==='partial'?`<p role="status">${e(c.partial)}</p>`:'')+(data.items?.length?data.items.map(r=>`<p><a href="${e(url('/recipes',{profile,report:r.result_id}))}">${e(time(r.started_at))} · ${e(r.recipe_reference)} · ${e(c.states[r.status]||r.status)}</a></p>`).join(''):`<p>${e(c.empty)}</p>`)+(data.next_offset!=null?`<button type="button" class="button" data-reports-more="${e(data.next_offset)}">${e(c.more)}</button>`:'');
}
export function renderReport(report,{e,profile,artifact}) {
 const meta=report.artifacts.find(a=>a.path===artifact)||(!artifact?report.artifacts[0]:null);
 let html=`<a href="${e(url('/recipes',{profile}))}">← ${e(c.back)}</a><div class="page-heading"><div><h1>${e(c.title)}</h1><p>${e(report.recipe_reference)}</p><p>${e(c.status)}：${e(c.states[report.status]||report.status)} · ${e(c.generated)}：${e(time(report.completed_at||report.started_at))}</p></div></div><p class="field-hint">${e(c.verified)}</p><div class="recipe-actions">${report.artifacts.map(a=>`<a class="button" href="${e(url('/recipes',{profile,report:report.result_id,artifact:a.path}))}">${e(a.title||a.path)} · ${e(a.path)}</a>`).join('')}</div>`;
 if(!meta)return html+`<p role="status">${e(artifact?c.invalid:c.noArtifacts)}</p>`;
 html+=`<section class="panel report-artifact"><h2>${e(meta.title||meta.path)}</h2><p>${e(meta.path)} · ${e(meta.media_type)} · ${e(meta.size_bytes)} bytes</p><div class="recipe-actions"><a class="button" href="${e(artifactUrl(profile,report.result_id,meta.path,'download'))}" download>${e(c.download)}</a></div><details><summary>${e(c.integrity)}</summary><pre>${e(meta.sha256)}</pre></details>`;
 if(meta.media_type==='text/html')html+=`<p>${e(c.htmlNote)}</p><iframe title="${e(c.preview+' · '+meta.title)}" sandbox="" referrerpolicy="no-referrer" src="${e(artifactUrl(profile,report.result_id,meta.path,'preview'))}" class="report-preview"></iframe><details id="report-source"><summary>${e(c.source)}</summary><pre id="report-text"></pre></details>`;
 else if(['image/png','image/jpeg','image/gif','image/webp'].includes(meta.media_type))html+=`<img class="report-image" alt="${e(meta.title)}" src="${e(artifactUrl(profile,report.result_id,meta.path,'preview'))}">`;
 else if(meta.media_type.startsWith('text/')||['application/json','image/svg+xml','application/xml'].includes(meta.media_type))html+=`<p>${e(c.rawNote)}</p><pre id="report-text"></pre>`;
 else html+=`<p>${e(c.downloadOnly)}</p>`;
 return html+'</section>';
}
export async function mountReportViewer(root,{e,profile,identifier,artifact,api}) {
 root.innerHTML=`<p role="status">${e(c.loading)}</p>`;
 try {
  const report=await api(url('/api/v1/reports/result',{profile,result_id:identifier}));
  root.innerHTML=renderReport(report,{e,profile,artifact});
  const meta=report.artifacts.find(a=>a.path===artifact)||(!artifact?report.artifacts[0]:null);
  const read=async()=>{
   const target=root.querySelector('#report-text');if(!target||!meta)return;
   try {const data=await api(artifactUrl(profile,report.result_id,meta.path));target.textContent=data.content;}
   catch {target.textContent=c.unavailable;}
  };
  if(meta?.media_type==='text/html')root.querySelector('#report-source').addEventListener('toggle',event=>{if(event.target.open)void read();},{once:true});
  else await read();
 }catch {root.innerHTML=`<p role="alert">${e(c.unavailable)}</p><a href="${e(url('/recipes',{profile}))}">${e(c.back)}</a>`;}
}
