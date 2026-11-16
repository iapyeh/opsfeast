"""Fixed read-only OS package page probe. Target Python 3.8+ stdlib only."""
import hashlib
import json
import os
import platform
import re
import selectors
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime,timezone

VERSION='0.2.0'
MAX_DATABASE=64*1024*1024
PAGE_BYTES=64*1024


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


class QueryError(ValueError):
    def __init__(self, code, *, exitcode=None, stderr='', stderr_truncated=False):
        super().__init__(code)
        self.evidence={'exitcode':exitcode,'stderr':stderr,'stderr_truncated':stderr_truncated}


def run(argv,timeout):
    """Bound both pipes/deadline; keep original native failure evidence."""
    process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,LC_ALL='C',LANG='C'))
    output=bytearray();errors=bytearray();deadline=time.monotonic()+timeout
    def failure(code):
        return QueryError(code,exitcode=process.poll(),stderr=errors.decode('utf-8',errors='replace'),stderr_truncated=len(errors)>=16384)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ,'stdout')
            selector.register(process.stderr,selectors.EVENT_READ,'stderr')
            while selector.get_map():
                remaining=deadline-time.monotonic()
                if remaining<=0:raise failure('package_query_timeout')
                ready=selector.select(remaining)
                if not ready:raise failure('package_query_timeout')
                for key,_ in ready:
                    data=os.read(key.fileobj.fileno(),65536)
                    if not data:
                        selector.unregister(key.fileobj);continue
                    if key.data=='stdout':
                        output.extend(data)
                        if len(output)>MAX_DATABASE:raise failure('package_database_byte_limit')
                    else:
                        remaining_error=16384-len(errors);errors.extend(data[:remaining_error])
                        if len(data)>=remaining_error:raise failure('package_query_stderr_limit')
        process.wait(timeout=max(.1,deadline-time.monotonic()))
        if process.returncode:raise failure('package_query_failed')
        return output.decode('utf-8')
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=5)
        process.stdout.close();process.stderr.close()


def os_release():
    result={}
    if platform.system().lower()=='linux':
        with open('/etc/os-release','rb') as stream:raw=stream.read(65537)
        if len(raw)>65536:raise ValueError('os_release_byte_limit')
        for line in raw.decode().splitlines():
            if not line or line.startswith('#') or '=' not in line:continue
            key,value=line.split('=',1)
            if key in ('ID','ID_LIKE','VERSION_ID','VERSION_CODENAME','NAME','PRETTY_NAME'):
                parsed=shlex.split(value,comments=True)
                if len(parsed)>1:raise ValueError('invalid_os_release')
                result[key.lower()]=parsed[0] if parsed else ''
    else:result={'id':platform.system().lower(),'version_id':platform.release()}
    result['platform']=platform.system().lower();result['machine']=platform.machine()
    return result


