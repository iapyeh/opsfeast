"""Controller-side ESXi inventory. Target Python is not required.

Fixed native ESXCLI XML queries over the borrowed session; no install or elevation.
"""
from datetime import datetime,timezone
import hashlib
import re
import time
import xml.etree.ElementTree as ET

from .advisories import digest

MAX_BYTES=64*1024*1024
MAX_XML_NODES=200000


def _tag(node):return node.tag.rsplit('}',1)[-1]


def _value(node,depth=0):
    if depth>12:raise ValueError('esxi_xml_depth_limit')
    tag=_tag(node)
    if tag=='structure':
        result={}
        for field in node:
            if _tag(field)!='field' or not field.get('name') or field.get('name') in result or len(field)!=1:raise ValueError('invalid_esxi_xml_field')
            result[field.get('name')]=_value(field[0],depth+1)
        return result
    if tag=='list':return [_value(child,depth+1) for child in node]
    if tag in ('string','integer','int','long','boolean','date','float','double'):
        if len(node):raise ValueError('invalid_esxi_xml_scalar')
        text=node.text or ''
        if len(text)>4096:raise ValueError('esxi_field_size_limit')
        return text
    raise ValueError('unsupported_esxi_xml_type')


def parse(text):
    raw=text.encode()
    if len(raw)>MAX_BYTES or re.search(br'<!\s*(?:DOCTYPE|ENTITY)',raw,re.I):raise ValueError('unsafe_or_oversized_esxi_xml')
    parser=ET.XMLPullParser(events=('start','end'));root=None;depth=0;count=0
    for offset in range(0,len(raw),65536):
        parser.feed(raw[offset:offset+65536])
        for event,node in parser.read_events():
            if event=='start':
                count+=1;depth+=1
                if root is None:root=node
                if count>MAX_XML_NODES or depth>32:raise ValueError('esxi_xml_resource_limit')
            else:depth-=1
    parser.close()
    if root is None:raise ValueError('empty_esxi_xml')
    if _tag(root)!='output' or len(root)!=1:raise ValueError('invalid_esxi_xml_output')
    value=_value(root[0])
    if isinstance(value,dict):return [value]
    if not isinstance(value,list) or any(not isinstance(row,dict) for row in value):raise ValueError('invalid_esxi_xml_records')
    return value


def read(recipe,deadline,command_seconds):
    details={'kind':'esxi','status':'complete','facts':{},'sources':[],'gaps':[],'package_database_status':'complete'}
    system={'id':'esxi','platform':'vmkernel','version_id':'unknown','machine':'unknown'}
    rows=[];acquisition=[]
    def query(argv):
        evidence={'command':argv,'started_at':datetime.now(timezone.utc).isoformat()}
        source={'command':argv,'status':'success','sha256':None,'error':None}
        try:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('collection_budget_exhausted')
            response=recipe.session.exec_command(argv,check=False,command_timeout=min(recipe.timeout,command_seconds,remaining))
            evidence.update(exitcode=response.exitcode,stdout_truncated=bool(response.stdout_truncated),stderr_truncated=bool(response.stderr_truncated))
            if response.exitcode or response.stdout_truncated or response.stderr_truncated:
                evidence['stderr']=getattr(response,'stderr','')[:16384]
                raise ValueError('esxi_command_failed_or_truncated')
            if len(response.stdout.encode())>MAX_BYTES:raise ValueError('esxi_output_byte_limit')
            source['sha256']=hashlib.sha256(response.stdout.encode()).hexdigest()
            return response.stdout
        except Exception as error:
            source.update(status='failed',error=str(error) if isinstance(error,ValueError) else type(error).__name__)
            details['gaps'].append(source['error']+':'+ ' '.join(argv));return None
        finally:
            evidence['completed_at']=datetime.now(timezone.utc).isoformat();acquisition.append(evidence);details['sources'].append(source)
    def xml_query(args):
        text=query(['esxcli','--formatter=xml',*args])
        if text is None:return None
        try:return parse(text)
        except (ValueError,ET.ParseError):
            details['gaps'].append('esxi_xml_unparseable:'+ ' '.join(args));return None
    versions=xml_query(['system','version','get'])
    if versions and len(versions)==1:
        details['facts']['system_version']=versions[0]
        version=versions[0].get('Version')
        if isinstance(version,str) and version:system['version_id']=version
        else:details['gaps'].append('esxi_version_missing')
        if not isinstance(versions[0].get('Build'),str) or not versions[0]['Build']:details['gaps'].append('esxi_build_missing')
    else:details['gaps'].append('esxi_version_unavailable')
    architecture=query(['uname','-m'])
    if architecture and architecture.strip():system['machine']=architecture.strip()
    details['facts']['image_profile']=xml_query(['software','profile','get'])
    if not details['facts']['image_profile']:details['gaps'].append('esxi_image_profile_unavailable')
    for kind,args in [('vib',['software','vib','list']),('component',['software','component','list'])]:
        records=xml_query(args)
        if records is None:
            details['package_database_status']='failed';continue
        for record in records:
            name,version=record.get('Name'),record.get('Version')
            if not isinstance(name,str) or not name or not isinstance(version,str) or not version:
                details['gaps'].append('esxi_'+kind+'_identity_missing');details['package_database_status']='failed';continue
            if any(isinstance(value,str) and any(ord(c)<32 for c in value) for value in (name,version)):
                details['gaps'].append('esxi_'+kind+'_identity_invalid');details['package_database_status']='failed';continue
            rows.append({'package_kind':kind,'name':name,'version':version,'architecture':record.get('Architecture') if isinstance(record.get('Architecture'),str) and record.get('Architecture') else 'unknown',
                         'architecture_source':'esxcli' if record.get('Architecture') else 'not_reported',
                         'installation_state':'installed','source_name':None,'source_version':None,'producer':record.get('Vendor') if isinstance(record.get('Vendor'),str) else None,
                         'epoch':None,'release':None,'source_rpm':None,'native_fields':record})
    rows.sort(key=lambda r:(r['package_kind'],r['name'],r['architecture'],r['version']))
    keys={(r['package_kind'],r['name'],r['version'],r['architecture']) for r in rows}
    if len(keys)!=len(rows):details['gaps'].append('duplicate_package_identity');details['package_database_status']='failed'
    details['gaps']=sorted(set(details['gaps']))
    if details['gaps']:details['status']='partial'
    data={'os':system,'manager':'esxcli','packages':rows,'excluded_states':{},'platform_details':details}
    return data,digest(data),acquisition
