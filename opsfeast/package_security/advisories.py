"""Immutable vendor advisory snapshots; fetching is explicit, analysis is offline."""
from datetime import datetime,timezone
import hashlib
import io
import json
import lzma
from pathlib import Path,PurePosixPath
import re
import tarfile
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler

VERSION='0.1.0'
MAX_RAW=128*1024*1024
MAX_RECORD=8*1024*1024
MAX_EXPANDED=1024*1024*1024
MAX_SNAPSHOT=256*1024*1024
NATIVE={'freebsd':'freebsd','proxmox':'debian','esxi':'esxi'}
OS_IDS={'debian':'debian','ubuntu':'ubuntu','redhat':'rhel',**NATIVE}
HOSTS={'freebsd':{'www.freebsd.org','vuxml.freebsd.org'},'proxmox':{'forum.proxmox.com'},'esxi':{'support.broadcom.com'},'debian':{'security-tracker.debian.org'},'ubuntu':{'security-metadata.canonical.com','raw.githubusercontent.com','github.com'},'redhat':{'security.access.redhat.com'}}


def now():return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def timestamp(value):
    if not isinstance(value,str):raise ValueError('invalid_timestamp')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.utcoffset() is None:raise ValueError('timezone_required')
    return parsed


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate_json_key')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_json')))


