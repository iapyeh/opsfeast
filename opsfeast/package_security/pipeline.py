"""Host-selected package-security workflow 0.2.0; reused by the bundled meal.

Collection borrows the supplied session. Vendor HTTPS and report writes are local.
No reconnects, privilege changes, package refreshes or remediation.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import time

from . import advisories
from .inventory import collect
from host_runtime import progress

VERSION = '0.3.0'
REPORT = 'feast/report/package-security'
COLLECT_VARS = ('collection_budget_seconds','command_timeout_seconds','page_size','declared_ecosystems')


def _directory(root, relative):
    from recipe_reports import safe_directory
    return safe_directory(root, relative, create=True)


def _write(path, value, *, replace=False):
    if path.is_symlink():raise ValueError('security_snapshot_symlink')
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name)
        try:
            json.dump(value,stream,ensure_ascii=False,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True);raise
    try:
        if replace:os.replace(temporary,path)
        else:
            try:os.link(temporary,path)
            except FileExistsError:
                if path.read_bytes()!=temporary.read_bytes():raise ValueError('security_snapshot_conflict')
    finally:temporary.unlink(missing_ok=True)


@contextmanager
def _lock(path, deadline):
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        while True:
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise ValueError('advisory_cache_wait_deadline')
                time.sleep(.05)
        yield


def _cached(root, vendor, scope, ids, max_age_hours, deadline):
    cache=_directory(root,'security/advisories');key=advisories.digest({'vendor':vendor,'scope':scope,'ids':ids})
    pointer=cache/(key+'.json')
    with _lock(cache/(key+'.lock'),deadline):
        if pointer.is_symlink():raise ValueError('advisory_cache_symlink')
        if pointer.exists():
            if pointer.stat().st_size>4096:raise ValueError('invalid_advisory_cache_index')
            index=advisories.parse(pointer.read_bytes());digest=index.get('snapshot_sha256')
            if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('invalid_advisory_cache_index')
            path=cache/(digest+'.snapshot.json')
            if path.is_symlink() or path.stat().st_size>advisories.MAX_SNAPSHOT:raise ValueError('invalid_advisory_cache_snapshot')
            value=advisories.load(advisories.parse(path.read_bytes()))
            if value['snapshot_sha256']!=digest or value['vendor']!=vendor or value['scope']!=scope:raise ValueError('advisory_cache_scope_mismatch')
            ages=[(datetime.now(timezone.utc)-advisories.timestamp(s['retrieved_at'])).total_seconds() for s in value['sources']]
            if max_age_hours>0 and ages and all(0<=age<=max_age_hours*3600 for age in ages):return value,path,'reused_fresh_snapshot'
        value=advisories.fetch(vendor,scope,ids,deadline=deadline)
        path=cache/(value['snapshot_sha256']+'.snapshot.json');_write(path,value)
        _write(pointer,{'snapshot_sha256':value['snapshot_sha256']},replace=True)
        return value,path,'downloaded_official_snapshot'


def _redhat_ids(recipe):
    source=Path(__file__).with_name('probe.py').read_text(encoding='utf-8')
    timeout=min(recipe.timeout,recipe.vars.get('command_timeout_seconds',30))
    response=recipe.session.exec_command(['python3','-B','-','redhat-advisories',str(timeout*.8)],input=source,check=False,command_timeout=timeout)
    if response.exitcode or response.stdout_truncated or response.stderr_truncated or len(response.stdout.encode())>1024*1024:raise ValueError('redhat_advisory_discovery_failed')
    value=advisories.parse(response.stdout)
    if value.get('error') or value.get('kind')!='redhat-advisory-discovery' or not isinstance(value.get('advisory_ids'),list) or len(value['advisory_ids'])>10000:raise ValueError('redhat_advisory_discovery_unavailable')
    if any(not isinstance(v,str) or not re.fullmatch('RHSA-[0-9]{4}:[0-9]+',v) for v in value['advisory_ids']):raise ValueError('invalid_redhat_advisory_ids')
    return value


def execute(recipe):
    root=Path(recipe.profile.root).resolve()
    run_id=recipe.run_id
    if not isinstance(run_id,str) or not re.fullmatch('[A-Za-z0-9-]{1,100}',run_id):raise ValueError('invalid_package_pipeline_run_id')
    age=recipe.vars.get('advisory_cache_hours',24);budget=recipe.vars.get('advisory_budget_seconds',180)
    if type(age) not in (int,float) or not 0<=age<=168 or type(budget) not in (int,float) or not 1<=budget<=240:raise ValueError('invalid_advisory_pipeline_limits')
    explicit_ids=recipe.vars.get('redhat_advisory_ids',[])
    if not isinstance(explicit_ids,list) or len(explicit_ids)>100 or any(not isinstance(i,str) or not re.fullmatch('RHSA-[0-9]{4}:[0-9]+',i) for i in explicit_ids):raise ValueError('invalid_redhat_advisory_ids')
    folder=_directory(root,'security/package-runs/'+run_id)
    progress('package-security 1/3: collecting OS package snapshot')
    # Only collection inputs reach the original collector, on its borrowed child scope.
    with recipe.child(vars={k:recipe.vars[k] for k in COLLECT_VARS if k in recipe.vars}) as child:
        collected=collect(child)
    inventory=collected['data'];inventory_path=folder/'inventory.json';_write(inventory_path,inventory)
    stages=[{'stage':'collection','status':collected['status'],'reason_code':collected['reason_code'],'input':inventory_path.relative_to(root).as_posix()}]
    vendor={'debian':'debian','ubuntu':'ubuntu','rhel':'redhat'}.get(inventory['os'].get('id'))
    from .native_advisories import scope_for
    native_vendor,native_scope=scope_for(inventory)
    if native_vendor:vendor=native_vendor
    inputs=[inventory_path];gaps=[]
    progress('package-security 2/3: acquiring matching vendor advisories on controller')
    try:
        if vendor is None:raise ValueError('vendor_distribution_unsupported_or_unidentified')
        system=inventory['os'];scope=native_scope or {'os_id':system['id'],'version_id':system.get('version_id',''),'codename':system.get('version_codename','')}
        ids=sorted(set(explicit_ids)) if vendor=='redhat' else recipe.vars.get('vendor_advisory_urls',[]) if native_vendor else []
        if not isinstance(ids,list) or len(ids)>1000 or any(not isinstance(url,str) for url in ids):raise ValueError('invalid_vendor_advisory_urls')
        for url in ids if native_vendor else []:advisories.validate_url(vendor,url)
        discovery=None
        if vendor=='redhat' and not ids:
            discovery=_redhat_ids(recipe);ids=discovery['advisory_ids']
            gaps.append('redhat_cache_metadata_freshness_unverified')
            if len(ids)>100:
                ids=sorted(ids,key=lambda v:tuple(map(int,re.findall('[0-9]+',v))),reverse=True)[:100]
                gaps.append('redhat_advisory_discovery_exceeds_100_record_scope')
            if not ids:raise ValueError('redhat_cache_has_no_security_advisory_ids')
        value,path,acquisition=_cached(root,vendor,scope,sorted(ids),age,time.monotonic()+budget)
        inputs.append(path)
        gaps.extend(value.get('coverage_gaps',[]))
        stages.append({'stage':'advisories','status':'partial' if gaps else 'success','reason_code':acquisition,'vendor':vendor,'record_count':value['record_count'],'snapshot_sha256':value['snapshot_sha256'],'input':path.relative_to(root).as_posix(),'discovery':discovery})
    except Exception as error:
        reason=str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z0-9_]+',str(error)) else 'vendor_acquisition_failed'
        gaps.append(reason);stages.append({'stage':'advisories','status':'failed','reason_code':reason,'vendor':vendor,'error_type':type(error).__name__})
    progress('package-security 3/3: generating saved vulnerability report')
    from recipe_catalog import choose
    from recipe_reports import run_report
    report_id=None
    try:
        report,path=run_report(root,choose(root,REPORT),inputs,values={'allow_missing_advisories':True,'acquisition_gaps':gaps},timeout=recipe.timeout)
        report_id=path.relative_to(root).as_posix()
    except Exception as error:
        gaps.append('package_security_report_generation_failed')
        report={'status':'failed','reason_code':'package_security_report_generation_failed','data':{}}
    stages.append({'stage':'report','status':report['status'],'reason_code':report['reason_code'],'result_id':report_id})
    complete=collected['status']=='success' and not gaps and report['status']=='success'
    status='success' if complete else 'partial' if report['status'] in ('success','partial') else 'failed'
    progress('package-security finished: '+status)
    summary={'kind':'os-package-security-run','stages':[{k:v for k,v in stage.items() if k!='discovery'} for stage in stages],'gaps':gaps,'inventory':{'complete':inventory['complete'],'collected_count':inventory['collected_count'],'snapshot_sha256':inventory['snapshot_sha256'],'input':inventory_path.relative_to(root).as_posix()},'report':{'result_id':report_id,'status':report['status'],'counts':report.get('data',{}).get('counts',{})}}
    return {'status':status,'reason_code':'package_security_pipeline_complete' if complete else 'package_security_pipeline_incomplete',
            'message':'Package snapshot, vendor acquisition and report receipts saved; inspect affected and unknown findings.',
            'data':{'kind':'os-package-security-run','schema_version':VERSION,'package_snapshot':inventory,'stages':stages,'gaps':gaps,'report':{'result_id':report_id,'status':report['status'],'counts':report.get('data',{}).get('counts',{})}},
            'summary':summary,'reports':[{'result_id':report_id,'status':report['status']}] if report_id else []}
