"""Official FreeBSD, Proxmox and ESXi source adapters and native predicates.

No target execution. HTML/XML is parsed as data, never rendered or executed.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from html.parser import HTMLParser
import fnmatch
import re
import time
from urllib.parse import urljoin,urlsplit,unquote
import xml.etree.ElementTree as ET

from .freebsd_versions import compare as pkg_compare
from .versions import debian

FREEBSD_INDEX='https://www.freebsd.org/security/advisories/'
VUXML='https://vuxml.freebsd.org/freebsd/vuln.xml.bz2'
PVE_THREAD='https://forum.proxmox.com/threads/proxmox-virtual-environment-security-advisories.149331/'
ESXI_INDEX='https://support.broadcom.com/web/ecx/security-advisory/-/securityadvisory/getSecurityAdvisoryList'
MAX_DOCUMENTS=1000
MAX_NODES=1500000
VENDORS={'freebsd':'freebsd','proxmox':'debian','esxi':'esxi'}


class Node:
    def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def walk(self,tag=None):
        if tag is None or self.tag==tag:yield self
        for child in self.children:
            if isinstance(child,Node):yield from child.walk(tag)
    def text(self):
        if self.tag in ('script','style'):return ''
        value=''.join(child.text() if isinstance(child,Node) else child for child in self.children)
        return ('\n'+value+'\n') if self.tag in ('br','p','div','li','tr','h1','h2','h3','h4','pre') else value


class HTML(HTMLParser):
    def __init__(self,raw):
        super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.nodes=0
        if len(raw)>32*1024*1024:raise ValueError('vendor_html_limit')
        self.feed(raw.decode('utf-8'));self.close()
    def handle_starttag(self,tag,attrs):
        self.nodes+=1
        if self.nodes>MAX_NODES or len(self.stack)>128:raise ValueError('vendor_html_structure_limit')
        node=Node(tag,attrs);self.stack[-1].children.append(node)
        if tag not in ('br','hr','img','meta','link','input','wbr','source','area','base','embed','param'):self.stack.append(node)
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:del self.stack[i:];break
    def handle_data(self,data):self.stack[-1].children.append(data)


def clean(value):return ' '.join(value.replace('\u200b','').split())


def xml(raw):
    if len(raw)>128*1024*1024 or b'\x00' in raw:raise ValueError('unsafe_vendor_xml')
    raw.decode('utf-8')
    # The official flattened feed retains unused historical-year declarations.
    # Accept only that inert prolog; reject entity use and never fetch a DTD.
    declaration=re.search(br'<!DOCTYPE[^[]*\[(.*?)\]\s*>',raw,re.S)
    if declaration:
        if b'vuxml' not in declaration[0] or re.sub(br'<!ENTITY vuln-[0-9]{4} SYSTEM \"vuln/[0-9]{4}\.xml\">',b'',declaration[1]).strip():raise ValueError('unsafe_vendor_xml')
        raw=raw[:declaration.start()]+raw[declaration.end():]
    if re.search(br'<!\s*ENTITY|&vuln-[0-9]+;',raw,re.I):raise ValueError('unsafe_vendor_xml')
    raw=re.sub(br'<!DOCTYPE[^>]*>',b'',raw,flags=re.I)
    parser=ET.XMLPullParser(events=('start','end'));root=None;depth=count=0
    for offset in range(0,len(raw),65536):
        parser.feed(raw[offset:offset+65536])
        for event,node in parser.read_events():
            if event=='start':
                count+=1;depth+=1
                if root is None:root=node
                if count>MAX_NODES or depth>64:raise ValueError('vendor_xml_structure_limit')
            else:depth-=1
    parser.close()
    if root is None:raise ValueError('empty_vendor_xml')
    for node in root.iter():node.tag=node.tag.rsplit('}',1)[-1]
    return root


def record(identifier,summary,entries,url,raw,*,published=None):
    from .advisories import digest
    return {'id':identifier,'aliases':sorted(set(re.findall(r'CVE-[0-9]{4}-[0-9]+',raw))), 'upstream':[],
            'summary':summary,'details':raw,'published':published,'modified':None,'withdrawn':None,
            'severity':[],'references':[{'type':'ADVISORY','url':url}], 'affected':entries,'native_record_sha256':digest(raw)}


def entry(name,ecosystem,rule):return {'package':{'name':name,'ecosystem':ecosystem},'ranges':[],'versions':[],'database_specific':rule}


def vuxml(raw,url):
    root=xml(raw)
    if root.tag!='vuxml':raise ValueError('invalid_vuxml_root')
    for issue in root.findall('vuln'):
        identifier=issue.get('vid');entries=[]
        if not identifier:raise ValueError('missing_vuxml_id')
        for package in issue.findall('./affects/package'):
            groups=[]
            for group in package.findall('range'):
                predicates=[{'operator':p.tag,'version':p.text or ''} for p in group]
                groups.append(predicates)
            for name in package.findall('name'):
                if name.text:entries.append(entry(name.text,'FreeBSD:pkg',{'native_type':'vuxml','ranges':groups}))
        refs=' '.join(n.text or '' for n in issue.findall('./references/cvename'))
        text=' '.join(issue.itertext())
        yield record('VuXML:'+identifier,issue.findtext('topic') or '',entries,url,ET.tostring(issue,encoding='unicode')+' '+refs,published=issue.findtext('./dates/entry'))


def freebsd_base(raw,url):
    text=raw.decode('utf-8');identifier=re.search(r'FreeBSD-SA-[0-9]{2}:[0-9]+\.[a-z0-9_]+',text)
    if not identifier:raise ValueError('invalid_freebsd_security_advisory')
    def field(name):
        match=re.search(r'^'+name+r':\s*(.*(?:\n[ \t]+[^\n]+)*)',text,re.M)
        return clean(match[1]) if match else ''
    corrected=sorted(set(re.findall(r'\(releng/[0-9.]+,\s*([0-9.]+-RELEASE(?:-p[0-9]+)?)\)',field('Corrected'))))
    module=field('Module').lower()
    # A whole-base comparison is conservative; module scope remains visible.
    if module in ('kern','kernel'):targets=('installed_kernel','running_kernel')
    elif module in ('libc','libcrypto','libssl','openssl','openssh','ssh','sshd','unbound','libarchive','fetch','ntp','ntpd','bzip2','xz','tar','libutil','rtsold'):targets=('userland',)
    else:targets=('installed_kernel','running_kernel','userland')
    entries=[entry('freebsd-base:'+target,'FreeBSD:base',{'native_type':'freebsd-base','corrected':corrected,'module':module,'target':target,'scope_confirmed':module in ('kern','kernel','libc','libcrypto','libssl','openssl','openssh','ssh','sshd','unbound','libarchive','fetch','ntp','ntpd','bzip2','xz','tar','libutil','rtsold')}) for target in targets]
    yield record(identifier[0],field('Topic'),entries,url,text,published=field('Announced') or None)


def proxmox(raw,url):
    tree=HTML(raw).root;count=0
    for article in tree.walk('article'):
        if article.attrs.get('data-author')!='ProxmoxSecurityAdvisory':continue
        bodies=[n for n in article.walk('div') if 'bbWrapper' in n.attrs.get('class','').split()]
        for body in bodies:
            text=body.text().replace('\u200b','');match=re.search(r'Subject:\s*(PSA-[0-9]{4}-[0-9]+-[0-9]+):\s*([^\n]+)',text)
            if not match:continue
            count+=1;entries=[];section='';major=None
            for line in text.splitlines():
                line=clean(line)
                if re.match(r'^(?:Not Fixed|Fixed(?: in)?|References|Details|Packages?\(s\)|Packages?):',line,re.I):section=line.split(':',1)[0].lower();major=None;continue
                if section=='not fixed':
                    missing=re.fullmatch(r'-?\s*([a-z0-9][a-z0-9+.*?-]*)',line)
                    if missing:entries.append(entry(missing[1],'Proxmox:VE',{'native_type':'unparsed','reason':'proxmox_vendor_no_fix'}))
                    continue
                if not section.startswith('fixed'):continue
                heading=re.search(r'Proxmox VE\s+([0-9]+)\.x',line,re.I)
                if heading:major=heading[1]
                m=re.fullmatch(r'-?\s*([a-z0-9][a-z0-9+.*?-]*)\s+(?:>=\s*)?([0-9][A-Za-z0-9.+:~_-]*)(?:\s*\(Proxmox VE ([0-9]+)\.x\))?',line)
                if not m:continue
                entries.append(entry(m[1],'Proxmox:VE',{'native_type':'proxmox','fixed_version':m[2],'major':m[3] or major}))
            # Preserve an unparsed bulletin as a platform-wide unknown finding.
            if not entries:entries=[entry('proxmox-platform','Proxmox:VE',{'native_type':'unparsed','reason':'proxmox_fix_rules_unparsed'})]
            date=re.search(r'Advisory date:\s*([0-9-]+)',text)
            yield record(match[1],match[2],entries,url+'#'+article.attrs.get('id',''),text,published=date[1] if date else None)
    if not count:raise ValueError('proxmox_advisories_not_found')


def table_rows(table):
    spans={};rows=[]
    for tr in table.walk('tr'):
        row={};next_spans={}
        for col,(value,left) in spans.items():
            row[col]=value
            if left>1:next_spans[col]=(value,left-1)
        col=0
        for cell in (c for c in tr.children if isinstance(c,Node) and c.tag in ('td','th')):
            while col in row:col+=1
            value=clean(cell.text());width=int(cell.attrs.get('colspan','1'));height=int(cell.attrs.get('rowspan','1'))
            if not 1<=width<=32 or not 1<=height<=1000:raise ValueError('vendor_table_span_limit')
            for pos in range(col,col+width):
                row[pos]=value
                if height>1:next_spans[pos]=(value,height-1)
            col+=width
        if row:rows.append([row.get(i,'') for i in range(max(row)+1)])
        spans=next_spans
    return rows


def esxi(raw,url):
    tree=HTML(raw).root;text=tree.text();identifier=re.search(r'VMSA-[0-9]{4}-[0-9]+(?:\.[0-9]+)?',text)
    if not identifier:raise ValueError('esxi_advisory_not_found')
    entries=[]
    for table in tree.walk('table'):
        rows=table_rows(table);header=None
        for row in rows:
            keys=[re.sub(r'\s+',' ',c).lower() for c in row]
            if 'fixed version' in keys and 'version' in keys and any(k in ('vmware product','product') for k in keys):header=keys;continue
            if header is None:continue
            cells=dict(zip(header,row));product=cells.get('vmware product',cells.get('product','')).strip()
            if not re.fullmatch(r'(?:VMware\s+)?ESXi?',product,re.I):continue
            fixed=cells.get('fixed version','');branch=cells.get('version','');cves=sorted(set(re.findall(r'CVE-[0-9]{4}-[0-9]+',cells.get('cve',''))))
            builds=[{'branch':m[1]+'.'+m[2]+'.'+(m[3] or '0'),'build':int(m[4]),'label':m[0]} for m in re.finditer(r'ESXi?([0-9])([0-9])(?:U([0-9]+)[a-z]*)?-([0-9]{5,})',fixed,re.I)]
            entries.append(entry('esxi-platform','VMware:ESXi',{'native_type':'esxi','affected_branch':branch,'fixed_builds':builds,'fixed_label':fixed,'running_on':cells.get('running on',''),'cves':cves}))
    grouped={}
    for item in entries:
        rule=item['database_specific'];key=(rule['affected_branch'],tuple(rule['cves']),rule['running_on'])
        if key in grouped:grouped[key]['database_specific']['fixed_builds'].extend(rule['fixed_builds'])
        else:grouped[key]=item
    entries=list(grouped.values())
    for item in entries:
        builds=item['database_specific']['fixed_builds']
        item['database_specific']['fixed_builds']=[{'branch':branch,'build':build,'label':label} for branch,build,label in sorted({(v['branch'],v['build'],v['label']) for v in builds})]
    if not entries:entries=[entry('esxi-platform','VMware:ESXi',{'native_type':'unparsed','reason':'esxi_response_matrix_unparsed'})]
    yield record(identifier[0],clean(text)[:512],entries,url,text[:65536])


def normalize(vendor,raw,url):
    if url.endswith('.bz2'):
        import bz2
        decoder=bz2.BZ2Decompressor();raw=decoder.decompress(raw,max_length=128*1024*1024+1)
        if not decoder.eof or decoder.unused_data or len(raw)>128*1024*1024:raise ValueError('vendor_xml_expansion_limit')
    if vendor=='freebsd':return vuxml(raw,url) if raw.lstrip().startswith(b'<?xml') or b'<vuxml' in raw[:8192] else freebsd_base(raw,url)
    if vendor=='proxmox':return proxmox(raw,url)
    if vendor=='esxi':return esxi(raw,url)
    raise ValueError('unsupported_native_vendor')


def scope_for(inventory):
    system=inventory['os'];kind=inventory['platform_details']['kind'];facts=inventory['platform_details']['facts']
    vendor='proxmox' if kind=='proxmox-ve' else {'freebsd':'freebsd','esxi':'esxi'}.get(system.get('id'))
    if vendor=='proxmox':version=(facts.get('manager_package_version') or '').split('.',1)[0];codename=''
    elif vendor=='freebsd':
        native=(facts.get('userland') or {}).get('version') or system.get('version_id','')
        m=re.match(r'([0-9]+\.[0-9]+)-',native);version=m[1] if m else '';codename=''
    elif vendor=='esxi':version=system.get('version_id','');codename=''
    else:return None,None
    return vendor,{'os_id':VENDORS[vendor],'version_id':version,'codename':codename}


def targets(inventory):
    kind=inventory['platform_details']['kind'];facts=inventory['platform_details']['facts'];result=list(inventory['packages'])
    def virtual(name,version):return {'name':name,'version':version or 'unknown','package_kind':'platform','architecture':inventory['os'].get('machine','unknown'),'installation_state':'installed','source_name':None,'source_version':None,'purl':None}
    if inventory['os'].get('id')=='freebsd':
        for name in ('installed_kernel','running_kernel','userland'):result.append(virtual('freebsd-base:'+name,(facts.get(name) or {}).get('version')))
    elif kind=='proxmox-ve':result.append(virtual('proxmox-platform',facts.get('manager_package_version')))
    elif inventory['os'].get('id')=='esxi':
        version=facts.get('system_version',{});result.append(virtual('esxi-platform',version.get('Version')))
    return result


def candidate(package,rule,inventory):
    native=rule.get('native_type');comp=[]
    if native=='unparsed':return 'unknown',rule['reason'],comp
    if native=='vuxml':
        groups=rule.get('ranges',[])
        if not groups:return 'unknown','vuxml_ranges_missing',comp
        if len(groups)>1000:return 'unknown','vuxml_range_limit',comp
        results=[]
        for group in groups:
            if not group:return 'unknown','vuxml_predicate_missing',comp
            if len(group)>128:return 'unknown','vuxml_predicate_limit',comp
            lower=upper=None;equal=None
            for p in group:
                op=p['operator'];version=p['version'];pkg_compare(version,version)
                if op in ('ge','gt') and (lower is None or pkg_compare(version,lower[0])>0 or pkg_compare(version,lower[0])==0 and op=='gt'):lower=(version,op)
                elif op in ('le','lt') and (upper is None or pkg_compare(version,upper[0])<0 or pkg_compare(version,upper[0])==0 and op=='lt'):upper=(version,op)
                elif op=='eq':
                    if equal is not None and pkg_compare(version,equal)!=0:return 'unknown','vuxml_contradictory_range',comp
                    equal=version
            if lower and upper:
                ordered=pkg_compare(lower[0],upper[0])
                if ordered>0 or ordered==0 and (lower[1]=='gt' or upper[1]=='lt'):return 'unknown','vuxml_contradictory_range',comp
            if equal is not None:
                if lower and (pkg_compare(equal,lower[0])<0 or pkg_compare(equal,lower[0])==0 and lower[1]=='gt'):return 'unknown','vuxml_contradictory_range',comp
                if upper and (pkg_compare(equal,upper[0])>0 or pkg_compare(equal,upper[0])==0 and upper[1]=='lt'):return 'unknown','vuxml_contradictory_range',comp
            checks=[]
            for p in group:
                value=pkg_compare(package['version'],p['version']);op=p['operator']
                if op not in ('lt','le','eq','gt','ge'):return 'unknown','vuxml_operator_unsupported',comp
                comp.append({'installed':package['version'],'boundary':p['version'],'operator':op,'result':value,'scheme':'freebsd-pkg'})
                checks.append({'lt':value<0,'le':value<=0,'eq':value==0,'gt':value>0,'ge':value>=0}[op])
            results.append(all(checks))
        return ('affected' if any(results) else 'not_affected'),'vuxml_native_range',comp
    if native=='freebsd-base':
        m=re.fullmatch(r'([0-9]+\.[0-9]+)-RELEASE(?:-p([0-9]+))?',package['version'])
        if not m:return 'unknown','freebsd_release_patch_identity_required',comp
        fixed=[v for v in rule['corrected'] if v.startswith(m[1]+'-RELEASE')]
        if len(fixed)!=1:return 'unknown','freebsd_corrected_branch_missing_or_ambiguous',comp
        patch=int(m[2] or 0);fixed_patch=int(re.search(r'-p([0-9]+)$',fixed[0])[1]) if '-p' in fixed[0] else 0
        comp=[{'installed':package['version'],'fixed':fixed[0],'result':(patch>fixed_patch)-(patch<fixed_patch),'scheme':'freebsd-release-patch','module':rule['module']}]
        if not rule['scope_confirmed']:return 'unknown','freebsd_module_scope_requires_review',comp
        return ('affected' if patch<fixed_patch else 'fixed'),'freebsd_corrected_release_patch',comp
    if native=='proxmox':
        version=inventory['platform_details']['facts'].get('manager_package_version','');major=version.split('.',1)[0]
        if rule.get('major') and rule['major']!=major:return 'unknown','proxmox_product_branch_mismatch',comp
        # Unqualified historical fixes are only ordered inside the same package major.
        if not rule.get('major') and package['version'].split(':')[-1].split('.')[0]!=rule['fixed_version'].split(':')[-1].split('.')[0]:return 'unknown','proxmox_package_branch_unconfirmed',comp
        value=debian(package['version'],rule['fixed_version']);comp=[{'installed':package['version'],'fixed':rule['fixed_version'],'result':value,'scheme':'deb'}]
        return ('affected' if value<0 else 'fixed'),'proxmox_vendor_fixed_version',comp
    if native=='esxi':
        facts=inventory['platform_details']['facts'].get('system_version',{});version=facts.get('Version','');build=re.fullmatch(r'(?:Releasebuild-|build-)?([0-9]+)',facts.get('Build',''))
        fixed=[v for v in rule['fixed_builds'] if v['branch']==version]
        if not rule.get('cves'):return 'unknown','esxi_cve_scope_missing',comp
        if rule.get('affected_branch') not in ('.'.join(version.split('.')[:2]),version.split('.')[0]+'.x',version):return 'unknown','esxi_affected_branch_mismatch',comp
        if rule.get('running_on','').lower()!='any':return 'unknown','esxi_runtime_scope_unconfirmed',comp
        if not build or len(fixed)!=1:return 'unknown','esxi_exact_update_branch_or_build_missing',comp
        value=int(build[1]);boundary=fixed[0];comp=[{'installed':version+'-'+build[1],'fixed':boundary['label'],'result':(value>boundary['build'])-(value<boundary['build']),'scheme':'esxi-same-update-build','branch':version}]
        return ('affected' if value<boundary['build'] else 'fixed'),'esxi_response_matrix_build',comp
    return 'unknown','native_rule_unsupported',comp


def matching(name,pattern):
    if len(pattern)>256:return False
    return fnmatch.fnmatchcase(name,pattern)


def acquire(vendor,scope,download,*,deadline=None,selected=()):
    """Bound official discovery and reads; keep incomplete acquisition explicit."""
    from .advisories import snapshot
    deadline=deadline or time.monotonic()+180;sources=[];inputs=[];gaps=[]
    def get(url,payload=None):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise ValueError('advisory_acquisition_deadline')
        return download(vendor,url,timeout=min(30,remaining),**({'payload':payload} if payload is not None else {}))
    def keep(url):
        raw,source=get(url);sources.append(source);inputs.append((raw,url));return raw
    if selected:
        urls=list(selected)
    elif vendor=='freebsd':
        raw=keep(VUXML)
        # Select official base SAs referenced by VuXML ranges for this exact release.
        # This avoids fetching hundreds of unrelated historical release advisories.
        candidates=[]
        for item in normalize(vendor,raw,VUXML):
            relevant=any(e['package']['name']=='FreeBSD' and any(re.match(re.escape(scope['version_id'])+r'(?:_|$)',p['version']) for group in e['database_specific']['ranges'] for p in group) for e in item['affected'])
            if relevant:candidates.extend(re.findall(r'<freebsdsa>(SA-[0-9]{2}:[0-9]+\.[a-z0-9_]+)</freebsdsa>',item['details']))
        urls=[FREEBSD_INDEX+'FreeBSD-'+identifier+'.asc' for identifier in dict.fromkeys(candidates)]
        if not urls:gaps.append('freebsd_release_base_advisory_mapping_missing')
    elif vendor=='proxmox':
        raw=keep(PVE_THREAD);tree=HTML(raw).root
        pages=[int(m[1]) for n in tree.walk('a') if (m:=re.search(r'/page-([0-9]+)$',n.attrs.get('href','')))]
        last=max(pages or [1])
        if last>100:raise ValueError('proxmox_page_limit')
        urls=[PVE_THREAD+'page-'+str(i) for i in range(2,last+1)]
    else:
        from .advisories import parse
        urls=[];page=0
        while True:
            raw,source=get(ESXI_INDEX,{'pageNumber':page,'pageSize':100,'searchVal':'','segment':'VC','sortInfo':None});sources.append(source)
            try:value=parse(raw)
            except ValueError:raise ValueError('esxi_advisory_index_unavailable') from None
            if not isinstance(value,dict):raise ValueError('esxi_advisory_index_unavailable')
            if value.get('success') is not True or not isinstance(value.get('data'),dict):raise ValueError('esxi_advisory_index_unavailable')
            data=value['data'];info=data.get('pageInfo',{});items=data.get('list')
            if not isinstance(items,list) or type(info.get('lastPage')) is not int or info.get('currentPage')!=page or info['lastPage']>99:raise ValueError('esxi_advisory_index_unavailable')
            for item in items:
                if not isinstance(item,dict):raise ValueError('esxi_advisory_index_unavailable')
                if re.search(r'\bESXi?\b',item.get('title',''),re.I):
                    url=item.get('notificationUrl','')
                    from .advisories import validate_url
                    validate_url(vendor,url);urls.append(url)
            if page==info['lastPage']:break
            page+=1
        urls=list(dict.fromkeys(urls))
        if not urls:raise ValueError('esxi_advisory_index_unavailable')
    if len(urls)>MAX_DOCUMENTS:gaps.append('vendor_discovery_document_limit');urls=urls[:MAX_DOCUMENTS]
    # Small parallel public reads share one total deadline; no retries.
    retained_bytes=sum(len(raw) for raw,_ in inputs)
    with ThreadPoolExecutor(max_workers=8) as pool:
        pending={pool.submit(get,url):url for url in urls}
        for future in as_completed(pending):
            url=pending[future]
            try:
                raw,source=future.result();sources.append(source);retained_bytes+=len(raw)
                if retained_bytes>256*1024*1024:gaps.append('vendor_acquisition_total_byte_limit');continue
                inputs.append((raw,url))
            except Exception:gaps.append('vendor_advisory_document_acquisition_failed')
    accepted=[];total=0
    for raw,url in inputs:
        total+=len(raw)
        if total>256*1024*1024:gaps.append('vendor_acquisition_total_byte_limit');break
        try:list(normalize(vendor,raw,url));accepted.append((raw,url))
        except (ValueError,ET.ParseError,UnicodeError):gaps.append('vendor_advisory_parse_failed')
    result=snapshot(vendor,scope,sources,accepted)
    result['coverage_gaps']=sorted(set(gaps));result['coverage']='Official discovered/provided advisories only; absent records are unknown; discovery, parsing and branch limits are explicit.'
    from .advisories import digest,load
    result['snapshot_sha256']=digest({k:v for k,v in result.items() if k!='snapshot_sha256'})
    return load(result)