def inventory(timeout):
    system=os_release();excluded={};rows=[];deadline=time.monotonic()+timeout
    details={'kind':system['platform'],'status':'complete','facts':{},'sources':[],'gaps':[],'package_database_status':'complete'}
    def query(argv,*,identity=False):
        remaining=deadline-time.monotonic()
        evidence={'command':argv,'status':'success','sha256':None,'error':None}
        try:
            if remaining<=0:raise ValueError('package_query_timeout')
            text=run(argv,remaining);evidence['sha256']=hashlib.sha256(text.encode()).hexdigest()
            return text
        except Exception as error:
            evidence.update(status='failed',error=str(error) if isinstance(error,ValueError) else type(error).__name__)
            if isinstance(error,QueryError):evidence['query_failure']=error.evidence
            if not identity:details['package_database_status']='failed'
            details['gaps'].append(('identity:' if identity else 'database:')+argv[0]+':'+evidence['error'])
            return None
        finally:details['sources'].append(evidence)
    if system['platform']=='linux':
        if system.get('id') in ('debian','ubuntu') or 'debian' in system.get('id_like','').split():manager='dpkg'
        elif shutil.which('rpm'):manager='rpm'
        else:raise ValueError('unsupported_os_package_manager')
        if manager=='dpkg':
            fmt='${Package}\t${Version}\t${Architecture}\t${source:Package}\t${source:Version}\t${db:Status-Status}\t${Maintainer}\n'
            output=query(['dpkg-query','-W','-f='+fmt]) or ''
            for line in output.splitlines():
                values=line.split('\t')
                if len(values)!=7:raise ValueError('invalid_package_record')
                name,version,arch,source,source_version,state,publisher=values
                if state in ('not-installed','config-files'):
                    excluded[state]=excluded.get(state,0)+1;continue
                rows.append(dict(package_kind='package',name=name,version=version,architecture=arch,source_name=source or None,source_version=source_version or None,installation_state=state,producer=publisher or None,epoch=None,release=None,source_rpm=None))
            pve=next((r for r in rows if r['name']=='pve-manager'),None)
            if pve is not None:
                details['kind']='proxmox-ve'
                details['facts']={'product':'Proxmox VE','manager_package_version':pve['version'],'manager_installation_state':pve['installation_state'],'components':[],'running_kernel':None,'running_manager':None}
                if pve['installation_state']!='installed':details['gaps'].append('proxmox_manager_not_fully_installed')
                text=query(['pveversion','--verbose'],identity=True)
                if text is not None:
                    if len(text.encode())>65536:raise ValueError('proxmox_version_output_limit')
                    components=[]
                    for line in text.splitlines():
                        match=re.fullmatch(r'([A-Za-z0-9.+_-]+):\s+([^\s]+)(?:\s+(.*))?',line)
                        if not match:details['gaps'].append('proxmox_version_record_unparsed');continue
                        missing=any(line.split(':',1)[1].strip().startswith(prefix) for prefix in ('not correctly installed','residual config','unknown package'))
                        if missing:details['gaps'].append('proxmox_component_state_incomplete')
                        available=re.search(r'\[available: ([^\]]+)\]',line)
                        components.append({'name':match[1],'version':None if missing else match[2],'status':'unavailable' if missing else 'observed','details':line.split(':',1)[1].strip(),'available_version':available[1] if available else None})
                    details['facts']['components']=components
                    for key,label in [('running_kernel','running kernel'),('running_manager','running version')]:
                        match=re.search(r'\('+label+r': ([^)]+)\)',text)
                        if match:details['facts'][key]=match[1]
                    if not components or not any(c['name']=='pve-manager' for c in components):details['gaps'].append('proxmox_manager_version_missing')
                    if not details['facts']['running_kernel']:details['gaps'].append('proxmox_running_kernel_missing')
                    if not details['facts']['running_manager']:details['gaps'].append('proxmox_running_manager_missing')
        else:
            fmt='%{NAME}\t%{EPOCH}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\t%{SOURCERPM}\t%{VENDOR}\n'
            output=query(['rpm','-qa','--qf',fmt]) or ''
            for line in output.splitlines():
                values=line.split('\t')
                if len(values)!=7:raise ValueError('invalid_package_record')
                name,epoch,version,release,arch,source,publisher=values
                if epoch=='(none)':epoch='0'
                if not epoch.isdigit():raise ValueError('invalid_package_epoch')
                rows.append(dict(package_kind='package',name=name,version=epoch+':'+version+'-'+release,architecture=arch,source_name=None,source_version=None,installation_state='installed',producer=None if publisher=='(none)' else publisher,epoch=int(epoch),release=release,source_rpm=None if source=='(none)' else source))
    elif system['platform']=='freebsd':
        manager='pkg'
        for key,flag in [('installed_kernel','-k'),('running_kernel','-r'),('userland','-u')]:
            text=query(['freebsd-version',flag],identity=True)
            value=text.strip() if text is not None else None
            if value and len(value)<=4096 and re.fullmatch(r'[0-9]+\.[0-9]+-[A-Za-z0-9._+-]+',value):
                patch=re.search(r'-p([0-9]+)$',value)
                details['facts'][key]={'version':value,'patch_level':int(patch[1]) if patch else None}
            else:
                details['facts'][key]={'version':None,'patch_level':None}
                if text is not None:details['gaps'].append('freebsd_'+key+'_invalid')
        output=query(['pkg','query','-a','%n\t%v\t%q\t%o']) or ''
        for line in output.splitlines():
            values=line.split('\t')
            if len(values)!=4:raise ValueError('invalid_package_record')
            name,version,arch,origin=values
            rows.append(dict(package_kind='package',name=name,version=version,architecture=arch,source_name=None,source_version=None,installation_state='installed',producer=None,epoch=None,release=None,source_rpm=None,ports_origin=origin))
    else:raise ValueError('unsupported_os_package_manager')
    seen=set()
    for row in rows:
        if any(not row[key] or any(ord(c)<32 for c in row[key]) for key in ('name','version','architecture')):raise ValueError('invalid_package_identity')
        key=(row['package_kind'],row['name'],row['version'],row['architecture'])
        if key in seen:raise ValueError('duplicate_package_identity')
        seen.add(key)
    rows.sort(key=lambda r:(r['package_kind'],r['name'],r['architecture'],r['version']))
    details['gaps']=sorted(set(details['gaps']))
    if details['gaps']:details['status']='partial'
    fingerprint=hashlib.sha256(encoded({'os':system,'manager':manager,'packages':rows,'excluded_states':excluded,'platform_details':details})).hexdigest()
    return system,manager,rows,excluded,fingerprint,hashlib.sha256(output.encode()).hexdigest(),details


def page(offset,limit,timeout):
    if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=500:raise ValueError('invalid_page_request')
    system,manager,rows,excluded,digest,source_digest,details=inventory(timeout)
    selected=[];size=0
    for row in rows[offset:offset+limit]:
        item=len(encoded(row))
        if size+item>PAGE_BYTES and selected:break
        if item>PAGE_BYTES:raise ValueError('package_record_byte_limit')
        selected.append(row);size+=item
    return {'schema_version':VERSION,'os':system,'platform_details':details,'manager':manager,'total':len(rows),'offset':offset,'next_offset':offset+len(selected),'packages':selected,'excluded_states':excluded,'snapshot_sha256':digest,'query_sha256':source_digest,'observed_at':datetime.now(timezone.utc).isoformat()}


def main():
    try:
        if sys.argv[1]=='redhat-advisories':
            if os_release().get('id')!='rhel' or not shutil.which('dnf'):raise ValueError('redhat_dnf_cache_unavailable')
            raw=run(['dnf','--cacheonly','--noplugins','updateinfo','list','--all','--security'],float(sys.argv[2]))
            ids=sorted(set(re.findall(r'\bRHSA-[0-9]{4}:[0-9]+\b',raw)))
            if len(ids)>10000:raise ValueError('redhat_advisory_discovery_limit')
            result={'schema_version':VERSION,'kind':'redhat-advisory-discovery','advisory_ids':ids,'query_sha256':hashlib.sha256(raw.encode()).hexdigest(),'observed_at':datetime.now(timezone.utc).isoformat(),'metadata_freshness':'not_verified'}
        else:result=page(int(sys.argv[1]),int(sys.argv[2]),float(sys.argv[3]))
    except Exception as error:
        code=str(error) if isinstance(error,ValueError) else type(error).__name__
        result={'schema_version':VERSION,'error':code}
        if isinstance(error,QueryError):result['query_evidence']=error.evidence
    print(json.dumps(result,ensure_ascii=True,separators=(',',':')))


if __name__=='__main__':main()
