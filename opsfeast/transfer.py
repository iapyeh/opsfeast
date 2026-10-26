"""Independent portable data units, immutable packages and recoverable archive plans.

All effects are local. Import never executes recipes, normalizers or consumers.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import copy
import hashlib
import json
import os
import io
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
from uuid import uuid4, UUID
import zipfile

from opsfeast import ConfigError
from .data_contract import canonical, validate as validate_data

VERSION = '0.1.0'
MAX_FILES = 20000
MAX_BYTES = 512 * 1024 * 1024
KINDS = ('observation', 'retention')


def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else canonical(value).encode()).hexdigest()


def document(content):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ConfigError('duplicate portable JSON key')
            result[key]=value
        return result
    try:
        return json.loads(content,object_pairs_hook=unique,parse_constant=lambda v: (_ for _ in ()).throw(ConfigError('nonfinite JSON')))
    except (ValueError, UnicodeError, RecursionError):
        raise ConfigError('invalid portable JSON document') from None


def relative(value):
    if (not isinstance(value,str) or not value or '\\' in value or ':' in value or '\x00' in value
            or any(p in ('','.','..') for p in value.split('/')) or PurePosixPath(value).is_absolute()):
        raise ConfigError('unsafe portable relative path')
    return value


def checked(root, name):
    root=Path(root).resolve(strict=True)
    target=root/relative(name)
    for path in (target,*target.parents):
        if path == root:
            break
        if path.is_symlink():
            raise ConfigError('transfer refuses symlink paths')
    if not target.resolve().is_relative_to(root):
        raise ConfigError('transfer path escapes profile')
    return target


def atomic(path, content):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.transfer-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(content if isinstance(content,bytes) else canonical(content).encode())
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


@contextmanager
def locked(root):
    import fcntl
    path=checked(root,'transfer/.lock');path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


@contextmanager
def database(root, write=False):
    path=checked(root,'transfer/space.sqlite3')
    if any(Path(str(path)+suffix).is_symlink() for suffix in ('-journal','-wal','-shm')):raise ConfigError('portable SQLite sidecar symlink refused')
    if not path.exists() and not write:
        yield None
        return
    if write:
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600);os.close(fd)
    db=sqlite3.connect(str(path) if write else path.as_uri()+'?mode=ro',uri=not write,timeout=30)
    try:
        if write:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS units(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS metadata(version TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS import_info(id TEXT PRIMARY KEY,received_at TEXT NOT NULL)')
            row=db.execute('SELECT version FROM metadata').fetchone()
            if row and row[0]!=VERSION:raise ConfigError('unsupported portable space version')
            if not row:db.execute('INSERT INTO metadata VALUES (?)',(VERSION,))
            db.commit();db.execute('BEGIN IMMEDIATE')
        elif db.execute('SELECT version FROM metadata').fetchone()[0]!=VERSION:
            raise ConfigError('unsupported portable space version')
        yield db
        if write:db.commit()
    except BaseException:
        db.rollback();raise
    finally:db.close()


def imported(root,kind=None):
    with database(root) as db:
        rows=db.execute('SELECT payload FROM units ORDER BY id').fetchall() if db else []
    units=[validate_unit(document(row[0])) for row in rows]
    return [unit for unit in units if kind is None or unit['kind']==kind]


def identity(kind,origin):
    return kind+':'+digest(origin)


def validate_unit(unit):
    required={'unit_version','id','kind','origin','recipe_reference','observed_at','payload','schema','attachments','context'}
    if not isinstance(unit,dict) or set(unit)!=required or unit['unit_version']!=VERSION or unit['kind'] not in KINDS:
        raise ConfigError('invalid portable data unit')
    origin=unit['origin']
    if not isinstance(origin,dict) or set(origin)!={'instance_id','profile','namespace','host_id','id'}:
        raise ConfigError('invalid portable origin')
    if any(not isinstance(v,str) or not v or len(v)>16384 for v in origin.values()):
        raise ConfigError('invalid portable identity')
    UUID(origin['instance_id'])
    if unit['id']!=identity(unit['kind'],origin):
        raise ConfigError('portable identity does not match origin')
    from observation_store import timestamp
    if timestamp(unit['observed_at'])!=unit['observed_at'] or not isinstance(unit['recipe_reference'],str) or not unit['recipe_reference']:
        raise ConfigError('invalid portable source time/reference')
    if not isinstance(unit['payload'],dict) or not isinstance(unit['schema'],(dict,bool)) or not isinstance(unit['context'],dict):
        raise ConfigError('invalid portable data/schema/context')
    if 'execution_identity' in unit['payload']:
        from opsfeast.recipe_execution import validate_evidence
        validate_evidence(unit['payload']['execution_identity'])
    if 'assessment' in unit['payload']:
        from opsfeast.recipe_assessment import validate as validate_assessment
        validate_assessment(unit['payload']['assessment'])
    validate_data(unit['payload']['data'] if unit['kind']=='retention' else unit['payload'],unit['schema'])
    if unit['kind']=='observation':
        raw=unit['payload']
        from retention_replay import producer_identity,source_identity
        if (raw.get('host_id')!=origin['host_id'] or raw.get('status') not in ('success','partial','failed','skipped','unsupported')
            or timestamp(raw.get('completed_at',raw.get('finished_at')))!=unit['observed_at']
            or raw.get('recipe',{}).get('reference',raw.get('recipe',{}).get('id'))!=unit['recipe_reference']
            or source_identity(raw,unit['context'].get('result_id'))!=origin['id']
            or producer_identity(raw)!=origin['instance_id']):
            raise ConfigError('raw observation differs from portable identity')
    if unit['kind']=='retention':
        record=unit['payload']
        if (record.get('kind')!='observation' or record.get('origin',{}).get('instance_id')!=origin['instance_id']
            or record.get('origin',{}).get('namespace')!=origin['namespace'] or record.get('origin',{}).get('host_id')!=origin['host_id']
            or record.get('origin',{}).get('record_id')!=origin['id'] or record.get('observed_at')!=unit['observed_at']
            or record.get('recipe_reference')!=unit['recipe_reference']):
            raise ConfigError('retained envelope differs from portable identity')
    if not isinstance(unit['attachments'],list):raise ConfigError('invalid attachment list')
    names=set()
    for attachment in unit['attachments']:
        if not isinstance(attachment,dict) or set(attachment)!={'path','sha256','size_bytes','hex'}:
            raise ConfigError('invalid attachment')
        relative(attachment['path'])
        if attachment['path'] in names:raise ConfigError('duplicate attachment')
        names.add(attachment['path'])
        content=bytes.fromhex(attachment['hex'])
        if digest(content)!=attachment['sha256'] or len(content)!=attachment['size_bytes']:
            raise ConfigError('attachment integrity mismatch')
    canonical(unit)
    return unit


def write_package(destination, units):
    destination=Path(destination).expanduser()
    if destination.exists() or destination.is_symlink():raise ConfigError('package destination already exists')
    payloads={}
    for unit in units:
        validate_unit(unit)
        name='units/'+digest(unit['id'])+'.json'
        if name in payloads:raise ConfigError('duplicate package unit identity')
        payloads[name]=canonical(unit).encode()
    if len(payloads)>MAX_FILES or sum(map(len,payloads.values()))>MAX_BYTES:
        raise ConfigError('data package exceeds file/size limit')
    manifest={'format':'opsfeast-data-package','version':VERSION,'package_id':str(uuid4()),
              'created_at':datetime.now(timezone.utc).isoformat(timespec='microseconds'),
              'files':{name:{'sha256':digest(data),'size_bytes':len(data)} for name,data in payloads.items()}}
    # Complete archive in its destination filesystem before publishing the final name.
    fd,temporary=tempfile.mkstemp(prefix='.package-',dir=destination.parent)
    try:
        with os.fdopen(fd,'w+b') as stream:
            with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('MANIFEST.json',canonical(manifest))
                for name,data in payloads.items():archive.writestr(name,data)
            stream.flush();os.fsync(stream.fileno())
        read_package(temporary)
        # link is exclusive; never replace a concurrently created destination.
        os.link(temporary,destination)
        fd=os.open(destination.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    return {'path':str(destination.resolve()),'sha256':digest(destination.read_bytes()),'units':len(units),'package_id':manifest['package_id']}


def read_package(path):
    path=Path(path)
    if path.stat().st_size>MAX_BYTES+16*1024*1024:raise ConfigError('compressed data package too large')
    content=path.read_bytes()
    return _read_package_bytes(content)


def _read_package_bytes(content):
    if len(content)>MAX_BYTES+16*1024*1024:raise ConfigError('compressed data package too large')
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries=archive.infolist();names=[e.filename for e in entries]
            if len(names)!=len(set(names)) or len(entries)>MAX_FILES+1 or sum(e.file_size for e in entries)>MAX_BYTES+1024*1024:
                raise ConfigError('invalid or oversized data package inventory')
            for entry in entries:
                relative(entry.filename)
                mode=entry.external_attr>>16
                if entry.is_dir() or entry.flag_bits&1 or stat.S_IFMT(mode) not in (0,stat.S_IFREG):
                    raise ConfigError('data package requires ordinary unencrypted files')
            if 'MANIFEST.json' not in names:raise ConfigError('missing package manifest')
            manifest=document(archive.read('MANIFEST.json'))
            if (not isinstance(manifest,dict) or set(manifest)!={'format','version','package_id','created_at','files'}
                or manifest['format']!='opsfeast-data-package' or manifest['version']!=VERSION or not isinstance(manifest['files'],dict)
                or set(names)!={'MANIFEST.json',*manifest['files']}):
                raise ConfigError('invalid data package manifest')
            UUID(manifest['package_id'])
            from observation_store import timestamp
            if timestamp(manifest['created_at'])!=manifest['created_at']:raise ConfigError('noncanonical package timestamp')
            units=[];identities=set()
            for name,info in manifest['files'].items():
                relative(name)
                data=archive.read(name)
                if info!={'sha256':digest(data),'size_bytes':len(data)}:raise ConfigError('data package integrity mismatch')
                unit=validate_unit(document(data))
                if unit['id'] in identities:raise ConfigError('duplicate data identity')
                identities.add(unit['id']);units.append(unit)
            return manifest,units
    except (zipfile.BadZipFile,KeyError,TypeError,ValueError,AttributeError,OverflowError,RecursionError) as exc:
        raise ConfigError('invalid data package: '+type(exc).__name__) from None


def bundle_schema(path):
    """Embed local external schema references into one offline schema document."""
    path=Path(path)
    if path.is_symlink():raise ConfigError('schema symlink refused')
    path=path.resolve(strict=True);base=path.parent;schemas={}
    def load(current):
        if current.is_symlink() or any(p.is_symlink() for p in current.parents if p.is_relative_to(base)):raise ConfigError('schema symlink refused')
        current=current.resolve(strict=True)
        if not current.is_relative_to(base) or current.is_symlink():raise ConfigError('schema reference escapes contract directory')
        key='s'+digest(str(current.relative_to(base)))
        if key in schemas:return key
        value=document(current.read_bytes());schemas[key]=value
        def visit(node):
            if isinstance(node,dict):
                ref=node.get('$ref')
                if ref and not ref.startswith('#'):
                    file,_,fragment=ref.partition('#')
                    if '://' in file:raise ConfigError('remote schemas are not portable')
                    child=load(current.parent/file)
                    node['$ref']='#/$defs/'+child+('/'+fragment.lstrip('/') if fragment else '')
                elif ref and ref.startswith('#/'):
                    node['$ref']='#/$defs/'+key+ref[1:]
                for item in node.values():visit(item)
            elif isinstance(node,list):
                for item in node:visit(item)
        visit(value)
        return key
    first=load(path)
    return {'$ref':'#/$defs/'+first,'$defs':schemas}


def infer_schema(value):
    """Fallback envelope shape for raw evidence, with original values preserved."""
    if isinstance(value,dict):return {'type':'object','required':list(value),'properties':{k:infer_schema(v) for k,v in value.items()},'additionalProperties':False}
    if isinstance(value,list):return {'type':'array'}
    return {'type':'null' if value is None else 'boolean' if type(value)is bool else 'integer' if type(value)is int else 'number' if type(value)is float else 'string'}


def native_units(root):
    """Read current evidence with source locators kept out of portable packages."""
    from retention_store import records, archives, settings, observation_source, observation_mode
    from recipe_reports import results, show_result, result_path
    root=Path(root).resolve(strict=True)
    namespace=(settings(root) or {}).get('namespace',root.name)
    retained=records(root)
    protected={r['data'].get('source_observation_id') for r in retained if r['kind']=='operation'}
    result=[]
    from observation_runs import list_runs
    runs={r['run_id']:r for r in list_runs(root)}
    for item in results(root,kind='operation')['results']:
        raw=show_result(root,item['result_id'],kind='operation')
        if not item['completed_at']:continue
        from retention_replay import producer_identity
        producer=producer_identity(raw)
        # Original location is stable within the producer; transfer retains it unchanged.
        from retention_replay import source_identity
        origin={'instance_id':producer,'profile':raw.get('profile',root.name),'namespace':namespace,'host_id':item['host_id'],'id':source_identity(raw,item['result_id'])}
        unit={'unit_version':VERSION,'id':identity('observation',origin),'kind':'observation','origin':origin,
              'recipe_reference':item['recipe_reference'] or item['recipe_id'],'observed_at':__import__('observation_store').timestamp(item['completed_at']),
              'payload':raw,'schema':infer_schema(raw),'attachments':[],'context':{'result_id':item['result_id']}}
        run=runs.get(raw.get('observation_run_id'))
        if run:
            unit['context']['batch']=run
        path=result_path(root,item['result_id']);source_bytes=path.read_bytes();attachments=[]
        if document(source_bytes)!=raw:raise ConfigError('raw source changed while reading')
        for entry in raw.get('artifacts',[]):
            name=relative(entry['path']);attachment=checked(root,path.parent.relative_to(root).as_posix()+'/'+name)
            data=attachment.read_bytes()
            if entry.get('sha256')!=digest(data) or entry.get('size_bytes')!=len(data):raise ConfigError('observation attachment changed')
            unit['attachments'].append({'path':name,'sha256':digest(data),'size_bytes':len(data),'hex':data.hex()})
            attachments.append({'path':str(attachment.relative_to(root)),'sha256':digest(data)})
        mode=raw.get('execution_access_mode',raw.get('recipe',{}).get('access_mode','unknown'))
        source=raw.get('source_observation_id')
        from retention_replay import execution_mode, source_identity
        mode=execution_mode(raw)
        try:source=source_identity(raw)
        except ConfigError:pass
        blocked='protected_operation_evidence' if mode!='read' or source in protected else None
        if blocked:unit['context']['archive_protection']=blocked
        result.append((validate_unit(unit),{'storage':'raw','path':str(path.relative_to(root)),'sha256':digest(source_bytes),'storage_bytes':path.stat().st_size+sum(a['size_bytes'] for a in unit['attachments']),'attachments':attachments,'blocked':blocked}))
    for record in retained:
        if record['kind']!='observation':continue
        declaration=record.get('retention_definition')
        if declaration and declaration.get('mode')=='portable':schema=declaration['data_schema']
        elif declaration and declaration['contract']!='host-values':
            from retention_contracts import location
            _,schema_path=location((declaration['contract'],declaration['version']))
            schema=bundle_schema(schema_path)
        else:schema=infer_schema(record['data'])
        origin={'instance_id':record['origin']['instance_id'],'profile':root.name,'namespace':record['origin']['namespace'],
                'host_id':record['origin']['host_id'],'id':record['origin']['record_id']}
        unit={'unit_version':VERSION,'id':identity('retention',origin),'kind':'retention','origin':origin,
              'recipe_reference':record['recipe_reference'],'observed_at':record['observed_at'],'payload':record,
              'schema':schema,'attachments':[],'context':{}}
        from retention_store import archive_path, database as native_db
        with native_db(archive_path(root,record)) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            events=[document(payload) for (payload,) in db.execute('SELECT payload FROM retention_events')] if 'retention_events' in tables else []
            selected_events=[e for e in events if e['record_id']==record['record_id']]
            event_ids={e['event_id'] for e in selected_events}
            unit['context']['consumer_events']=selected_events
            unit['context']['consumer_deliveries']=[document(payload) for eid,payload in db.execute('SELECT event_id,payload FROM consumer_deliveries') if eid in event_ids] if 'consumer_deliveries' in tables else []
        blocked='protected_operation_evidence' if observation_mode(record)!='read' or observation_source(record) in protected else None
        if blocked:unit['context']['archive_protection']=blocked
        result.append((validate_unit(unit),{'storage':'retention','path':str(archive_path(root,record).relative_to(root)),
            'record_id':record['record_id'],'sha256':digest(record),'blocked':blocked}))
    return result


def catalog(root,kind=None):
    if kind is not None and kind not in KINDS:raise ConfigError('unknown transfer unit kind')
    result={u['id']:(u,locator) for u,locator in native_units(root) if kind is None or u['kind']==kind}
    for unit in imported(root,kind):
        if unit['id'] in result:
            if digest(result[unit['id']][0])!=digest(unit):raise ConfigError('native/imported identity conflict')
            continue
        from retention_replay import execution_mode
        mode=execution_mode(unit['payload']) if unit['kind']=='observation' else unit['payload'].get('retention_provenance',{}).get('execution_access_mode','unknown')
        result[unit['id']]=(unit,{'storage':'imported','id':unit['id'],'sha256':digest(unit),'blocked':unit['context'].get('archive_protection') or ('protected_operation_evidence' if mode!='read' else None)})
    return result


def select(root, *, kinds=KINDS, recipe=None, hosts=None, ids=None, older_than=None, before=None, now=None):
    if not kinds or any(kind not in KINDS for kind in kinds):raise ConfigError('select observation and/or retention')
    if older_than is not None and (type(older_than)is not int or older_than<0 or older_than>365000):raise ConfigError('invalid retention days')
    if older_than is not None and before is not None:raise ConfigError('choose days or cutoff')
    instant=now or datetime.now(timezone.utc)
    if instant.tzinfo is None:raise ConfigError('selection time requires timezone')
    instant=instant.astimezone(timezone.utc)
    if isinstance(hosts,str) or isinstance(ids,str):raise ConfigError('host/ID filters require sequences')
    from observation_store import timestamp
    cutoff=timestamp(before) if before else (instant-timedelta(days=older_than)).isoformat(timespec='microseconds') if older_than is not None else None
    selected=[]
    for unit,locator in catalog(root).values():
        if ids and unit['id'] not in ids:continue
        if unit['kind'] not in kinds or recipe and unit['recipe_reference']!=recipe or hosts and unit['origin']['host_id'] not in hosts:continue
        if cutoff and unit['observed_at']>=cutoff:continue
        selected.append({'id':unit['id'],'kind':unit['kind'],'origin':unit['origin'],'recipe_reference':unit['recipe_reference'],
                         'observed_at':unit['observed_at'],'sha256':digest(unit),'bytes':len(canonical(unit).encode()),'source':locator})
    return {'version':VERSION,'cutoff':cutoff,'selected':selected,'bytes':sum(s['bytes'] for s in selected)}


def export(root,destination,**filters):
    plan=select(root,**filters);current=catalog(root)
    if any(s['id'] not in current or digest(current[s['id']][0])!=s['sha256'] for s in plan['selected']):raise ConfigError('export source changed; select again')
    receipt=write_package(destination,[current[s['id']][0] for s in plan['selected']])
    return {'status':'success','selection':plan,'package':receipt,'source_changed':False}


def import_plan(root,package,mode='merge'):
    if mode not in ('merge','replace'):raise ConfigError('import mode must be merge or replace')
    content=Path(package).read_bytes();_,units=_read_package_bytes(content);existing=catalog(root)
    actions=[]
    for unit in units:
        old=existing.get(unit['id']);equal=old and digest(old[0])==digest(unit)
        action='skip' if equal else 'add' if old is None else 'replace' if mode=='replace' else 'conflict'
        if action=='replace' and old[1]['blocked']:
            action='protected_native_conflict'
        actions.append({'id':unit['id'],'action':action,'before':digest(old[0]) if old else None,'after':digest(unit)})
    result={'version':VERSION,'operation':'import','mode':mode,'package_sha256':digest(content),'actions':actions}
    result['sha256']=digest(result)
    return result


def _write_native(root,source,unit):
    if source['storage']=='raw':
        atomic(checked(root,source['path']),unit['payload'])
    else:
        from retention_store import database as native_db
        record=unit['payload']
        with native_db(checked(root,source['path']),True) as db:
            db.execute('UPDATE records SET payload=?,observed_at=?,recipe_id=? WHERE record_id=?',
                (canonical(record),record['observed_at'],record['recipe_id'],record['record_id']))
            # Historical replacement must not inherit a previous live event's effect permission.
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='consumer_effects'").fetchone():
                event_ids=[eid for eid,payload in db.execute('SELECT event_id,payload FROM retention_events')
                           if document(payload).get('record_id')==source['record_id']]
                for eid in event_ids:db.execute('UPDATE consumer_effects SET permitted=0 WHERE event_id=?',(eid,))


def import_package(root,package,*,mode='merge',expected_plan=None):
    from retention_store import locked as retention_lock, validate_record
    from retention_replay import execution_mode
    with locked(root),retention_lock(root):
        plan=import_plan(root,package,mode)
        if expected_plan is None or expected_plan!=plan['sha256']:raise ConfigError('import requires the current reviewed plan digest')
        if any(a['action'] in ('conflict','protected_native_conflict') for a in plan['actions']):raise ConfigError('unresolved import conflict')
        content=Path(package).read_bytes()
        if digest(content)!=plan['package_sha256']:raise ConfigError('package changed during import')
        _,units=_read_package_bytes(content)
        by_id={u['id']:u for u in units}
        if {k:digest(v) for k,v in by_id.items()}!={a['id']:a['after'] for a in plan['actions']}:raise ConfigError('package unit content changed during import')
        before=catalog(root)
        targets=[]
        for action in plan['actions']:
            if action['action']=='skip':continue
            old=before.get(action['id']);incoming=by_id[action['id']]
            source=old[1] if old else {'storage':'imported','id':action['id']}
            if source['storage']=='raw':
                if execution_mode(incoming['payload'])!='read':raise ConfigError('replacement cannot change execution access mode')
                if incoming['attachments']!=old[0]['attachments']:raise ConfigError('native attachment changes require archive/import')
                if incoming['origin']!=old[0]['origin']:raise ConfigError('replacement cannot change origin')
            if source['storage']=='retention':
                record=validate_record(incoming['payload'])
                if (record['namespace'],record['host_id'],record['record_id'],record['observed_at'][:4])!=(old[0]['payload']['namespace'],old[0]['payload']['host_id'],old[0]['payload']['record_id'],old[0]['observed_at'][:4]):
                    raise ConfigError('native replacement cannot change storage identity')
            after_source=(digest(canonical(incoming['payload']).encode()) if source['storage']=='raw' else
                          digest(incoming['payload']) if source['storage']=='retention' else digest(incoming))
            targets.append({'id':action['id'],'source':source,'before_unit':digest(old[0]) if old else None,
                            'after_unit':digest(incoming),'after_source':after_source})
        receipt_id=str(uuid4());backup=checked(root,'transfer/imports/'+receipt_id+'.before.zip')
        backup.parent.mkdir(parents=True,exist_ok=True)
        write_package(backup,[before[a['id']][0] for a in targets if a['id'] in before])
        journal={'id':receipt_id,'status':'prepared','plan':plan,'targets':targets,'backup':str(backup),
                 'backup_sha256':digest(backup.read_bytes())}
        journal_path=checked(root,'transfer/imports/'+receipt_id+'.json');atomic(journal_path,journal)
        try:
            for target in targets:
                if target['source']['storage']!='imported':_write_native(root,target['source'],by_id[target['id']])
            with database(root,True) as db:
                for target in targets:
                    if target['source']['storage']=='imported':
                        unit=by_id[target['id']]
                        db.execute('INSERT OR REPLACE INTO units VALUES (?,?,?)',(unit['id'],unit['kind'],canonical(unit)))
                        db.execute('INSERT OR REPLACE INTO import_info VALUES (?,?)',(unit['id'],datetime.now(timezone.utc).isoformat(timespec='microseconds')))
            journal['status']='completed';atomic(journal_path,journal)
        except Exception as exc:
            journal.update(status='recoverable',error_type=type(exc).__name__);atomic(journal_path,journal)
            raise ConfigError('import incomplete; inspect import recovery '+receipt_id) from None
    try:content=publish(root)
    except Exception as exc:content={'status':'failed','error_type':type(exc).__name__}
    return {'status':'success','plan':plan,'receipt_id':receipt_id,'content_update':content,
            'effects':'data-only projection; no consumer/provider execution'}


def import_recovery_plan(root,receipt_id):
    UUID(receipt_id)
    journal=document(checked(root,'transfer/imports/'+receipt_id+'.json').read_bytes())
    backup=checked(root,'transfer/imports/'+receipt_id+'.before.zip')
    if str(backup)!=journal['backup']:raise ConfigError('import recovery backup path mismatch')
    if digest(backup.read_bytes())!=journal['backup_sha256']:raise ConfigError('import recovery backup changed')
    states=[]
    for target in journal['targets']:
        current=_current(root,target['source'])
        before=target['source'].get('sha256')
        states.append({'id':target['id'],'current':current,'allowed':current in (before,target['after_source'])})
    result={'operation':'import-recovery','id':receipt_id,'receipt_status':journal['status'],'targets':states}
    result['sha256']=digest(result)
    return result


def recover_import(root,receipt_id,*,expected_plan=None):
    from retention_store import locked as retention_lock
    with locked(root),retention_lock(root):
        plan=import_recovery_plan(root,receipt_id)
        if expected_plan is None or expected_plan!=plan['sha256'] or any(not s['allowed'] for s in plan['targets']):
            raise ConfigError('import recovery requires current reviewed plan and unchanged affected data')
        path=checked(root,'transfer/imports/'+receipt_id+'.json');journal=document(path.read_bytes())
        before={u['id']:u for u in read_package(journal['backup'])[1]}
        for target in journal['targets']:
            if target['source']['storage']!='imported':_write_native(root,target['source'],before[target['id']])
        with database(root,True) as db:
            for target in journal['targets']:
                if target['source']['storage']=='imported':
                    old=before.get(target['id'])
                    if old:db.execute('INSERT OR REPLACE INTO units VALUES (?,?,?)',(old['id'],old['kind'],canonical(old)))
                    else:
                        db.execute('DELETE FROM units WHERE id=?',(target['id'],))
                        db.execute('DELETE FROM import_info WHERE id=?',(target['id'],))
        journal['status']='rolled_back';atomic(path,journal)
        return {'status':'success','receipt_id':receipt_id}


def query(root,*,kind=None,recipe=None,hosts=None):
    return [copy.deepcopy(unit) for unit,_ in catalog(root,kind).values()
            if (recipe is None or unit['recipe_reference']==recipe) and (not hosts or unit['origin']['host_id'] in hosts)]


def archive_plan(root,destination,**filters):
    root=Path(root).resolve(strict=True);destination=Path(destination).expanduser().resolve()
    if destination.is_relative_to(root):raise ConfigError('archive destination must be outside the active profile')
    plan=select(root,**filters)
    selected_ids={s['id'] for s in plan['selected']}
    shared={a['path'] for uid,(_,loc) in catalog(root).items() if uid not in selected_ids and loc['storage']=='raw' for a in loc['attachments']}
    for selected in plan['selected']:
        source=selected['source']
        if source['storage']=='raw' and any(a['path'] in shared for a in source['attachments']):source['blocked']='shared_attachment'
    plan.update(operation='archive',destination=str(destination),profile=str(root))
    plan['sha256']=digest(plan)
    atomic(checked(root,'transfer/plans/'+plan['sha256']+'.json'),plan)
    return plan


def _current(root,source):
    if source['storage']=='raw':
        path=checked(root,source['path']);return digest(path.read_bytes()) if path.exists() else None
    if source['storage']=='imported':
        found=next((u for u in imported(root) if u['id']==source['id']),None)
        return digest(found) if found else None
    from retention_store import database as native_db
    path=checked(root,source['path'])
    if not path.exists():return None
    with native_db(path) as db:row=db.execute('SELECT payload FROM records WHERE record_id=?',(source['record_id'],)).fetchone()
    return digest(document(row[0])) if row else None


def _remove(root,source):
    if source['storage']=='raw':
        for attachment in source['attachments']:
            path=checked(root,attachment['path'])
            if path.exists():
                if digest(path.read_bytes())!=attachment['sha256']:raise ConfigError('archive attachment changed')
                path.unlink()
        checked(root,source['path']).unlink(missing_ok=True)
    elif source['storage']=='imported':
        with database(root,True) as db:
            db.execute('DELETE FROM units WHERE id=?',(source['id'],))
            db.execute('DELETE FROM import_info WHERE id=?',(source['id'],))
    else:
        from retention_store import database as native_db
        with native_db(checked(root,source['path']),True) as db:
            db.execute('DELETE FROM records WHERE record_id=?',(source['record_id'],))
            has=db.execute("SELECT 1 FROM sqlite_master WHERE name='retention_events'").fetchone()
            if has:
                ids=[eid for eid,payload in db.execute('SELECT event_id,payload FROM retention_events') if document(payload).get('record_id')==source['record_id']]
                for eid in ids:
                    db.execute('DELETE FROM consumer_deliveries WHERE event_id=?',(eid,))
                    db.execute('DELETE FROM consumer_effects WHERE event_id=?',(eid,))
                    db.execute('DELETE FROM retention_events WHERE event_id=?',(eid,))


def archive(root,destination=None,*,expected_plan=None,resume=None,**filters):
    from retention_store import locked as retention_lock
    root=Path(root).resolve(strict=True)
    with locked(root),retention_lock(root):
        if resume:
            UUID(resume);receipt_path=checked(root,'transfer/archives/'+resume+'.json')
            journal=document(receipt_path.read_bytes());plan=journal['plan']
            if plan['profile']!=str(root):raise ConfigError('archive belongs to another profile')
            destination=Path(plan['destination'])
            if digest(destination.read_bytes())!=journal['package']['sha256']:raise ConfigError('archive package changed or missing; source cleanup refused')
            _,units=read_package(destination)
        else:
            if expected_plan is None or len(expected_plan)!=64 or any(c not in '0123456789abcdef' for c in expected_plan):raise ConfigError('archive requires a reviewed plan digest')
            plan=document(checked(root,'transfer/plans/'+expected_plan+'.json').read_bytes())
            if digest({k:v for k,v in plan.items() if k!='sha256'})!=expected_plan or plan['sha256']!=expected_plan or plan['profile']!=str(root) or str(Path(destination).expanduser().resolve())!=plan['destination']:
                raise ConfigError('archive plan/profile/destination mismatch')
            # The reviewed plan is the complete scope; do not expand it with a later clock.
            current=catalog(root)
            for selected in plan['selected']:
                entry=current.get(selected['id'])
                if entry is None or digest(entry[0])!=selected['sha256'] or entry[1]!=selected['source']:
                    raise ConfigError('archive source or protection changed; create a new plan')
            if any(s['source']['blocked'] for s in plan['selected']):raise ConfigError('archive selection includes protected operation evidence')
            current=catalog(root)
            units=[current[s['id']][0] for s in plan['selected']]
            receipt=write_package(destination,units)
            journal={'id':str(uuid4()),'status':'verified','plan':plan,'package':receipt,'removed':[],
                     'completed_at':None,'bytes_reclaimed':0,'compaction':'pending','content':'pending'}
            receipt_path=checked(root,'transfer/archives/'+journal['id']+'.json');atomic(receipt_path,journal)
        if {u['id']:digest(u) for u in units}!={s['id']:s['sha256'] for s in plan['selected']}:
            raise ConfigError('archive package does not match source plan')
        if journal['status']=='completed':return journal
        try:
            # Validate every remaining source before deleting the first one.
            for selected in plan['selected']:
                current=_current(root,selected['source'])
                if current is not None and current!=selected['source']['sha256']:raise ConfigError('archive source changed; no further deletion')
            for selected in plan['selected']:
                if selected['id'] in journal['removed']:continue
                source=selected['source']
                if _current(root,source) is not None:_remove(root,source)
                journal['removed'].append(selected['id']);journal['status']='removing';atomic(receipt_path,journal)
            # Rebuild retention projections without dispatching executable consumers/providers.
            from retention_store import rebuild_unlocked
            rebuild_unlocked(root)
            paths={checked(root,s['source']['path']) for s in plan['selected'] if s['source']['storage']=='retention'}
            for base in ('retention','transfer'):
                directory=checked(root,base)
                if directory.exists():paths.update(p for p in directory.rglob('*.sqlite3') if not p.is_symlink())
            reclaimed=0
            for path in paths:
                before=path.stat().st_size
                db=sqlite3.connect(path)
                try:db.execute('VACUUM')
                finally:db.close()
                reclaimed+=max(0,before-path.stat().st_size)
            journal['bytes_reclaimed']=reclaimed+sum(s['source']['storage_bytes'] for s in plan['selected'] if s['source']['storage']=='raw')
            journal['compaction']='completed'
            # Only the bundled, pure retention projection; never arbitrary consumers or SMTP.
            from host_vault import rebuild as rebuild_vault
            rebuild_vault(root)
            publish(root)
            _publish_service_evidence(root)
            journal['content']='completed';journal['status']='completed'
            journal['completed_at']=datetime.now(timezone.utc).isoformat(timespec='microseconds')
            atomic(receipt_path,journal)
        except Exception as exc:
            journal.update(status='recoverable',error_type=type(exc).__name__)
            atomic(receipt_path,journal)
            raise ConfigError('archive cleanup incomplete; resume '+journal['id']+' ('+type(exc).__name__+')') from None
        return journal


def receipts(root):
    directory=checked(root,'transfer/archives')
    return [document(p.read_bytes()) for p in sorted(directory.glob('*.json'))] if directory.exists() else []


class Space:
    """Profile-bound portable data/recipe operations; never connects or executes."""
    def __init__(self,root):self.root=Path(root).resolve(strict=True)
    def query(self,**filters):return query(self.root,**filters)
    def select(self,**filters):return select(self.root,**filters)
    def export(self,destination,**filters):return export(self.root,destination,**filters)
    def import_plan(self,package,mode='merge'):return import_plan(self.root,package,mode)
    def import_package(self,package,**options):return import_package(self.root,package,**options)
    def archive_plan(self,destination,**filters):return archive_plan(self.root,destination,**filters)
    def archive(self,destination=None,**options):return archive(self.root,destination,**options)
    def receipts(self):return receipts(self.root)


def retained_views(root):
    """Origin-qualified read-only projections; never remap the stored portable payload."""
    from retention_store import settings
    namespace=(settings(root) or {}).get('namespace')
    result=[]
    with database(root) as db:
        received={i:t for i,t in db.execute('SELECT id,received_at FROM import_info')} if db else {}
    for unit in imported(root,'retention'):
        validate_unit(unit)
        record=copy.deepcopy(unit['payload'])
        record['record_id']=unit['id']
        record['host_id']='import-'+digest({k:unit['origin'][k] for k in ('instance_id','profile','namespace')})[:16]+'-'+unit['origin']['host_id']
        record['mappings'].append({'from':{key:unit['payload'][key] for key in ('namespace','host_id')},
            'to':{'namespace':namespace,'host_id':record['host_id']},'mapped_at':received[unit['id']],
            'basis':'portable-import:'+unit['id']})
        record['namespace']=namespace
        record['transfer_identity']=unit['id']
        result.append(record)
    return result


def publish(root):
    """Basic data-only view. Never imports candidate code or invokes service delivery."""
    from host_vault import publish as publish_vault,locked as vault_lock
    from vault_content import text,markdown_table
    units=imported(root)
    entries={}
    rows=[]
    for unit in sorted(units,key=lambda u:(u['kind'],u['observed_at'],u['id'])):
        name=digest(unit['id'])+'.md'
        rows.append((unit['kind'],text(unit['origin']['host_id']),text(unit['recipe_reference']),unit['observed_at'],
                     '['+text(unit['origin']['id'])+']('+name+')'))
        entries['Transfers/'+name]='\n'.join(['# Portable '+unit['kind'],'',
            'Origin: '+text(canonical(unit['origin'])),'','Unit: '+unit['id'],'',
            'Recipe: '+text(unit['recipe_reference']),'','Observed: '+unit['observed_at'],'','Preview limited to 12000 characters; transfer show returns the complete unit.','',
            '```json',json.dumps(unit['payload'],indent=2,ensure_ascii=False)[:12000].replace('```','\\u0060\\u0060\\u0060'),'```',''])
    entries['Transfers/SUMMARY.md']='\n'.join(['# Portable observation and retention data','',
        'Read-only projections. Imported records preserve their original source; no recipe is required.','',
        *markdown_table(['Kind','Origin host','Recipe','Observed','Original ID'],rows),''])
    with vault_lock(root):publish_vault(root,'portable-data',entries)
    return {'status':'success','units':len(units)}


def archived_reference(root,record_id):
    for receipt in reversed(receipts(root)):
        for selected in receipt['plan']['selected']:
            if selected['origin']['id']==record_id:
                return {'status':receipt['status'],'package':receipt['package']['path'],'receipt_id':receipt['id']}
    return None



def _publish_service_evidence(root):
    from opsfeast.services import Services, configuration
    from opsfeast.service_adapters import vault
    from host_vault import locked as vault_lock, publish as publish_vault
    for name,adapter in configuration(root)['presentations'].items():
        if adapter['enabled'] and adapter['source']=='builtin:vault':
            entries=vault(Services(root).snapshot(),{},Path(root))
            with vault_lock(root):publish_vault(root,'service-'+name,entries)
