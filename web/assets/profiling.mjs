import c from './locales/profiling-zh-TW.mjs';
import {formatDateTime} from './i18n.mjs';

export function profilingUrl(profile,host_id,offset=0) {
  return '/api/v1/profiling/host?'+new URLSearchParams({profile,host_id,offset:String(offset),limit:'250'});
}

export function renderProfiling(data,{e}) {
  const time=value=>value&&!Number.isNaN(Date.parse(value))?formatDateTime(value):value||c.noSource;
  const state=value=>c.states[value]||value;
  const row=item=>{
    const sources=item.evidence.length?item.evidence:[null];
    return sources.map(source=>{
      const values=source?.samples||[];
      const value=source?(values.length?values.map(sample=>`<div>${Object.keys(sample.keys||{}).length?`<code>${e(JSON.stringify(sample.keys))}</code>`:''}${sample.basis?`<p class="field-hint">${e(c.basis)}: ${e(c.bases[sample.basis]||sample.basis)}</p>`:''}<pre class="log-content">${e(sample.status==='success'?sample.value_preview:sample.reason_code||c.states.unavailable)}</pre>${sample.status==='success'&&source.definition?.unit?`<p class="field-hint">${e(c.unit)}: ${e(source.definition.unit)}</p>`:''}${sample.value_truncated?`<p class="field-hint">${e(c.preview)}</p>`:''}</div>`).join(''):e(source.state==='complete'?c.emptyEnumeration:c.states.unavailable)):e(c.noSource);
      return `<tr><th scope="row"><code>${e(item.property_id)}</code>${source?`<p>${e(source.namespace)} · ${e(source.recipe_reference)}${source.instance?` · ${e(source.instance)}`:''}</p>`:''}</th><td>${e(state(source?.state||item.state))}</td><td>${value}${source?.reason_codes?.length?`<p>${e(c.reason)}: ${e(source.reason_codes.join(', '))}</p>`:''}${source?.samples_truncated?`<p>${e(c.preview)}</p>`:''}${source?.source_scope||source?.commands?.length?`<details><summary>${e(c.scopeEvidence)}</summary><p>${e(source.source_scope||'')}</p><pre class="log-content">${e(JSON.stringify(source.commands||[],null,2))}</pre></details>`:''}${source?.routine_evidence?.length?`<details><summary>Routine 權限與身分證據</summary><pre class="log-content">${e(JSON.stringify({routines:source.routine_evidence,connection:source.connection_evidence},null,2))}</pre></details>`:''}${source?`<details><summary>${e(c.record)}</summary><code>${e(source.record_id)}</code><p>${e(c.definition)}</p><pre class="log-content">${e(JSON.stringify(source.definition,null,2))}</pre></details>`:''}</td><td>${e(time(source?.observed_at))}</td></tr>`;
    }).join('');
  };
  return `<p>${e(c.intro)}</p><p class="field-hint">${e(c.limits)}</p><p>${e(c.integrationNote)}</p>${data.retained_record_count===0?`<p role="status">${e(c.empty)}</p>`:''}`+
    data.domains.map(domain=>`<section class="panel roadmap-section"><h2>${e(c.domains[domain.id]||domain.title)}</h2>${data.capabilities.filter(cap=>cap.domain===domain.id).map(cap=>{
      const items=data.items.filter(item=>item.capability_id===cap.id),counts=cap.evidence_counts;
      return `<details class="roadmap-section"><summary>${e(c.capabilities[cap.id]||cap.title)} · ${e(cap.integration==='not_integrated'?c.notIntegrated:c.integrated)}</summary>${counts?`<p class="field-hint">${e(c.counts)}: ${['complete','partial','unavailable','not_collected'].map(key=>e(counts[key])).join(' / ')}</p>`:''}<details><summary>${e(c.sourceScope)}</summary><p>${e(cap.scope_note)}</p></details>${items.length?`<div class="table-scroll"><table class="roadmap-table"><thead><tr>${c.columns.map(label=>`<th scope="col">${e(label)}</th>`).join('')}</tr></thead><tbody>${items.map(row).join('')}</tbody></table></div>`:''}</details>`;
    }).join('')}</section>`).join('');
}

export async function mountProfiling(root,{profile,host_id,e,request}) {
  root.innerHTML=`<h2>${e(c.title)}</h2><div id="profiling-content"><p role="status">${e(c.loading)}</p></div><p id="profiling-status" role="status"></p><button id="profiling-more" type="button" class="button" hidden>${e(c.more)}</button><button id="profiling-retry" type="button" class="button" hidden>${e(c.retry)}</button>`;
  const content=root.querySelector('#profiling-content'),status=root.querySelector('#profiling-status'),more=root.querySelector('#profiling-more'),retry=root.querySelector('#profiling-retry');
  let data=null,busy=false;
  async function load(offset=0) {
    if(busy)return;
    busy=true;more.disabled=true;retry.hidden=true;status.textContent=c.loading;
    try {
      const page=await request(profilingUrl(profile,host_id,offset));
      data={...page,items:offset&&data?[...data.items,...page.items]:page.items};
      content.innerHTML=renderProfiling(data,{e});
      status.textContent='';more.hidden=data.next_offset===null;
    }catch(error){status.textContent=error.status===401?c.login:c.unavailable;retry.hidden=false;}
    finally{busy=false;more.disabled=false;}
  }
  more.addEventListener('click',()=>void load(data.next_offset));
  retry.addEventListener('click',()=>void load());
  await load();
}
