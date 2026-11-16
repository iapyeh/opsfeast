"""Offline, vendor-scoped package findings with explicit unknowns and evidence."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
import math
import re
from urllib.parse import parse_qs,urlsplit

from .advisories import load,timestamp,digest
from .versions import compare

VERSION='0.3.0'
from . import native_advisories as native


def unwrap(value):
    if isinstance(value,dict) and value.get('kind') in ('os-package-inventory','vendor-advisories'):return value
    if isinstance(value,dict) and isinstance(value.get('data'),dict) and value['data'].get('kind')=='os-package-inventory':return value['data']
    raise ValueError('expected_os_package_snapshot_or_vendor_advisories')


def validate_inventory(value):
    if not isinstance(value,dict) or value.get('schema_version')!='0.2.0' or value.get('kind')!='os-package-inventory' or type(value.get('complete')) is not bool or not isinstance(value.get('os'),dict) or not isinstance(value.get('packages'),list):raise ValueError('invalid_os_package_inventory')
    if type(value.get('packages_complete')) is not bool or not isinstance(value.get('platform_details'),dict):raise ValueError('invalid_platform_details')
    if value['complete'] and (not value['packages_complete'] or value['platform_details'].get('status')!='complete'):raise ValueError('inconsistent_package_completeness')
    if not isinstance(value.get('host_id'),str) or not value['host_id']:raise ValueError('inventory_host_required')
    start=timestamp(value['acquisition']['started_at']);end=timestamp(value['acquisition']['completed_at'])
    if end<start:raise ValueError('inventory_time_order')
    if not isinstance(value.get('gaps'),list) or not isinstance(value.get('scope'),str) or not isinstance(value.get('declared_ecosystems',[]),list):raise ValueError('invalid_inventory_scope')
    if any(not isinstance(v,str) for v in value.get('declared_ecosystems',[])):raise ValueError('invalid_declared_ecosystems')
    for package in value['packages']:
        if not isinstance(package,dict) or any(not isinstance(package.get(key),str) or not package[key] for key in ('package_kind','name','version','architecture','installation_state')):raise ValueError('invalid_package_identity')
    keys={(p['package_kind'],p['name'],p['version'],p['architecture']) for p in value['packages']}
    if len(keys)!=len(value['packages']):raise ValueError('duplicate_package_identity')
    if value['complete'] and value['gaps']:raise ValueError('complete_inventory_with_gaps')
    if value['packages_complete'] and (len(value['packages'])!=value.get('expected_count') or value.get('collected_count')!=len(value['packages'])):raise ValueError('inventory_count_mismatch')
    if value['packages_complete']:
        native=[{k:v for k,v in p.items() if k not in ('purl','repository_origin','provenance_status')} for p in value['packages']]
        expected=digest({'os':value['os'],'manager':value['manager'],'packages':native,'excluded_states':value['excluded_states'],'platform_details':value['platform_details']})
        if expected!=value.get('snapshot_sha256'):raise ValueError('inventory_snapshot_digest_mismatch')
    return value


def ranges_status(version,entry,scheme):
    """OSV interval membership; do not treat 'not listed' as not affected."""
    if version in entry.get('versions',[]):return 'affected','vendor_explicit_affected_version',[]
    ranges=entry.get('ranges',[])
    if not ranges:return 'unknown','vendor_affected_range_missing',[]
    statuses=[];comparisons=[];fixes=[]
    for interval in ranges:
        if interval.get('type')!='ECOSYSTEM' or not isinstance(interval.get('events'),list):return 'unknown','unsupported_vendor_range_type',comparisons
        start=None;seen=False;affected=False;after_fix=False;previous=None
        kinds={next(iter(event)) for event in interval['events'] if isinstance(event,dict) and len(event)==1}
        if 'fixed' in kinds and 'last_affected' in kinds:return 'unknown','conflicting_vendor_range_events',comparisons
        for event in interval['events']:
            if not isinstance(event,dict) or len(event)!=1:return 'unknown','invalid_vendor_range',comparisons
            kind,boundary=next(iter(event.items()))
            if kind not in ('introduced','fixed','last_affected','limit') or not isinstance(boundary,str):return 'unknown','unsupported_vendor_range_event',comparisons
            if boundary=='*':return 'unknown','unsupported_vendor_infinite_limit',comparisons
            if previous is not None and (boundary=='0' or compare(boundary,previous,scheme)<0):return 'unknown','unordered_vendor_range',comparisons
            previous=boundary
            if kind=='introduced':
                if start is not None:return 'unknown','unclosed_vendor_range',comparisons
                start=boundary;seen=True;continue
            if start is None:return 'unknown','vendor_range_missing_introduction',comparisons
            lower=1 if start=='0' else compare(version,start,scheme)
            upper=compare(version,boundary,scheme)
            comparisons.append({'installed':version,'lower':start,'upper':boundary,'upper_kind':kind,'lower_compare':lower,'upper_compare':upper,'scheme':scheme})
            if lower>=0 and (upper<=0 if kind=='last_affected' else upper<0):affected=True
            if kind=='fixed':
                fixes.append(boundary)
                if upper>=0:after_fix=True
            start=None
        if not seen:return 'unknown','empty_vendor_range',comparisons
        if start is not None:
            lower=1 if start=='0' else compare(version,start,scheme)
            comparisons.append({'installed':version,'lower':start,'upper':None,'upper_kind':None,'lower_compare':lower,'upper_compare':None,'scheme':scheme})
            if lower>=0:affected=True
        statuses.append('affected' if affected else 'fixed' if after_fix else 'not_affected')
    if 'affected' in statuses:return 'affected','within_vendor_affected_range',comparisons
    if 'fixed' in statuses:return 'fixed','vendor_fixed_version_satisfied',comparisons
    return 'not_affected','outside_vendor_affected_intervals',comparisons


def _candidate(package,entry,vendor):
    if vendor=='debian':
        data=entry.get('database_specific',{});state=data.get('debian_status');fixed=data.get('fixed_version')
        version=package.get('source_version')
        if not version:return 'unknown','source_package_version_missing',[]
        if state=='resolved' and fixed=='0':return 'not_affected','debian_vendor_not_affected',[]
        if state=='resolved' and isinstance(fixed,str) and fixed:
            comparison=compare(version,fixed,'deb')
            return ('fixed' if comparison>=0 else 'affected'),'debian_source_version_comparison',[{'installed':version,'fixed':fixed,'compare':comparison,'scheme':'deb'}]
        if state=='open' and not fixed:return 'affected','debian_vendor_open_issue',[]
        return 'unknown','debian_vendor_status_undetermined',[]
    version=package.get('source_version') if vendor=='ubuntu' else package['version']
    if not version:return 'unknown','source_package_version_missing',[]
    return ranges_status(version,entry,'deb' if vendor=='ubuntu' else 'rpm')


def _scope_reasons(inventory,feed,entry):
    reasons=[];system=inventory['os'];scope=feed['scope']
    if system.get('id')!=scope['os_id'] or system.get('version_id')!=scope['version_id']:reasons.append('vendor_os_release_mismatch')
    if feed['vendor'] in ('debian','ubuntu') and scope['codename'] and system.get('version_codename')!=scope['codename']:reasons.append('vendor_codename_mismatch')
    ecosystem=entry['package']['ecosystem'];declared=inventory.get('declared_ecosystems',[])
    architecture=parse_qs(urlsplit(entry['package'].get('purl','')).query).get('arch',[])
    if architecture and architecture[0] not in ('source','noarch','all') and architecture[0]!=inventory.get('_assessed_arch'):reasons.append('vendor_architecture_mismatch')
    if feed['vendor']=='redhat' and ecosystem not in declared:reasons.append('redhat_product_stream_not_confirmed')
    if feed['vendor']=='ubuntu':
        match=re.fullmatch(r'Ubuntu:(Pro:)?([^:]+)(?::LTS)?',ecosystem)
        if match is None or match[2]!=system.get('version_id'):reasons.append('ubuntu_ecosystem_mismatch')
        if match and match[1] and ecosystem not in declared:reasons.append('ubuntu_pro_scope_not_confirmed')
        purl=entry['package'].get('purl','')
        distro=parse_qs(urlsplit(purl).query).get('distro',[])
        if distro and distro[0].split('/')[-1]!=system.get('version_codename'):reasons.append('vendor_codename_mismatch')
    return reasons


def assess(inventory,feeds,*,as_of=None,max_inventory_age_hours=24,max_advisory_age_days=7,max_findings=100000):
    inventory=validate_inventory(inventory)
    instant=timestamp(as_of) if as_of else datetime.now(timezone.utc)
    if type(max_inventory_age_hours) not in (int,float) or not math.isfinite(max_inventory_age_hours) or max_inventory_age_hours<=0 or type(max_advisory_age_days) not in (int,float) or not math.isfinite(max_advisory_age_days) or max_advisory_age_days<=0 or type(max_findings) is not int or max_findings<1:raise ValueError('invalid_assessment_limits')
    feeds=list({feed['snapshot_sha256']:load(feed) for feed in feeds}.values())
    global_reasons=[]
    if not inventory['complete']:global_reasons.append('inventory_incomplete')
    age=(instant-timestamp(inventory['acquisition']['completed_at'])).total_seconds()
    if age<0:global_reasons.append('inventory_time_in_future')
    elif age>max_inventory_age_hours*3600:global_reasons.append('inventory_stale')
    vendor={'debian':'debian','ubuntu':'ubuntu','rhel':'redhat'}.get(inventory['os'].get('id'))
    native_vendor,native_scope=native.scope_for(inventory)
    if native_vendor:vendor=native_vendor
    compatible=[feed for feed in feeds if feed['vendor']==vendor]
    if len(compatible)!=1:global_reasons.append('missing_or_ambiguous_vendor_snapshot')
    elif compatible[0]['scope']!=(native_scope or {'os_id':inventory['os'].get('id'),'version_id':inventory['os'].get('version_id'),'codename':inventory['os'].get('version_codename','')}):global_reasons.append('vendor_os_release_mismatch')
    global_reasons.extend(gap for feed in compatible for gap in feed.get('coverage_gaps',[]))
    index=defaultdict(list);feed_reasons={}
    for feed in compatible:
        reasons=list(feed.get('coverage_gaps',[]))
        source_ages=[(instant-timestamp(source['retrieved_at'])).total_seconds() for source in feed['sources']]
        if any(age<0 for age in source_ages):reasons.append('advisory_retrieval_time_in_future')
        if not source_ages or any(age>max_advisory_age_days*86400 for age in source_ages):reasons.append('advisory_snapshot_stale')
        feed_reasons[feed['snapshot_sha256']]=reasons
        for record in feed['records']:
            for entry in record['affected']:index[entry['package']['name']].append((feed,record,entry))
    patterns={name:items for name,items in index.items() if re.search(r'[*?\[]',name)}
    findings=[];omitted=0
    for package in native.targets(inventory) if native_vendor else inventory['packages']:
        name=package.get('source_name') if vendor in ('debian','ubuntu') else package['name']
        matches=(list(index.get(name,[]))+[item for pattern,items in patterns.items() if native.matching(name,pattern) for item in items] if native_vendor else index.get(name,[]))
        if not matches:
            matches=[(None,None,None)]
        for feed,record,entry in matches:
            reasons=list(global_reasons);candidate='unknown';reason='no_vendor_record';comparison=[]
            if package['installation_state']!='installed':reasons.append('installation_state_not_fully_installed')
            if feed:
                reasons+=feed_reasons[feed['snapshot_sha256']]
                if not native_vendor:reasons+=_scope_reasons({**inventory,'_assessed_arch':package['architecture']},feed,entry)
                if record.get('withdrawn'):reasons.append('advisory_withdrawn')
                try:candidate,reason,comparison=native.candidate(package,entry.get('database_specific',{}),inventory) if native_vendor else _candidate(package,entry,vendor)
                except (ValueError,TypeError,KeyError):reason='unsupported_or_invalid_vendor_version_rule';candidate='unknown'
                if entry.get('package',{}).get('ecosystem') is None:reasons.append('vendor_ecosystem_missing')
            if inventory['manager']!=({'debian':'dpkg','ubuntu':'dpkg','redhat':'rpm','freebsd':'pkg','proxmox':'dpkg','esxi':'esxcli'}.get(vendor)):reasons.append('vendor_package_manager_mismatch')
            if vendor is None:reasons.append('unsupported_vendor_distribution')
            if vendor in ('debian','ubuntu') and (not package.get('source_name') or not package.get('source_version')):reasons.append('source_package_identity_missing')
            finding={'host_id':inventory['host_id'],'package':package['name'],'package_kind':package['package_kind'],'architecture':package['architecture'],'installed_version':package['version'],'source_package':package.get('source_name'),'source_version':package.get('source_version'),'purl':package.get('purl'),
                     'status':'unknown' if reasons else candidate,'candidate_status':candidate,'reason':reason,'uncertainty':sorted(set(reasons)),
                     'advisory_id':record['id'] if record else None,'summary':(record or {}).get('summary'),'details':(record or {}).get('details'),'cves':sorted(set(value for value in ((record or {}).get('aliases',[])+(record or {}).get('upstream',[])+[(record or {}).get('id','')]) if re.fullmatch(r'CVE-[0-9]{4}-[0-9]+',value))),
                     'severity':(record or {}).get('severity',[]),'references':(record or {}).get('references',[]),'vendor_modified_at':(record or {}).get('modified'),
                     'evidence':{'scheme':inventory['manager'],'matched_identity':'source-package' if vendor in ('debian','ubuntu') else 'binary-package','ecosystem':entry['package']['ecosystem'] if entry else None,'comparisons':comparison,'native_record_sha256':record['native_record_sha256'] if record else None,'advisory_snapshot_sha256':feed['snapshot_sha256'] if feed else None,'inventory_snapshot_sha256':inventory['snapshot_sha256'],'provenance_status':package.get('provenance_status','unknown'),'version_assessment_only':True}}
            if native_vendor=='esxi' and entry:finding['cves']=entry.get('database_specific',{}).get('cves',[])
            if len(findings)>=max_findings:omitted+=1
            else:findings.append(finding)
    counts={key:sum(f['status']==key for f in findings) for key in ('affected','fixed','not_affected','unknown')}
    complete=not global_reasons and not omitted and not counts['unknown']
    return {'schema_version':VERSION,'kind':'os-package-vulnerability-report','host_id':inventory['host_id'],'assessed_at':instant.isoformat(),'inventory_completed_at':inventory['acquisition']['completed_at'],'inventory_complete':inventory['complete'],'packages_complete':inventory['packages_complete'],'platform_details':inventory['platform_details'],'scope':inventory['scope'],
            'status':'attention' if counts['affected'] else 'evaluated' if complete else 'incomplete','assessment_complete':complete,'counts':counts,'finding_count':len(findings),'omitted_findings':omitted,'gaps':sorted(set(global_reasons+(['report_finding_limit'] if omitted else []))),
            'inventory_gaps':inventory['gaps'],'package_count':len(inventory['packages']),'vendor_snapshots':[{key:feed[key] for key in ('vendor','scope','sources','snapshot_sha256','coverage','record_count')} for feed in feeds],
            'limitations':['Version-based vendor assessment, not binary/signature attestation or exploitability proof.','OS package databases only: application libraries, containers, running-process linkage and effective service configuration are not assessed.','No matching advisory is unknown, never a safe or not-affected assertion.','A fixed version does not establish that running processes or the kernel were restarted.'], 'findings':findings}
