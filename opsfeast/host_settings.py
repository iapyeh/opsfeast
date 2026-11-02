"""Host configuration editing 0.1.0; no connections or remote effects."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import uuid

from . import ConfigError,Validator,read_yaml,group_names
from .core import Instance
from .identity import _locked
from .site import SiteConflict,_atomic

VERSION='0.1.0'
CONNECTION_FIELDS={'hostname','port','user','identity_file','allow_agent','look_for_keys','ssh_config_alias','local','via'}

class HostSettingsError(ConfigError):
    def __init__(self,code):self.code=code;super().__init__(code)

def _text(value,limit=200):
    if not isinstance(value,str) or not value.strip() or value!=value.strip() or len(value)>limit or any(ord(c)<32 for c in value):raise HostSettingsError('invalid_host_input')
    try:value.encode('utf-8')
    except UnicodeError:raise HostSettingsError('invalid_host_input') from None
    return value

class _TextDocument:
    def __init__(self,path,text):self.path=path;self.text=text
    def read_text(self,encoding='utf-8'):return self.text
    def __str__(self):return str(self.path)

class _Candidate(Validator):
    def __init__(self,root,path,text):super().__init__(root);self.changed=path;self.text=text
    def read_document(self,path):return read_yaml(_TextDocument(path,self.text)) if path==self.changed else super().read_document(path)

def _load(installation,profile):
    _text(profile,80)
    selected=Instance.open(installation).profile(profile)
    config=selected.hosts._config
    files={path:path.read_bytes() for path in config.documents}
    if any(read_yaml(_TextDocument(path,content.decode('utf-8')))!=config.documents[path] for path,content in files.items()):raise SiteConflict('host configuration changed while reading')
    return selected,config,files

def _revision(selected,files):
    digest=hashlib.sha256(str(selected.root).encode())
    for path,content in sorted(files.items()):
        digest.update(str(path.relative_to(selected.root)).encode()+b'\x00'+len(content).to_bytes(8,'big')+content)
    return digest.hexdigest()

def _definition(document,host_id):
    ordinary=document.get('hosts',{})
    if host_id in ordinary:return ordinary,None
    for name,group in document.get('groups',{}).items():
        if host_id in group.get('hosts',{}):return group['hosts'],name
    raise HostSettingsError('host_definition_missing')

def _edit_document(document,action,host_id,changes):
    if action=='create':
        document.setdefault('hosts',{})[host_id]=deepcopy(changes)
        return
    owner,_=_definition(document,host_id)
    if action=='delete':del owner[host_id];return
    for key,value in changes.items():
        if key=='connection':
            for field,item in value.items():
                if item is None:owner[host_id][key].pop(field,None)
                else:owner[host_id][key][field]=deepcopy(item)
        else:owner[host_id][key]=deepcopy(value)

def inspect(installation,*,profile):
    selected,config,files=_load(installation,profile)
    rows=[]
    from management_view import user_accounts
    for host_id,value in config.hosts.items():
        connection=value['connection']
        safe={key:deepcopy(value) for key,value in connection.items() if key in CONNECTION_FIELDS and key!='via'}
        via=connection.get('via')
        if isinstance(via,dict) and set(via)=={'host'}:safe['via']=deepcopy(via)
        _,parent=_definition(config.documents[config.sources[host_id]],host_id)
        login,users=user_accounts(value)
        try:ips=selected.hosts.reference_ips(host_id)
        except (ConfigError,ValueError,OSError):ips={'status':'unknown','ipv4_addresses':[],'ipv6_addresses':[],'observed_at':None}
        rows.append({'host_id':host_id,'source':config.sources[host_id].relative_to(selected.root).as_posix(),
            'parent_group':parent,'groups':list(dict.fromkeys(group_names(value.get('group',[]),'host group'))),
            'enabled':value.get('enabled',True),'label':value.get('label',''),'description':value.get('description',''),
            'connection':safe,'advanced_connection':bool(set(connection)-CONNECTION_FIELDS) or ('via' in connection and 'via' not in safe),
            'login_user':login,'users':[{'name':name,'sudo':value.get('users',{}).get(name,{}).get('sudo',True)} for name in users],
            'recipe_references':list(value.get('recipes',{})) if isinstance(value.get('recipes',{}),dict) else [],
            'reference_ips':{key:ips.get(key) for key in ('status','ipv4_addresses','ipv6_addresses','observed_at')}})
    return {'schema_version':VERSION,'profile':profile,'revision':_revision(selected,files),
            'groups':[{'id':name,'label':value.get('label',name)} for name,value in config.groups.items()],
            'hosts':rows,'connectivity_verified':False}

def _connection(value,*,create):
    if not isinstance(value,dict) or set(value)-CONNECTION_FIELDS:raise HostSettingsError('unsupported_connection_fields')
    if 'via' in value and not (value['via'] is None and not create) and (not isinstance(value['via'],dict) or set(value['via'])!={'host'}):raise HostSettingsError('unsupported_connection_fields')
    if any(item is None and (create or key not in ('via','identity_file','user')) for key,item in value.items()):raise HostSettingsError('unsupported_connection_fields')
    # Switching connection modes is explicit only when creating a host.
    if not create and 'local' in value:raise HostSettingsError('connection_mode_change_unsupported')
    return deepcopy(value)

def _changes(value,*,create=False):
    allowed={'connection','group','enabled','label','description'}
    if not isinstance(value,dict) or not value or set(value)-allowed:raise HostSettingsError('unsupported_host_fields')
    clean=deepcopy(value)
    if create and 'connection' not in clean:raise HostSettingsError('connection_required')
    if 'connection' in clean:clean['connection']=_connection(clean['connection'],create=create)
    if 'group' in clean:
        clean['group']=list(dict.fromkeys(group_names(clean['group'],'host group')))
        for name in clean['group']:_text(name)
    if 'enabled' in clean and type(clean['enabled']) is not bool:raise HostSettingsError('invalid_host_input')
    for key in ('label','description'):
        if key in clean and (not isinstance(clean[key],str) or len(clean[key])>4000 or '\x00' in clean[key]):raise HostSettingsError('invalid_host_input')
    return clean

def mutate(installation,*,profile,action,host_id,expected_revision,changes=None,confirmation=None):
    """Edit one source, check the whole profile, back up original bytes, then replace."""
    _text(host_id)
    if action not in ('create','update','delete'):raise HostSettingsError('unknown_host_action')
    if action=='delete' and confirmation!=host_id:raise HostSettingsError('host_confirmation_required')
    clean=_changes(changes,create=action=='create') if action!='delete' else None
    installation=Path(installation).resolve(strict=True)
    with _locked(installation/'.opsfeast-profiles.json'):
        selected,_,_=_load(installation,profile)
        with _locked(selected.root/'.opsfeast-host-settings.json'):
            selected,config,files=_load(installation,profile)
            before=_revision(selected,files)
            if expected_revision!=before:raise SiteConflict('host configuration changed; reload before saving')
            exists=host_id in config.hosts
            if action=='create' and exists:raise HostSettingsError('host_already_exists')
            if action!='create' and not exists:raise HostSettingsError('host_not_found')
            source=selected.root/'hosts.yaml' if action=='create' else config.sources[host_id]
            if source.is_symlink() or not source.is_file():raise HostSettingsError('invalid_host_source')
            raw=files[source]
            import yaml
            # Aliases can share mutable nodes; refuse rather than changing other hosts.
            if any(isinstance(token,(yaml.tokens.AnchorToken,yaml.tokens.AliasToken)) for token in yaml.scan(raw.decode('utf-8'))):raise HostSettingsError('yaml_alias_edit_unsupported')
            from ruamel.yaml import YAML
            from ruamel.yaml.error import YAMLError
            editor=YAML(typ='rt');editor.preserve_quotes=True;editor.version=(1,1)
            try:
                document=editor.load(raw.decode('utf-8'))
                _edit_document(document,action,host_id,clean)
                output=io.StringIO();editor.dump(document,output);candidate=output.getvalue()
            except YAMLError:raise HostSettingsError('yaml_roundtrip_unsupported') from None
            expected=deepcopy(config.documents[source])
            _edit_document(expected,action,host_id,clean)
            if read_yaml(_TextDocument(source,candidate))!=expected:raise HostSettingsError('yaml_semantics_changed')
            if action=='delete' and any(host_id in targets for targets in config.edges.values()):raise HostSettingsError('host_is_jump_dependency')
            try:_Candidate(selected.root,source,candidate).check()
            except ConfigError:raise HostSettingsError('candidate_configuration_invalid') from None
            # Recheck every source immediately before committing; non-cooperating writers
            # are not an OS-level lock, and must not be silently overwritten.
            if any(path.read_bytes()!=content for path,content in files.items()):raise SiteConflict('host configuration changed while preparing save')
            backups=selected.root/'.host-settings-backups'
            if backups.is_symlink() or (backups.exists() and not backups.is_dir()):raise HostSettingsError('invalid_backup_directory')
            backups.mkdir(mode=0o700,exist_ok=True)
            backup_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+str(uuid.uuid4())
            backup=backups/backup_id;backup.mkdir(mode=0o700)
            _atomic(backup/'original.yaml',raw)
            after_files=dict(files);after_files[source]=candidate.encode('utf-8')
            revision=_revision(selected,after_files)
            receipt={'schema_version':VERSION,'action':action,'profile':profile,'host_id':host_id,
                     'source':source.relative_to(selected.root).as_posix(),'previous_revision':before,'revision':revision,
                     'backup_id':backup_id,'backup_kind':'pre-change','changed_at':datetime.now(timezone.utc).isoformat(),'remote_effects':False}
            _atomic(backup/'receipt.json',(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode())
            _atomic(source,candidate.encode('utf-8'))
            return dict(receipt,configuration_changed=True)

def main():
    import argparse,sys
    parser=argparse.ArgumentParser(description='Inspect/edit local host configuration; never connects. Passwords are not accepted by this interface.')
    parser.add_argument('--installation',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--profile',required=True)
    commands=parser.add_subparsers(dest='action',required=True)
    commands.add_parser('list')
    for action in ('create','update','delete'):
        command=commands.add_parser(action);command.add_argument('host_id');command.add_argument('--expected-revision',required=True)
        if action=='delete':command.add_argument('--confirm-host',required=True)
    args=parser.parse_args()
    try:
        if args.action=='list':result=inspect(args.installation,profile=args.profile)
        else:
            body=sys.stdin.read(65537) if args.action!='delete' else None
            if body is not None and len(body)>65536:raise HostSettingsError('request_too_large')
            result=mutate(args.installation,profile=args.profile,action=args.action,host_id=args.host_id,
                          expected_revision=args.expected_revision,changes=json.loads(body) if body is not None else None,
                          confirmation=getattr(args,'confirm_host',None))
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ConfigError,OSError,ValueError,ImportError) as error:
        code=error.code if isinstance(error,HostSettingsError) else 'revision_conflict' if isinstance(error,SiteConflict) else 'host_configuration_unavailable'
        print(json.dumps({'error':code}));return 1

if __name__=='__main__':raise SystemExit(main())
