"""Read-only, bounded failure evidence for saved operation/report results."""
from console_output import cell
from recipe_reports import result_path, show_result
from opsfeast import ConfigError


def excerpt(value):
    if not isinstance(value,str) or not value:
        return None
    lines=value.splitlines()
    selected=lines[:4]
    text='\n'.join(selected)
    clipped=len(lines)>4 or len(text)>400
    return {'text':text[:400],'clipped':clipped}


def diagnose(root, identifier, *, limit=5):
    """Use known evidence fields, never search arbitrary payloads or reconnect."""
    if type(limit) is not int or not 1<=limit<=50:
        raise ConfigError('diagnosis limit must be between 1 and 50')
    raw=show_result(root,identifier)
    resolved=result_path(root,identifier).relative_to(root).as_posix()
    issues=[]
    def add(stage,reason=None,error_type=None,**details):
        issues.append(dict(stage=stage,reason_code=reason,error_type=error_type,**details))
    errors=raw.get('execution_errors') or []
    for error in errors:
        if isinstance(error,dict):
            add(error.get('stage','execution'),error.get('reason_code'),error.get('error_type') or error.get('type'))
    if raw.get('cleanup_error') and not any(i['stage']=='cleanup' for i in issues):
        add('cleanup','cleanup_failed',raw['cleanup_error'])
    for key in ('retention','content_update','operation_recording'):
        receipt=raw.get(key) or {}
        if receipt.get('status')=='failed':
            add(key,receipt.get('reason_code') or key+'_failed',receipt.get('error_type'))
            for consumer in receipt.get('consumers',[]):
                if isinstance(consumer,dict) and consumer.get('status')=='failed':
                    add(key,consumer.get('reason_code'),consumer.get('error_type'),consumer=consumer.get('consumer'))
    access=raw.get('access') or {}
    if access.get('degraded'):
        add('access','fallback_user')
    probes=raw.get('probes')
    if not isinstance(probes,list):
        probes=(raw.get('collection_process') or {}).get('probes',raw.get('sources',[]))
    probes=[p for p in probes if isinstance(p,dict)]
    skipped=0
    failed_ids=set()
    for probe in probes:
        state=probe.get('status')
        if state is None:
            if probe.get('exitcode')==0 and not probe.get('error'):
                continue
            if probe.get('exitcode') is None and not probe.get('error'):
                continue
            state='failed'
        error=probe.get('error') if isinstance(probe.get('error'),dict) else {}
        reason=probe.get('reason_code') or error.get('code')
        if state in ('skipped','not_supported','unsupported') or (state=='not_attempted' and reason in (None,'not_attempted')) or reason=='unsupported_platform_or_probe':
            skipped+=1
            continue
        if state=='success':
            continue
        # Synthetic acquisition gaps merely repeat the outer execution error.
        if not probe.get('command') and errors:
            continue
        failed_ids.add(probe.get('id'))
        add('probe',reason or state,probe.get('error_type') or error.get('type'),probe_id=probe.get('id'),
            command=probe.get('command'),exitcode=probe.get('exitcode'),
            stdout=excerpt(probe.get('stdout')),stderr=excerpt(probe.get('stderr')),
            stdout_truncated=probe.get('stdout_truncated',False),stderr_truncated=probe.get('stderr_truncated',False))
    gaps={}
    for group in raw.get('groups',[]):
        for sample in group.get('samples',[]):
            if sample.get('status')!='success':
                reason=sample.get('reason_code')
                if reason=='unsupported_platform_or_probe' or sample.get('source_id') in failed_ids or errors:
                    continue
                key=(sample.get('source_id'),reason)
                gaps.setdefault(key,set()).add(sample.get('property','unknown'))
    for (source,reason),properties in gaps.items():
        add('samples',reason or 'value_not_reported',probe_id=source,properties=sorted(properties))
    selected=issues[:limit]
    notes=[]
    if any(i['error_type'] for i in selected if i['stage']!='probe'):
        notes.append('Exception messages and source locations were not recorded; the exact failing key or line cannot be recovered from this result.')
    if not issues and raw.get('status')!='success':
        notes.append('No specific failure evidence was recorded. The result does not establish a successful collection.')
    return {'diagnosis_version':'0.1.0','result_id':resolved,'requested_id':identifier,
            'host_id':raw.get('host_id'),'status':raw.get('status'),'reason_code':raw.get('reason_code'),
            'probe_count':len(probes),'unsupported_or_unattempted':skipped,'issue_count':len(issues),
            'shown_count':len(selected),'omitted_count':len(issues)-len(selected),'issues':selected,'notes':notes}


def format_diagnosis(report):
    lines=['Result: '+cell(report['requested_id'])[:200], 'Host: '+cell(report.get('host_id') or 'Not recorded')[:200],
           'Status: '+cell(report.get('status') or 'unknown')[:100]+
           (' ('+cell(report['reason_code'])[:200]+')' if report.get('reason_code') else ''),
           'Problems: '+str(report['issue_count'])+'; unsupported/not attempted probes: '+str(report['unsupported_or_unattempted'])]
    if not report['issues'] and report.get('status')=='success':
        lines += ['No recorded failures.']
    for index,issue in enumerate(report['issues'],1):
        title=' / '.join(cell(value) for value in (issue['stage'],issue.get('error_type'),issue.get('reason_code')) if value)
        lines += ['',str(index)+'. '+title[:400]]
        for name in ('command','probe_id','exitcode','consumer'):
            if issue.get(name) is not None:
                lines += ['   '+name+': '+cell(issue[name])[:400]]
        if issue.get('properties'):
            properties=issue['properties']
            lines += ['   properties: '+', '.join(cell(p) for p in properties[:5])+(' …' if len(properties)>5 else '')]
        for stream in ('stderr','stdout'):
            evidence=issue.get(stream)
            if evidence:
                lines += ['   '+stream+':',*['     '+cell(line) for line in evidence['text'].splitlines()]]
                if evidence['clipped'] or issue.get(stream+'_truncated'):
                    lines += ['     [excerpt/capture truncated; inspect the saved probe for available output]']
            elif issue.get(stream+'_truncated'):
                lines += ['   '+stream+': capture truncated; output unavailable']
    if report['omitted_count']:
        lines += ['',str(report['omitted_count'])+' more problems omitted; increase --limit (maximum 50).']
    if report['notes']:
        lines += ['',*report['notes']]
    return '\n'.join(lines)