def validate_url(vendor,url):
    parsed=urlsplit(url)
    if vendor not in HOSTS or parsed.scheme!='https' or parsed.hostname not in HOSTS[vendor] or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.fragment or (parsed.query and not (vendor=='esxi' and url=='https://support.broadcom.com/web/ecx/security-advisory?segment=VC')):raise ValueError('unsupported_vendor_url')
    if vendor=='ubuntu' and parsed.hostname in ('github.com','raw.githubusercontent.com') and not parsed.path.startswith('/canonical/ubuntu-security-notices/'):raise ValueError('unsupported_vendor_url')
    if vendor=='proxmox' and not re.fullmatch(r'/threads/proxmox-virtual-environment-security-advisories\.149331/(?:page-[0-9]+)?',parsed.path):raise ValueError('unsupported_vendor_url')
    if vendor=='freebsd' and not (parsed.hostname=='www.freebsd.org' and (parsed.path=='/security/advisories/' or re.fullmatch(r'/security/advisories/FreeBSD-SA-[0-9]{2}:[0-9]+\.[a-z0-9_]+\.asc',parsed.path)) or parsed.hostname=='vuxml.freebsd.org' and parsed.path in ('/freebsd/vuln.xml','/freebsd/vuln.xml.bz2')):raise ValueError('unsupported_vendor_url')
    if vendor=='esxi' and not (parsed.path in ('/web/ecx/security-advisory','/web/ecx/security-advisory/-/securityadvisory/getSecurityAdvisoryList') or re.fullmatch(r'/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/(?:0|[A-Za-z0-9_-]+)/[0-9]+',parsed.path)):raise ValueError('unsupported_vendor_url')
    return url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def download(vendor,url,timeout=60,*,payload=None):
    validate_url(vendor,url)
    deadline=time.monotonic()+timeout
    http=build_opener(ProxyHandler({}),NoRedirect())
    with http.open(Request(url,data=canonical(payload) if payload is not None else None,headers={'Content-Type':'application/json','Accept':'application/json, application/octet-stream','User-Agent':'OpsFeast-package-security/0.3.0'}),timeout=timeout) as response:
        chunks=[];size=0
        while True:
            if time.monotonic()>deadline:raise ValueError('vendor_download_deadline')
            chunk=response.read1(65536)
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
            if size>(32*1024*1024 if vendor in NATIVE else MAX_RAW):raise ValueError('vendor_download_limit')
        raw=b''.join(chunks)
        evidence={'url':url,'retrieved_at':now(),'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'https_official_endpoint','last_modified':response.headers.get('Last-Modified')}
        if payload is not None:evidence['request']={'method':'POST','json':payload}
        return raw,evidence


def documents(raw,name):
    """No archive extraction. Bound xz dictionary, expanded bytes and members."""
    if len(raw)>MAX_RAW:raise ValueError('vendor_input_limit')
    if name.endswith('.tar.xz'):
        decoder=lzma.LZMADecompressor(memlimit=128*1024*1024)
        with tempfile.TemporaryFile() as stream:
            total=0
            for offset in range(0,len(raw),65536):
                chunk=raw[offset:offset+65536]
                while True:
                    decoded=decoder.decompress(chunk,max_length=1024*1024);chunk=b'';total+=len(decoded)
                    if total>MAX_EXPANDED:raise ValueError('vendor_expansion_limit')
                    stream.write(decoded)
                    if decoder.eof or decoder.needs_input:break
                if decoder.eof:
                    if decoder.unused_data or offset+65536<len(raw):raise ValueError('unexpected_vendor_archive_tail')
                    break
            if not decoder.eof:raise ValueError('incomplete_vendor_archive')
            stream.seek(0);members=0;total=0
            with tarfile.open(fileobj=stream,mode='r:') as archive:
                for item in archive:
                    members+=1;total+=item.size
                    if members>250000 or total>MAX_EXPANDED:raise ValueError('vendor_archive_limit')
                    if item.isdir():continue
                    if not item.isfile() or '..' in PurePosixPath(item.name).parts or item.name.startswith('/') or '\\' in item.name:raise ValueError('invalid_vendor_archive_member')
                    if item.size>MAX_RECORD:raise ValueError('vendor_record_limit')
                    if item.name.endswith('.json'):
                        with archive.extractfile(item) as source:yield parse(source.read(MAX_RECORD+1))
    else:
        if len(raw)>MAX_RECORD:raise ValueError('vendor_record_limit')
        value=parse(raw)
        if not isinstance(value,dict):raise ValueError('vendor_record_requires_object')
        yield value


def _debian(raw,scope):
    if len(raw)>MAX_RAW:raise ValueError('vendor_input_limit')
    data=parse(raw)
    if not isinstance(data,dict):raise ValueError('invalid_debian_tracker')
    for package,issues in data.items():
        if not isinstance(issues,dict):raise ValueError('invalid_debian_tracker')
        for identifier,issue in issues.items():
            if not isinstance(issue,dict) or not isinstance(issue.get('releases',{}),dict):raise ValueError('invalid_debian_record')
            release=issue.get('releases',{}).get(scope['codename'])
            if release is None:continue
            if not isinstance(release,dict):raise ValueError('invalid_debian_release')
            yield {'id':identifier,'aliases':[],'upstream':[identifier],'summary':issue.get('description',''),'modified':None,'published':None,'severity':[{'type':'Debian','score':release.get('urgency','unknown')}],
                   'references':[{'type':'ADVISORY','url':'https://security-tracker.debian.org/tracker/'+identifier}],
                   'affected':[{'package':{'name':package,'ecosystem':'Debian:'+scope['version_id']},'ranges':[],'versions':[],'database_specific':{'debian_status':release.get('status'),'fixed_version':release.get('fixed_version'),'repository_versions':release.get('repositories',{})}}]}


def _applicable(vendor,entry,scope):
    package=entry.get('package',{})
    if not isinstance(package,dict) or not isinstance(package.get('name'),str) or not isinstance(package.get('ecosystem'),str):raise ValueError('invalid_osv_package')
    ecosystem=package['ecosystem']
    if vendor=='ubuntu':return bool(re.fullmatch(r'Ubuntu:(?:Pro:)?'+re.escape(scope['version_id'])+r'(?::LTS)?',ecosystem))
    if vendor=='redhat':
        version=scope['version_id'].split('.')[0]
        return ecosystem.startswith('Red Hat:enterprise_linux:'+version+':')
    return False


def snapshot(vendor,scope,sources,inputs):
    """Normalize original vendor JSON, retaining its native version predicates."""
    if vendor not in HOSTS or set(scope)!={'os_id','version_id','codename'} or not all(isinstance(v,str) for v in scope.values()) or not scope['version_id']:raise ValueError('invalid_vendor_scope')
    if scope['os_id']!=OS_IDS[vendor]:raise ValueError('vendor_os_scope_mismatch')
    if vendor=='debian' and not re.fullmatch('[a-z][a-z0-9-]*',scope['codename']):raise ValueError('debian_codename_required')
    records=[];ids=set();bytes_used=0
    for raw,name in inputs:
        iterator=__import__('opsfeast.package_security.native_advisories',fromlist=['normalize']).normalize(vendor,raw,name if name.startswith('https://') else sources[0]['url']) if vendor in NATIVE else _debian(raw,scope) if vendor=='debian' else documents(raw,name)
        for document in iterator:
            if not isinstance(document,dict) or not isinstance(document.get('id'),str) or not isinstance(document.get('affected'),list):raise ValueError('invalid_vendor_document')
            identifier=document['id']
            if vendor not in NATIVE and vendor!='debian' and not re.fullmatch(r'1\.[0-9]+\.[0-9]+',document.get('schema_version','1.0.0')):raise ValueError('unsupported_osv_schema_version')
            if vendor=='ubuntu' and not identifier.startswith('UBUNTU-CVE-'):continue  # USN/LSN records must not substitute for full CVE data.
            if vendor=='redhat' and not re.fullmatch('RHSA-[0-9]{4}:[0-9]+',identifier):continue
            relevant=[entry for entry in document['affected'] if isinstance(entry,dict) and (vendor in NATIVE or vendor=='debian' or _applicable(vendor,entry,scope))]
            if not relevant:continue
            record={key:document.get(key,[] if key in ('aliases','upstream','severity','references') else None) for key in ('id','aliases','upstream','summary','details','published','modified','withdrawn','severity','references')}
            record['affected']=relevant;record['native_record_sha256']=document.get('native_record_sha256',digest(document))
            identity=(identifier,tuple(entry['package']['name'] for entry in relevant))
            if identity in ids:raise ValueError('duplicate_vendor_record')
            ids.add(identity);bytes_used+=len(canonical(record))
            if bytes_used>MAX_SNAPSHOT:raise ValueError('advisory_snapshot_limit')
            records.append(record)
    for source in sources:
        validate_url(vendor,source['url']);timestamp(source['retrieved_at'])
        if not re.fullmatch('[0-9a-f]{64}',source['sha256']):raise ValueError('invalid_source_hash')
    if not sources:raise ValueError('advisory_sources_required')
    result={'schema_version':VERSION,'kind':'vendor-advisories','vendor':vendor,'scope':scope,'created_at':now(),'sources':sources,'coverage':'provided vendor records; absence is not a not-affected assertion','record_count':len(records),'records':records}
    result['snapshot_sha256']=digest(result);return load(result)


def load(value):
    if not isinstance(value,dict) or value.get('schema_version')!=VERSION or value.get('kind')!='vendor-advisories':raise ValueError('invalid_advisory_snapshot')
    if value.get('snapshot_sha256')!=digest({k:v for k,v in value.items() if k!='snapshot_sha256'}):raise ValueError('advisory_snapshot_digest_mismatch')
    vendor=value.get('vendor');scope=value.get('scope',{})
    if vendor not in HOSTS or set(scope)!={'os_id','version_id','codename'} or scope['os_id']!=OS_IDS[vendor] or any(not isinstance(v,str) for v in scope.values()):raise ValueError('invalid_vendor_scope')
    if not isinstance(value.get('records'),list) or value.get('record_count')!=len(value['records']):raise ValueError('advisory_record_count_mismatch')
    if not isinstance(value.get('sources'),list) or not value['sources']:raise ValueError('advisory_sources_required')
    if not isinstance(value.get('coverage_gaps',[]),list) or len(value.get('coverage_gaps',[]))>32 or any(not isinstance(v,str) or len(v)>256 for v in value.get('coverage_gaps',[])):raise ValueError('invalid_advisory_coverage_gaps')
    timestamp(value['created_at'])
    for source in value['sources']:
        validate_url(vendor,source['url']);timestamp(source['retrieved_at'])
        if not re.fullmatch('[0-9a-f]{64}',source['sha256']) or source.get('acquisition') not in ('https_official_endpoint','user_attested_local_import'):raise ValueError('invalid_advisory_source')
    for record in value['records']:
        if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not re.fullmatch('[0-9a-f]{64}',record.get('native_record_sha256','')) or not isinstance(record.get('affected'),list):raise ValueError('invalid_advisory_record')
        for key in ('aliases','upstream','severity','references'):
            if not isinstance(record.get(key),list):raise ValueError('invalid_advisory_record')
        if any(not isinstance(v,str) for v in record['aliases']+record['upstream']):raise ValueError('invalid_advisory_alias')
        for entry in record['affected']:
            if not isinstance(entry,dict) or not isinstance(entry.get('package'),dict) or any(not isinstance(entry['package'].get(k),str) for k in ('name','ecosystem')):raise ValueError('invalid_advisory_package')
            if not isinstance(entry.get('ranges',[]),list) or not isinstance(entry.get('versions',[]),list):raise ValueError('invalid_advisory_ranges')
    return value


def fetch(vendor,scope,advisory_ids=(),*,deadline=None):
    if vendor in NATIVE:
        if not isinstance(scope,dict) or set(scope)!={'os_id','version_id','codename'} or scope.get('os_id')!=OS_IDS[vendor] or any(not isinstance(v,str) for v in scope.values()) or not re.fullmatch({'freebsd':r'[0-9]+\.[0-9]+','proxmox':r'[0-9]+','esxi':r'[0-9]+\.[0-9]+\.[0-9]+'}[vendor],scope['version_id']):raise ValueError('invalid_native_vendor_scope')
        from .native_advisories import acquire
        for url in advisory_ids:validate_url(vendor,url)
        return acquire(vendor,scope,download,deadline=deadline,selected=advisory_ids)
    if vendor=='debian':urls=['https://security-tracker.debian.org/tracker/data/json']
    elif vendor=='ubuntu':urls=['https://security-metadata.canonical.com/osv/osv-all.tar.xz']
    elif vendor=='redhat':
        if not advisory_ids or any(not re.fullmatch('RHSA-[0-9]{4}:[0-9]+',value) for value in advisory_ids):raise ValueError('redhat_requires_explicit_rhsa_ids')
        if len(advisory_ids)>100:raise ValueError('too_many_redhat_advisories')
        urls=['https://security.access.redhat.com/data/osv/'+value+'.json' for value in advisory_ids]
    else:raise ValueError('unsupported_advisory_vendor')
    sources=[];inputs=[]
    for url in urls:
        if deadline is None:raw,source=download(vendor,url)
        else:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('advisory_acquisition_deadline')
            raw,source=download(vendor,url,timeout=min(60,remaining))
        if vendor=='redhat':
            if len(raw)>MAX_RECORD or parse(raw).get('id')!=urlsplit(url).path.rsplit('/',1)[-1][:-5]:raise ValueError('redhat_advisory_identity_mismatch')
        sources.append(source);inputs.append((raw,urlsplit(url).path))
    return snapshot(vendor,scope,sources,inputs)


def import_local(vendor,scope,source,source_url,retrieved_at):
    validate_url(vendor,source_url);timestamp(retrieved_at)
    path=Path(source)
    if path.is_symlink():raise ValueError('symlink_advisory_source')
    if path.is_dir() and any(p.is_symlink() for p in path.rglob('*')):raise ValueError('symlink_advisory_source')
    paths=sorted(p for p in path.rglob('*' if vendor in NATIVE else '*.json') if p.is_file()) if path.is_dir() else [path]
    if not paths:raise ValueError('empty_advisory_import')
    inputs=[];sources=[];total=0
    for file in paths:
        if file.is_symlink() or not file.is_file() or file.stat().st_size>MAX_RAW:raise ValueError('invalid_advisory_source')
        raw=file.read_bytes();total+=len(raw)
        if total>MAX_SNAPSHOT:raise ValueError('advisory_import_limit')
        inputs.append((raw,file.name));sources.append({'url':source_url,'retrieved_at':retrieved_at,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'user_attested_local_import','last_modified':None})
    return snapshot(vendor,scope,sources,inputs)
