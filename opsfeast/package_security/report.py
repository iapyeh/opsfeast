"""Escaped, self-contained reports over explicit package/advisory snapshots."""
from datetime import datetime,timezone
from html import escape
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .analysis import assess,unwrap

VERSION='0.3.0'
LABELS={'affected':'受影響','fixed':'已達廠商修補版本','not_affected':'廠商範圍顯示不受影響','unknown':'待確認'}


def generate(inputs,variables):
    values=[unwrap(value) for value in inputs]
    inventories=[value for value in values if value['kind']=='os-package-inventory'];feeds=[value for value in values if value['kind']=='vendor-advisories']
    if not inventories or not feeds and variables.get('allow_missing_advisories') is not True:raise ValueError('select_package_inventory_and_vendor_advisory_inputs')
    options={key:variables[key] for key in ('max_inventory_age_hours','max_advisory_age_days','max_findings') if key in variables}
    if variables.get('as_of'):options['as_of']=variables['as_of']
    gaps=variables.get('acquisition_gaps',[])
    if not isinstance(gaps,list) or len(gaps)>32 or any(not isinstance(g,str) or len(g)>256 for g in gaps):raise ValueError('invalid_acquisition_gaps')
    reports=[assess(inventory,feeds,**options) for inventory in inventories]
    for item in reports:
        if gaps:
            item['gaps']=sorted(set(item['gaps']+gaps));item['assessment_complete']=False
            if item['status']!='attention':item['status']='incomplete'
    return {'schema_version':VERSION,'kind':'os-package-security-reports','generated_at':datetime.now(timezone.utc).isoformat(),'title':variables.get('title','OS 套件弱點分析'),'reports':reports}


def render(data,directory):
    directory=Path(directory);title=str(data['title']);html=[];markdown=['# '+escape(title,quote=True).replace('\n',' ').replace('#','').replace('[','&#91;').replace(']','&#93;')+'\n']
    esc=lambda value:escape(str(value),quote=True)
    text=lambda value:esc(value).replace('|','&#124;').replace('\n',' ').replace('[','&#91;').replace(']','&#93;')
    for report in data['reports']:
        display_time=lambda value:datetime.fromisoformat(value.replace('Z','+00:00')).astimezone().strftime('%Y-%m-%d %H:%M:%S %z')
        collected=display_time(report['inventory_completed_at']);assessed=display_time(report['assessed_at'])
        headline=report['host_id']+' · '+report['status'];summary=json.dumps(report['counts'],ensure_ascii=False)
        html.append('<h2>'+esc(headline)+'</h2><p>'+esc(summary)+'</p><p>採集：'+esc(collected)+'；判讀：'+esc(assessed)+'</p>')
        markdown+=['\n## '+text(headline),'\n採集：'+text(collected)+'；判讀：'+text(assessed)+'\n','\n'+text(summary)+'\n']
        for limitation in report['limitations']:html.append('<p>'+esc(limitation)+'</p>');markdown.append('- '+text(limitation))
        for status in ('affected','unknown','fixed','not_affected'):
            rows=[finding for finding in report['findings'] if finding['status']==status]
            if not rows:continue
            section='<h3>'+esc(LABELS[status])+' ('+str(len(rows))+')</h3><table><tr><th>套件／架構</th><th>版本</th><th>公告</th><th>廠商修補界線</th><th>依據</th></tr>'
            markdown+=['\n### '+LABELS[status],'\n| 套件／架構 | 版本 | 公告 | 廠商修補界線 | 依據 |','| --- | --- | --- | --- | --- |']
            for row in rows:
                evidence={key:row[key] for key in ('summary','details','reason','uncertainty','candidate_status','source_package','source_version','cves','severity','references','vendor_modified_at','evidence')}
                boundaries=sorted(set(str(c.get('fixed') or c.get('upper')) for c in row['evidence']['comparisons'] if c.get('fixed') or c.get('upper_kind')=='fixed'))
                fixes=', '.join(boundaries) or '廠商未提供可用修補版本'
                section+='<tr><td>'+esc(row['package_kind']+': '+row['package']+'/'+row['architecture'])+'</td><td>'+esc(row['installed_version'])+'</td><td>'+esc(row['advisory_id'])+'</td><td>'+esc(fixes)+'</td><td><details><summary>'+esc(row['reason'])+'</summary><pre>'+esc(json.dumps(evidence,ensure_ascii=False,indent=2))+'</pre></details></td></tr>'
                markdown.append('| '+' | '.join(text(v) for v in (row['package_kind']+': '+row['package']+'/'+row['architecture'],row['installed_version'],row['advisory_id'],fixes,json.dumps(evidence,ensure_ascii=False)))+' |')
            section+='</table>'
            html.append(section if status=='affected' else '<details><summary>'+esc(LABELS[status])+'</summary>'+section+'</details>')
        details={key:report[key] for key in ('assessment_complete','inventory_complete','packages_complete','platform_details','inventory_gaps','gaps','omitted_findings','vendor_snapshots')}
        html.append('<h3>涵蓋範圍與公告來源</h3><pre>'+esc(json.dumps(details,ensure_ascii=False,indent=2))+'</pre>')
        markdown+=['\n### 涵蓋範圍與公告來源','\n<pre>'+escape(json.dumps(details,ensure_ascii=False,indent=2))+'</pre>']
    web='<!doctype html><html lang="zh-TW"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+esc(title)+'</title><style>body{font:16px system-ui;max-width:90rem;margin:2rem auto;padding:1rem;line-height:1.6}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:.5rem;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:.7rem 0}</style><h1>'+esc(title)+'</h1><p>版本與廠商公告的離線判讀；缺少資料、過期或範圍不符都不代表安全。產生報告不會重新採集或更新公告。</p>'+''.join(html)+'</html>'
    stamp=datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S');markdown+=['\n*Last modified: '+stamp+'*\n']
    (directory/'package-security.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    web=web.replace('</html>','<footer>Last modified: '+stamp+'</footer></html>')
    (directory/'package-security.html').write_text(web,encoding='utf-8')
    (directory/'package-security.md').write_text('\n'.join(markdown),encoding='utf-8')
    return [{'path':'package-security.'+ext,'title':title+suffix,'media_type':mime} for ext,suffix,mime in [('html',' · 閱讀版','text/html'),('md',' · Markdown','text/markdown'),('json',' · 判讀證據','application/json')]]


def execute(*,context,timeout):
    try:data=generate(context.inputs,context.vars)
    except (ValueError,KeyError,TypeError) as error:
        return {'status':'failed','reason_code':'invalid_package_security_inputs','message':'Select supported inventory and intact vendor snapshots; no analysis or collection was performed.','data':{'error_type':type(error).__name__,'detail_code':str(error) if isinstance(error,ValueError) else 'invalid_input_shape'},'artifacts':[]}
    artifacts=render(data,context.artifact_dir)
    incomplete=any(not report['assessment_complete'] for report in data['reports'])
    return {'status':'partial' if incomplete else 'success','reason_code':'package_security_report_incomplete' if incomplete else 'package_security_report_generated','message':'Vendor version findings generated; review affected and unknown entries. Report generation is not a safe-host verdict.','data':{'reports':len(data['reports']),'counts':{key:sum(r['counts'][key] for r in data['reports']) for key in LABELS}},'artifacts':artifacts}
