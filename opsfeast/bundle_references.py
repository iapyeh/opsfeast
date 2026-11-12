"""Bounded static resource hints, never an HTML/JS evaluator or network fetcher."""
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlsplit


class References(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.imports={};self.script=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        for key in ('src','href','poster'):
            if key in attrs:self.links.append(attrs[key])
        if tag=='script':self.script=attrs.get('type','');self.text=[]
    def handle_data(self,data):
        if self.script is not None:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:
            value=''.join(self.text)
            if self.script=='importmap':
                try:
                    mapping=json.loads(value).get('imports',{})
                    if isinstance(mapping,dict):self.imports.update({k:v for k,v in mapping.items() if isinstance(k,str) and isinstance(v,str)})
                except (ValueError,AttributeError):pass
            else:self.links.extend(js_references(value))
            self.script=None


def js_references(text):return re.findall(r'''(?:\bfrom\s*|\bimport\s*|\bimport\(\s*|\bfetch\(\s*)['"]([^'"\r\n]+)['"]''',text)


def inspect(files,entry):
    from .note_bundles import relative_path,MAX_ENTRY
    warnings=[];imports={};references=[];budget=4*1024*1024
    html=References()
    if entry.lower().endswith(('.html','.htm')):
        html.feed(files[entry].decode('utf-8-sig'));imports=html.imports
    for name,data in files.items():
        suffix=name.rsplit('.',1)[-1].lower()
        if suffix not in ('html','htm','js','mjs','css'):continue
        if len(data)>MAX_ENTRY or len(data)>budget:
            warnings.append({'file':name,'reference':'','reason':'scan_limit'});continue
        budget-=len(data)
        try:text=data.decode('utf-8-sig')
        except UnicodeError:
            warnings.append({'file':name,'reference':'','reason':'non_utf8_resource'});continue
        if suffix in ('html','htm'):
            parser=html if name==entry else References()
            if name!=entry:parser.feed(text)
            references.extend((name,ref) for ref in parser.links)
        elif suffix in ('js','mjs'):references.extend((name,ref) for ref in js_references(text))
        else:references.extend((name,ref.strip(' \t\'"')) for ref in re.findall(r'url\(([^)]+)\)',text))
    seen=set()
    for name,value in references:
        if not value or value.startswith('#'):continue
        reference=value;origin=name
        try:urlsplit(value)
        except ValueError:
            warnings.append({'file':name,'reference':value[:500],'reason':'invalid_reference'});continue
        if value in imports:value=imports[value];origin=entry
        elif not value.startswith(('./','../','/')) and not urlsplit(value).scheme:
            prefix=next((key for key in sorted(imports,key=len,reverse=True) if key.endswith('/') and value.startswith(key)),None)
            if prefix:value=imports[prefix]+value[len(prefix):];origin=entry
        reason=None
        try:parsed=urlsplit(value)
        except ValueError:reason='invalid_reference';parsed=None
        if parsed is None:pass
        elif parsed.scheme or value.startswith('//'):reason='external_or_embedded'
        else:
            try:
                path,_=relative_path(origin,value)
                if path not in files:reason='missing_file'
            except ValueError:reason='outside_bundle'
        if reason:
            item=(name,reference[:500],reason)
            if item not in seen:
                seen.add(item);warnings.append(dict(zip(('file','reference','reason'),item)))
        if len(warnings)>=256:break
    return warnings[:256]
