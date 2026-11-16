"""Page-consistent OS package inventory using the borrowed Recipe session."""
from datetime import datetime,timezone
import hashlib
import json
import re
from pathlib import Path
import time
from urllib.parse import quote,urlencode

VERSION='0.2.0'
MAX_SNAPSHOT=64*1024*1024


def now():return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def purl(row,system,manager):
    kind={'dpkg':'deb','rpm':'rpm','pkg':'freebsd'}.get(manager)
    if kind is None:return None
    namespace={'rhel':'redhat'}.get(system.get('id'),system.get('id','unknown'))
    qualifiers={'arch':row['architecture'],'distro':system.get('version_codename') or system.get('version_id','unknown')}
    return 'pkg:'+kind+'/'+quote(namespace,safe='')+'/'+quote(row['name'],safe='')+'@'+quote(row['version'],safe='')+'?'+urlencode(qualifiers,quote_via=quote)


def collect(recipe):
    budget=recipe.vars.get('collection_budget_seconds',180);page_size=recipe.vars.get('page_size',200);command_seconds=recipe.vars.get('command_timeout_seconds',30)
    if type(budget) not in (int,float) or not 1<=budget<=900 or type(page_size) is not int or not 1<=page_size<=500 or type(command_seconds) not in (int,float) or not 1<=command_seconds<=120:raise ValueError('invalid_package_collection_limits')
    declared=recipe.vars.get('declared_ecosystems',[])
    if not isinstance(declared,list) or len(declared)>100 or any(not isinstance(v,str) or not 1<=len(v)<=256 for v in declared):raise ValueError('invalid_declared_ecosystems')
    source=Path(__file__).with_name('probe.py').read_text();started=now();deadline=time.monotonic()+budget
    snapshot={'schema_version':VERSION,'kind':'os-package-inventory','host_id':recipe.host_id,'declared_ecosystems':declared,'scope':'Visible native OS package databases plus FreeBSD base/kernel and product identity; no application/container filesystem crawl','os':{},'platform_details':{'kind':'unknown','status':'partial','facts':{},'sources':[],'gaps':['platform_unidentified'],'package_database_status':'failed'},'packages_complete':False,'manager':None,'packages':[],'complete':False,'expected_count':None,'collected_count':0,'excluded_states':{},'snapshot_sha256':None,'acquisition':{'started_at':started,'completed_at':None,'pages':[]},'gaps':[]}
    try:
        response=recipe.session.exec_command(['uname','-s'],check=False,command_timeout=min(command_seconds,recipe.timeout,budget))
        if response.exitcode or response.stdout_truncated or response.stderr_truncated or len(response.stdout)>128:raise ValueError('platform_detection_failed')
        kernel=response.stdout.strip().lower()
        snapshot['acquisition']['platform_detection']={'command':['uname','-s'],'kernel':kernel,'observed_at':now()}
    except Exception as error:
        snapshot['gaps'].append(str(error) if isinstance(error,ValueError) else type(error).__name__)
        snapshot['acquisition']['completed_at']=now()
        return _result(snapshot)
    if kernel=='vmkernel':return _esxi(recipe,snapshot,deadline,command_seconds)
    if kernel not in ('linux','freebsd'):
        snapshot['os']={'id':kernel,'platform':kernel};snapshot['gaps'].append('unsupported_os_package_manager')
        snapshot['acquisition']['completed_at']=now();return _result(snapshot)
    offset=0;fingerprint=None;final_check=False;bytes_used=0;native_rows=[]
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:snapshot['gaps'].append('collection_budget_exhausted');break
        timeout=min(command_seconds,recipe.timeout,remaining)
        evidence={'offset':offset,'started_at':now()}
        try:
            response=recipe.session.exec_command(['python3','-B','-',str(0 if final_check else offset),str(1 if final_check else page_size),str(max(.01,timeout*.8))],input=source,check=False,command_timeout=timeout)
            evidence.update(exitcode=response.exitcode,termination_status=getattr(response,'termination_status','unknown'),stdout_truncated=bool(response.stdout_truncated),stderr_truncated=bool(response.stderr_truncated),completed_at=now())
            if response.exitcode or response.stdout_truncated or response.stderr_truncated:raise ValueError('package_command_failed_or_truncated')
            if len(response.stdout.encode())>128*1024:raise ValueError('package_page_byte_limit')
            payload=json.loads(response.stdout)
            if not isinstance(payload,dict) or payload.get('schema_version')!=VERSION:raise ValueError('invalid_package_page')
            if payload.get('error'):
                evidence['query_failure']=payload.get('query_evidence')
                raise ValueError('target:'+str(payload['error']))
            if set(payload)!={'schema_version','os','manager','total','offset','next_offset','packages','excluded_states','snapshot_sha256','query_sha256','observed_at','platform_details'}:raise ValueError('invalid_package_page')
            if type(payload['total']) is not int or payload['total']<0 or not isinstance(payload['packages'],list):raise ValueError('invalid_package_page')
            if not isinstance(payload['os'],dict) or payload['manager'] not in ('dpkg','rpm','pkg') or any(not isinstance(payload.get(k),str) or not re.fullmatch('[0-9a-f]{64}',payload[k]) for k in ('snapshot_sha256','query_sha256')):raise ValueError('invalid_package_page_identity')
            details=payload['platform_details']
            if not isinstance(details,dict) or set(details)!={'kind','status','facts','sources','gaps','package_database_status'} or details['status'] not in ('complete','partial') or details['package_database_status'] not in ('complete','failed') or not isinstance(details['facts'],dict) or not isinstance(details['gaps'],list) or any(not isinstance(g,str) for g in details['gaps']) or not isinstance(details['sources'],list) or details['kind'] not in ('linux','freebsd','proxmox-ve','esxi','unknown'):raise ValueError('invalid_platform_details')
            if fingerprint is None:
                fingerprint=payload['snapshot_sha256'];snapshot.update(platform_details=payload['platform_details'],os=payload['os'],manager=payload['manager'],expected_count=payload['total'],snapshot_sha256=fingerprint,excluded_states=payload['excluded_states'])
            if payload['snapshot_sha256']!=fingerprint or payload['os']!=snapshot['os'] or payload['manager']!=snapshot['manager'] or payload['total']!=snapshot['expected_count'] or payload['platform_details']!=snapshot['platform_details']:raise ValueError('package_database_changed_during_collection')
            evidence.update(query_sha256=payload['query_sha256'],snapshot_sha256=payload['snapshot_sha256'],observed_at=payload['observed_at'],records=len(payload['packages']))
            if final_check:
                encoded=json.dumps({'os':snapshot['os'],'manager':snapshot['manager'],'packages':native_rows,'excluded_states':snapshot['excluded_states'],'platform_details':snapshot['platform_details']},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
                if hashlib.sha256(encoded).hexdigest()!=fingerprint:raise ValueError('package_snapshot_digest_mismatch')
                snapshot['packages_complete']=snapshot['platform_details']['package_database_status']=='complete'
                snapshot['complete']=snapshot['packages_complete'] and snapshot['platform_details']['status']=='complete'
                snapshot['gaps'].extend(snapshot['platform_details']['gaps']);break
            if payload['offset']!=offset or payload['next_offset']!=offset+len(payload['packages']) or payload['next_offset']>payload['total'] or not payload['packages'] and offset<payload['total']:raise ValueError('invalid_package_page_sequence')
            for row in payload['packages']:
                if not isinstance(row,dict) or any(not isinstance(row.get(k),str) or not row[k] for k in ('package_kind','name','version','architecture','installation_state')):raise ValueError('invalid_package_identity')
                if any(isinstance(v,str) and len(v)>4096 for v in row.values()):raise ValueError('package_record_byte_limit')
                native_rows.append(dict(row))
                row={**row,'purl':purl(row,snapshot['os'],snapshot['manager']),'repository_origin':None,'provenance_status':'package_database_only; repository/signature not independently verified'}
                bytes_used+=len(json.dumps(row).encode())
                if bytes_used>MAX_SNAPSHOT:raise ValueError('package_snapshot_byte_limit')
                snapshot['packages'].append(row)
            offset=payload['next_offset'];snapshot['collected_count']=offset
            if offset==payload['total']:final_check=True
        except Exception as error:
            snapshot['gaps'].append(str(error) if isinstance(error,ValueError) else type(error).__name__);break
        finally:
            evidence.setdefault('completed_at',now());snapshot['acquisition']['pages'].append(evidence)
    snapshot['acquisition']['completed_at']=now()
    snapshot['collected_count']=len(snapshot['packages'])
    if snapshot['packages_complete']:
        keys={(p['package_kind'],p['name'],p['version'],p['architecture']) for p in snapshot['packages']}
        if len(keys)!=len(snapshot['packages']) or len(snapshot['packages'])!=snapshot['expected_count']:snapshot['complete']=False;snapshot['packages_complete']=False;snapshot['gaps'].append('package_identity_or_count_mismatch')
    return _result(snapshot)


def _result(snapshot):
    status='success' if snapshot['complete'] else 'partial' if snapshot['packages'] or snapshot['platform_details']['facts'] else 'unsupported' if any('unsupported_os_package_manager' in reason for reason in snapshot['gaps']) else 'failed'
    return {'status':status,'reason_code':'os_package_snapshot' if snapshot['complete'] else 'os_package_inventory_incomplete','message':'OS package and platform snapshot; inspect package completeness, identity gaps and provenance. No vulnerability assessment has been performed.','data':snapshot}


def _esxi(recipe,snapshot,deadline,command_seconds):
    from .esxi import read
    try:
        data,fingerprint,evidence=read(recipe,deadline,command_seconds)
        snapshot.update({k:v for k,v in data.items() if k!='packages'})
        snapshot.update(snapshot_sha256=fingerprint,expected_count=len(data['packages']))
        size=0
        for row in data['packages']:
            enriched={**row,'purl':None,'repository_origin':None,'provenance_status':'native_esxcli_metadata_only; binary/signature verification not performed'}
            size+=len(json.dumps(enriched).encode())
            if size>MAX_SNAPSHOT:raise ValueError('package_snapshot_byte_limit')
            snapshot['packages'].append(enriched)
        snapshot['acquisition']['pages'].append({'phase':'initial','sources':evidence})
        _,verified,evidence=read(recipe,deadline,command_seconds)
        snapshot['acquisition']['pages'].append({'phase':'final_check','sources':evidence})
        if verified!=fingerprint:raise ValueError('package_database_changed_during_collection')
        snapshot['packages_complete']=data['platform_details']['package_database_status']=='complete'
        snapshot['complete']=snapshot['packages_complete'] and data['platform_details']['status']=='complete'
        snapshot['gaps'].extend(data['platform_details']['gaps'])
    except Exception as error:
        snapshot['gaps'].append(str(error) if isinstance(error,ValueError) else type(error).__name__)
    snapshot['collected_count']=len(snapshot['packages']);snapshot['acquisition']['completed_at']=now()
    return _result(snapshot)
