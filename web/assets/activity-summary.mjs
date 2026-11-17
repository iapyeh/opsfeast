import c from './locales/workspace-zh-TW.mjs';
import {workspaceUrl} from './workspace-url.mjs';
const state=value=>c.states[value]||value||c.unknown;
export function renderActivitySummary(item,{e,profile}) {
  const summary=item.summary;
  if(!summary)return '';
  const reason=value=>{
    if(!value)return '未提供具體原因';
    const [code,...scope]=String(value).split(':');
    const label=c.activityReasons[code]||c.reasons[code]||code;
    return label+(scope.length?'（'+scope.join(':')+'）':'');
  };
  const receipt=value=>({stored:'已保存',success:'成功',failed:'失敗',skipped:'略過'})[value]||state(value||'unknown');
  return `<section class="activity-summary">${!summary.total_hosts&&item.status!=='success'?'<p>紀錄未提供主機層級的未完成原因。</p>':''}<p>主機：完成 ${e(summary.completed_hosts)} ／ 未完成 ${e(summary.incomplete_hosts)} ／ 共 ${e(summary.total_hosts)} 台</p>${summary.issues.map(issue=>`<article><h3>${e(issue.host_id||c.unknown)} · ${e(state(issue.status))}</h3>${issue.stages?.length?`<ul>${issue.stages.map(stage=>`<li><strong>${e(c.activityStages[stage.stage]||stage.stage)}</strong>：${e(state(stage.status))}${stage.status==='success'?'':' · '+e(reason(stage.reason_code))}</li>`).join('')}</ul>`:`<p>${e(reason(issue.reason_code))}</p>`}${issue.packages?`<p>套件採集：${e(issue.packages.collected_count??'未知')} 筆${issue.packages.complete?'':'，未能確認完整性'}</p>`:''}${issue.gaps?.length?`<ul>${issue.gaps.map(gap=>`<li>${e(reason(gap))}</li>`).join('')}</ul>`:''}${issue.receipts?`<p>資料保存：${e(receipt(issue.receipts.retention))} · 後續呈現／通知：${e(receipt(issue.receipts.content_update))}</p>`:''}<p><a href="${e(workspaceUrl('/logs',profile,issue.result_id?{result:issue.result_id}:{entry:item.id}))}">${e(issue.result_id?c.diagnosis:'查看處理階段與未完成原因')} →</a></p></article>`).join('')}${summary.omitted_result_details?`<p>另有 ${e(summary.omitted_result_details)} 份主機結果未展開；可從主機結果連結查看。</p>`:''}${summary.omitted_hosts?`<p>另有 ${e(summary.omitted_hosts)} 台未完成主機；請查看執行紀錄。</p>`:''}${summary.incomplete_hosts&&!item.expanded?`<p><a href="${e(workspaceUrl('/logs',profile,{entry:item.id}))}">查看各階段與未完成原因 →</a></p>`:''}</section>`;
}

export function renderTaskActivity(item,hostId,{e}) {
 const issues=(item.summary?.issues||[]).filter(issue=>issue.host_id===hostId);
 if(!issues.length)return '<p>這份紀錄未提供本主機的具體未完成原因。</p>';
 const explain=code=>c.activityReasons[code]||c.reasons[code]||code||'未提供具體原因';
 return issues.map(issue=>{
  const stages=issue.stages||[],advisories=stages.find(stage=>stage.stage==='advisories'&&stage.status!=='success');
  const seen=new Set(),problems=[];
  for(const stage of stages){
   if(stage.status==='success')continue;
   if(advisories&&stage.stage==='report'&&stage.reason_code==='package_security_report_incomplete')continue;
   const message=explain(stage.reason_code);
   if(seen.has(stage.reason_code))continue;seen.add(stage.reason_code);
   problems.push(`${c.activityStages[stage.stage]||stage.stage}：${message}`);
  }
  if(!stages.length&&issue.reason_code){seen.add(issue.reason_code);problems.push(explain(issue.reason_code));}
  for(const gap of issue.gaps||[]){
   if(seen.has(gap)||gap==='package_security_report_incomplete'&&advisories)continue;
   seen.add(gap);problems.push(explain(gap));
  }
  return `${problems.length?`<ul>${problems.map(message=>`<li>${e(message)}</li>`).join('')}</ul>`:'<p>這份紀錄未提供具體未完成原因。</p>'}${advisories&&stages.some(stage=>stage.stage==='report'&&stage.status!=='success')?'<p>公告資料不足，弱點報告未能完成判讀；不能據此判定沒有弱點。</p>':''}${issue.packages?`<p>本次取得 ${e(issue.packages.collected_count??'未知')} 筆已安裝套件紀錄，作為弱點比對的輸入${issue.packages.complete?'':'（套件清單完整性尚未確認）'}；這是套件紀錄數，不是弱點數，也不代表全部已完成比對。</p>`:''}`;
 }).join('');
}
