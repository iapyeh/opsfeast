"""Immutable Profile-local host-note document bundles 0.1.0; no execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from urllib.parse import unquote, urlsplit
from uuid import uuid4
import zipfile

from . import ConfigError, host_notes as notes
from .identity import _locked
from .site import _atomic

VERSION='0.1.0'
DIRECTORY='.host-note-attachments'
MAX_ARCHIVE=65*1024*1024
MAX_TOTAL=64*1024*1024
MAX_FILE=16*1024*1024
MAX_FILES=256
MAX_ATTACHMENTS=32
MAX_ENTRY=2*1024*1024


class BundleError(ConfigError):
    def __init__(self,code):self.code=code;super().__init__(code)


def fail(code):raise BundleError(code)


def safe_path(value):
    if (not isinstance(value,str) or not value or len(value)>500 or value.startswith('/')
            or '\\' in value or ':' in value or '%' in value or '?' in value or '#' in value
            or any(ord(c)<32 or ord(c)==127 for c in value)
            or any(part in ('','.','..') or part.startswith('.') for part in value.split('/'))):
        fail('invalid_bundle_path')
    reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
    if any(part.rstrip(' .')!=part or part.split('.')[0].upper() in reserved for part in value.split('/')):fail('invalid_bundle_path')
    return value


def _base(selected,create=False):
    root=selected.root/DIRECTORY
    if root.is_symlink() or (root.exists() and not root.is_dir()):fail('bundle_storage_invalid')
    if create:root.mkdir(mode=0o700,exist_ok=True)
    return root


def _folder(selected,identifier):
    notes._uuid(identifier)
    root=_base(selected)/identifier
    if root.is_symlink() or not root.is_dir():fail('bundle_not_found')
    return root


def _regular(root,name):
    safe_path(name)
    if root.is_symlink() or not root.is_dir():fail('bundle_storage_invalid')
    path=root
    for part in PurePosixPath(name).parts:
        path=path/part
        if path.is_symlink():fail('bundle_storage_invalid')
    if not path.is_file():fail('bundle_file_not_found')
    return path


def validate_references(values):
    if not isinstance(values,list) or len(values)>MAX_ATTACHMENTS:fail('invalid_bundle_metadata')
    ids=set()
    for value in values:
        if not isinstance(value,dict) or set(value)!={'uuid','title','entry','kind','file_count','bytes','sha256','created_at'}:fail('invalid_bundle_metadata')
        notes._uuid(value['uuid']);notes._text(value['title'],200);safe_path(value['entry'])
        if (value['uuid'] in ids or value['kind'] not in ('markdown','html') or type(value['file_count']) is not int
                or not 1<=value['file_count']<=MAX_FILES or type(value['bytes']) is not int or not 0<value['bytes']<=MAX_TOTAL
                or not isinstance(value['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',value['sha256'])):fail('invalid_bundle_metadata')
        stamp=datetime.fromisoformat(value['created_at'])
        if stamp.utcoffset() is None or stamp.isoformat(timespec='seconds')!=value['created_at']:fail('invalid_bundle_metadata')
        ids.add(value['uuid'])
    return values


def unpack(content):
    if not isinstance(content,bytes) or len(content)>MAX_ARCHIVE:fail('bundle_archive_too_large')
    result={};total=0;seen=set()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if len(archive.infolist())>MAX_FILES*2:fail('bundle_too_many_files')
            for item in archive.infolist():
                if item.orig_filename!=item.filename:fail('invalid_bundle_path')
                name=safe_path(item.filename.rstrip('/') if item.is_dir() else item.filename)
                mode=item.external_attr>>16
                if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)) or item.flag_bits&1:fail('invalid_bundle_archive')
                if name.casefold() in seen:fail('duplicate_bundle_path')
                seen.add(name.casefold())
                if item.is_dir():continue
                if item.file_size>MAX_FILE or item.file_size>max(1,item.compress_size)*200:fail('bundle_expansion_limit')
                total+=item.file_size
                if total>MAX_TOTAL or len(result)>=MAX_FILES:fail('bundle_expansion_limit')
                with archive.open(item) as source:data=source.read(MAX_FILE+1)
                if len(data)!=item.file_size or len(data)>MAX_FILE:fail('bundle_expansion_limit')
                result[name]=data
    except BundleError:raise
    except (zipfile.BadZipFile,RuntimeError,NotImplementedError,OSError,ValueError):fail('invalid_bundle_archive')
    return _files(result)


def _files(files):
    if not isinstance(files,dict) or not 1<=len(files)<=MAX_FILES:fail('bundle_too_many_files')
    seen=set();total=0
    for name,data in files.items():
        safe_path(name)
        if name.casefold() in seen:fail('duplicate_bundle_path')
        seen.add(name.casefold())
        if not isinstance(data,bytes) or len(data)>MAX_FILE:fail('bundle_file_too_large')
        total+=len(data)
        if total>MAX_TOTAL:fail('bundle_expansion_limit')
    # A path may not be both a file and a parent directory.
    for name in files:
        if any('/'.join(name.split('/')[:i]).casefold() in seen for i in range(1,len(name.split('/')))):fail('invalid_bundle_path')
    if not total:fail('invalid_bundle_archive')
    return files


def read_directory(directory):
    root=Path(directory)
    if root.is_symlink() or not root.is_dir():fail('invalid_bundle_directory')
    result={}
    def unavailable(error):raise error
    for current,dirs,files in os.walk(root,followlinks=False,onerror=unavailable):
        for name in dirs:
            path=Path(current)/name
            if path.is_symlink():fail('invalid_bundle_path')
            safe_path(path.relative_to(root).as_posix())
        for name in files:
            path=Path(current)/name
            if path.is_symlink() or not path.is_file():fail('invalid_bundle_path')
            if path.stat().st_size>MAX_FILE:fail('bundle_file_too_large')
            result[path.relative_to(root).as_posix()]=path.read_bytes()
            if len(result)>MAX_FILES or sum(map(len,result.values()))>MAX_TOTAL:fail('bundle_expansion_limit')
    return _files(result)


def _record(installation,profile,host_id,note_uuid,bundle_uuid=None):
    selected=notes._selected(installation,profile);data,revision=notes._read(selected)
    notes._uuid(note_uuid)
    note=next((n for n in data['notes'] if n['uuid']==note_uuid and n['host_id']==host_id),None)
    if note is None:fail('note_not_found')
    if bundle_uuid is None:return selected,data,revision,note
    notes._uuid(bundle_uuid)
    reference=next((r for r in note.get('attachments',[]) if r['uuid']==bundle_uuid),None)
    if reference is None:fail('bundle_not_found')
    return selected,data,revision,note,reference


def _manifest(selected,reference):
    root=_folder(selected,reference['uuid']);path=_regular(root,'manifest.json')
    if path.stat().st_size>256*1024:fail('bundle_storage_invalid')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=reference['sha256']:fail('bundle_digest_mismatch')
    try:manifest=json.loads(raw)
    except (ValueError,UnicodeError):fail('bundle_storage_invalid')
    if not isinstance(manifest,dict) or set(manifest)!={'schema_version','entry','kind','files','warnings'} or manifest['schema_version']!=VERSION or manifest['entry']!=reference['entry'] or manifest['kind']!=reference['kind']:fail('bundle_storage_invalid')
    items=manifest['files']
    if not isinstance(items,list) or len(items)!=reference['file_count']:fail('bundle_storage_invalid')
    seen=set();total=0
    for item in items:
        if not isinstance(item,dict) or set(item)!={'path','bytes','sha256'}:fail('bundle_storage_invalid')
        safe_path(item['path'])
        if item['path'].casefold() in seen or type(item['bytes']) is not int or not 0<=item['bytes']<=MAX_FILE or not isinstance(item['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',item['sha256']):fail('bundle_storage_invalid')
        seen.add(item['path'].casefold());total+=item['bytes']
    if total!=reference['bytes'] or manifest['entry'].casefold() not in seen:fail('bundle_storage_invalid')
    if not isinstance(manifest['warnings'],list) or len(manifest['warnings'])>256:fail('bundle_storage_invalid')
    for warning in manifest['warnings']:
        if not isinstance(warning,dict) or set(warning)!={'file','reference','reason'} or any(not isinstance(value,str) or len(value)>500 for value in warning.values()):fail('bundle_storage_invalid')
    return root,manifest


def inspect(installation,*,profile,host_id,note_uuid,bundle_uuid):
    selected,_,revision,_,reference=_record(installation,profile,host_id,note_uuid,bundle_uuid)
    _,manifest=_manifest(selected,reference)
    return {'schema_version':VERSION,'profile':profile,'host_id':host_id,'note_uuid':note_uuid,'revision':revision,'bundle':reference,'files':manifest['files'],'warnings':manifest['warnings']}


def read_file(installation,*,profile,host_id,note_uuid,bundle_uuid,path):
    safe_path(path)
    selected,_,_,_,reference=_record(installation,profile,host_id,note_uuid,bundle_uuid)
    root,manifest=_manifest(selected,reference)
    metadata=next((f for f in manifest['files'] if f['path']==path),None)
    if metadata is None:fail('bundle_file_not_found')
    file=_regular(root/'files',path)
    if file.stat().st_size!=metadata['bytes'] or file.stat().st_size>MAX_FILE:fail('bundle_digest_mismatch')
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=metadata['sha256']:fail('bundle_digest_mismatch')
    return raw


def create(installation,*,profile,host_id,note_uuid,expected_revision,title,entry,files=None,archive=None,source=None):
    """Copy reviewed files/ZIP/directory into one immutable attachment; never execute."""
    if sum(value is not None for value in (files,archive,source))!=1:fail('invalid_bundle_input')
    if source is not None:
        path=Path(source)
        if path.is_symlink():fail('invalid_bundle_path')
        if path.is_dir():files=read_directory(path)
        else:
            if not path.is_file() or path.stat().st_size>MAX_ARCHIVE:fail('bundle_archive_too_large')
            archive=path.read_bytes()
    files=unpack(archive) if archive is not None else _files(files)
    notes._text(title,200);safe_path(entry)
    if entry not in files:fail('bundle_entry_missing')
    suffix=PurePosixPath(entry).suffix.lower();kind='markdown' if suffix=='.md' else 'html' if suffix in ('.html','.htm') else None
    if kind is None or len(files[entry])>MAX_ENTRY:fail('invalid_bundle_entry')
    try:files[entry].decode('utf-8')
    except UnicodeError:fail('bundle_entry_requires_utf8')
    manifest={'schema_version':VERSION,'entry':entry,'kind':kind,'files':[{'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in sorted(files.items())]}
    from .bundle_references import inspect as inspect_references
    manifest['warnings']=inspect_references(files,entry)
    raw=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    reference={'uuid':str(uuid4()),'title':title,'entry':entry,'kind':kind,'file_count':len(files),'bytes':sum(map(len,files.values())),'sha256':hashlib.sha256(raw).hexdigest(),'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    installation=Path(installation).resolve(strict=True)
    with _locked(installation/'.opsfeast-profiles.json'):
        selected=notes._selected(installation,profile)
        with _locked(selected.root/notes.FILENAME):
            _,data,revision,note=_record(installation,profile,host_id,note_uuid)
            if revision!=expected_revision:notes._fail('note_revision_conflict')
            if len(note.get('attachments',[]))>=MAX_ATTACHMENTS:fail('bundle_attachment_limit')
            base=_base(selected,create=True);target=base/reference['uuid']
            staging=Path(tempfile.mkdtemp(prefix='.upload-',dir=base))
            try:
                for name,content in files.items():
                    file=staging/'files'/name;file.parent.mkdir(parents=True,mode=0o700,exist_ok=True);_atomic(file,content)
                _atomic(staging/'manifest.json',raw)
                os.rename(staging,target)
                note['attachments']=[*note.get('attachments',[]),reference]
                note['timestamp']=datetime.now(timezone.utc).isoformat(timespec='seconds')
                committed_revision=notes._save(selected,data,revision)
            except BaseException:
                # An interrupted/uncertain write may already have linked the new
                # bytes. Remove them only when a fresh read proves no reference.
                try:
                    latest,_=notes._read(selected)
                    linked=any(r['uuid']==reference['uuid'] for n in latest['notes'] for r in n.get('attachments',[]))
                except (ConfigError,OSError):linked=True
                if target.exists() and not linked:shutil.rmtree(target)
                raise
            finally:
                if staging.exists():shutil.rmtree(staging)
    return {'schema_version':VERSION,'profile':profile,'host_id':host_id,'note_uuid':note_uuid,'revision':committed_revision,'bundle':reference,'files':manifest['files'],'warnings':manifest['warnings']}


def cleanup(selected,references):
    """Delete only exact unreferenced immutable bundle IDs after metadata commit."""
    result={'deleted':[],'failed':[]}
    for reference in references:
        identifier=reference['uuid']
        try:
            root=_folder(selected,identifier);shutil.rmtree(root);result['deleted'].append(identifier)
        except (OSError,ConfigError):result['failed'].append(identifier)
    return result


def delete(installation,*,profile,host_id,note_uuid,bundle_uuid,expected_revision,confirmation):
    if confirmation!=bundle_uuid:fail('bundle_confirmation_required')
    installation=Path(installation).resolve(strict=True)
    with _locked(installation/'.opsfeast-profiles.json'):
        selected=notes._selected(installation,profile)
        with _locked(selected.root/notes.FILENAME):
            _,data,revision,note,reference=_record(installation,profile,host_id,note_uuid,bundle_uuid)
            if revision!=expected_revision:notes._fail('note_revision_conflict')
            note['attachments']=[r for r in note['attachments'] if r['uuid']!=bundle_uuid]
            note['timestamp']=datetime.now(timezone.utc).isoformat(timespec='seconds')
            revision=notes._save(selected,data,revision)
            receipt=cleanup(selected,[reference])
    return {'schema_version':VERSION,'revision':revision,'deleted':bundle_uuid,'cleanup':receipt}


def export(installation,**scope):
    state=inspect(installation,**scope);stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for item in state['files']:archive.writestr(item['path'],read_file(installation,**scope,path=item['path']))
    return stream.getvalue()


def relative_path(entry,url):
    """Resolve a document link within its bundle, never a filesystem/remote URL."""
    parsed=urlsplit(url)
    if parsed.scheme or parsed.netloc or url.startswith(('/','\\')):fail('external_bundle_reference')
    value=unquote(parsed.path)
    if not value:return safe_path(entry),parsed.fragment
    parts=list(PurePosixPath(entry).parent.parts)
    for part in value.split('/'):
        if part in ('','.'):continue
        if part=='..':
            if not parts:fail('invalid_bundle_path')
            parts.pop()
        else:parts.append(part)
    return safe_path('/'.join(parts)),parsed.fragment


def main(argv=None):
    parser=argparse.ArgumentParser(description='Manage private host-note document bundles. Copies local files only; never executes HTML, connects hosts or fetches libraries.')
    parser.add_argument('--installation',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--profile',required=True);parser.add_argument('--host',required=True);parser.add_argument('--note',required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    for action in ('add','show','export','delete'):
        command=sub.add_parser(action)
        if action=='add':
            command.add_argument('--source',type=Path,required=True);command.add_argument('--title',required=True);command.add_argument('--entry',required=True)
        else:command.add_argument('bundle_uuid')
        if action in ('add','delete'):command.add_argument('--expected-revision',required=True)
        if action=='delete':command.add_argument('--confirm',required=True)
        if action=='export':command.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv);scope=dict(profile=args.profile,host_id=args.host,note_uuid=args.note)
    try:
        if args.action=='add':result=create(args.installation,**scope,source=args.source,title=args.title,entry=args.entry,expected_revision=args.expected_revision)
        elif args.action=='delete':result=delete(args.installation,**scope,bundle_uuid=args.bundle_uuid,expected_revision=args.expected_revision,confirmation=args.confirm)
        elif args.action=='export':
            raw=export(args.installation,**scope,bundle_uuid=args.bundle_uuid)
            with args.output.open('xb') as target:target.write(raw)
            result={'exported':True,'bytes':len(raw)}
        else:result=inspect(args.installation,**scope,bundle_uuid=args.bundle_uuid)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ConfigError,OSError,ValueError) as error:
        print(json.dumps({'error':getattr(error,'code','bundle_request_failed')}));return 1


if __name__=='__main__':raise SystemExit(main())
