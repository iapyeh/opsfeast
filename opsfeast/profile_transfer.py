"""Profile-local backup/import and recoverable deletion, contract 0.1.0.

No host operations. External references and installation identity are not copied.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import time
from uuid import uuid4
import zipfile

from . import ConfigError, load_profiles, registered_root, profile_name, save_profiles, Validator
from .identity import _locked
from .profile_settings import check_revision, inspect

VERSION = '0.1.0'
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
MAX_FILE = 128 * 1024 * 1024
MAX_FILES = 25000


def _root(installation, name):
    profile_name(name)
    return registered_root(load_profiles(installation), name, Path(installation))


def _files(root):
    found = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ConfigError('profile backup does not accept symlinks')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ConfigError('profile backup requires regular files')
        journal_base=next((path.with_name(path.name[:-len(suffix)]) for suffix in ('-wal','-shm','-journal') if path.name.endswith(suffix)),None)
        if journal_base is not None and journal_base.is_file():
            with journal_base.open('rb') as stream:
                if stream.read(16)==b'SQLite format 3\x00':continue
        if path.stat().st_size > MAX_FILE:
            raise ConfigError('profile backup file exceeds 128 MiB')
        found.append(path)
        if len(found) > MAX_FILES:
            raise ConfigError('profile backup exceeds file count limit')
    return found


def export(installation, *, name, expected_revision):
    """Bytes for a private ZIP; database backups use SQLite's transaction backup."""
    check_revision(installation, expected_revision)
    root = _root(installation, name)
    from .storage import resolve_data_root
    from . import profile_root
    data_root=resolve_data_root(installation,required=False)
    protected=[Path(installation).resolve()]+([data_root] if data_root is not None else [])
    protected += [profile_root(item['root'],Path(installation)) for other,item in load_profiles(installation)['profiles'].items() if other!=name]
    if any(p==root or p.is_relative_to(root) for p in protected):raise ConfigError('profile backup overlaps installation or another Profile')
    paths = _files(root)
    before = {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    manifest = {'kind':'opsfeast-profile-backup','version':VERSION,'profile':name,
                'description':load_profiles(installation)['profiles'][name].get('description',''),
                'created_at':datetime.now(timezone.utc).isoformat(),
                'consistency':'Stable ordinary-file set and per-database SQLite transaction snapshots; not a global transaction.',
                'external_references':'Not copied or rebound. Review original external paths before use.', 'files':[]}
    output = io.BytesIO();total = 0
    with tempfile.TemporaryDirectory(prefix='opsfeast-profile-backup-') as temporary:
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                relative = path.relative_to(root).as_posix()
                with path.open('rb') as stream:
                    sqlite = stream.read(16) == b'SQLite format 3\x00'
                if sqlite:
                    target = Path(temporary)/'database.sqlite'
                    target.unlink(missing_ok=True)
                    source = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=5)
                    destination = sqlite3.connect(target)
                    try:
                        deadline=time.monotonic()+30
                        page_bytes=source.execute('PRAGMA page_size').fetchone()[0]
                        def progress(status,remaining,total):
                            if total*page_bytes>MAX_FILE or time.monotonic()>deadline:raise ConfigError('SQLite backup byte/time limit')
                        source.backup(destination,pages=256,progress=progress)
                    finally:
                        source.close();destination.close()
                    with target.open('rb') as stream:raw=stream.read(MAX_FILE+1)
                else:
                    with path.open('rb') as stream:raw=stream.read(MAX_FILE+1)
                total += len(raw)
                if len(raw) > MAX_FILE or total > MAX_EXPANDED:
                    raise ConfigError('profile backup byte limit')
                archive.writestr('profile/'+relative, raw)
                manifest['files'].append({'path':relative,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'executable':bool(path.stat().st_mode & 0o111)})
                if output.tell() > MAX_ARCHIVE:
                    raise ConfigError('profile backup archive limit')
            archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
    after = {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns) for p in _files(root)}
    if before != after:
        raise ConfigError('profile changed during backup; stop writers and try again')
    check_revision(installation, expected_revision)
    if len(output.getvalue()) > MAX_ARCHIVE:
        raise ConfigError('profile backup archive limit')
    return output.getvalue()


def _member(name):
    if not isinstance(name,str) or not name or '\\' in name or name.startswith('/') or any(part in ('','.','..') for part in name.split('/')) or ':' in name or '\x00' in name:
        raise ConfigError('invalid profile archive path')
    return PurePosixPath(name)


def import_archive(installation, data_root, raw, *, name, expected_revision):
    """Import a complete verified file set into a fresh managed directory."""
    from .core import Instance
    name = profile_name(name)
    check_revision(installation, expected_revision)
    if name in load_profiles(installation)['profiles']:
        raise ConfigError('profile name already registered')
    if not isinstance(raw,bytes) or len(raw) > MAX_ARCHIVE:
        raise ConfigError('profile archive byte limit')
    parent = Path(data_root)/'profiles'
    if parent.is_symlink():raise ConfigError('profile parent must not be a symlink')
    parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    target = parent/name
    if target.exists() or target.is_symlink():raise ConfigError('profile destination already exists')
    stage = Path(tempfile.mkdtemp(prefix='.import-',dir=parent))
    moved = False
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries)>MAX_FILES+1 or len({item.filename for item in entries})!=len(entries):
                raise ConfigError('profile archive duplicate or excessive members')
            by_name = {}
            for item in entries:
                _member(item.filename)
                mode = item.external_attr >> 16
                if item.is_dir() or mode & 0o170000 not in (0,0o100000) or item.file_size>MAX_FILE or item.flag_bits & 1:
                    raise ConfigError('profile archive contains unsupported members')
                by_name[item.filename] = item
            if sum(item.file_size for item in entries)>MAX_EXPANDED or 'manifest.json' not in by_name or by_name['manifest.json'].file_size>8*1024*1024:
                raise ConfigError('profile archive bounds or manifest invalid')
            from recipe_inputs import parse_json_object
            manifest = parse_json_object(archive.read('manifest.json'))
            from . import REPOSITORY_ROOT
            from .data_contract import validate
            schema=json.loads((REPOSITORY_ROOT/'schemas/profile-backup.schema.json').read_text())
            validate(manifest,schema)
            if manifest.get('kind')!='opsfeast-profile-backup' or manifest.get('version')!=VERSION or not isinstance(manifest.get('files'),list):
                raise ConfigError('unsupported profile archive contract')
            expected = {'manifest.json'}
            for record in manifest['files']:
                relative = record['path'];_member(relative)
                member = 'profile/'+relative
                if member in expected or member not in by_name:
                    raise ConfigError('profile manifest file set mismatch')
                expected.add(member)
                content = archive.read(member)
                if len(content)!=record['size'] or hashlib.sha256(content).hexdigest()!=record['sha256']:
                    raise ConfigError('profile manifest digest mismatch')
                destination = stage/relative
                destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                with destination.open('xb') as stream:stream.write(content)
                if type(record.get('executable',False)) is not bool:raise ConfigError('invalid executable metadata')
                destination.chmod(0o700 if record.get('executable',False) else 0o600)
            if expected != set(by_name):raise ConfigError('profile manifest file set mismatch')
        Validator(stage).check()  # Static configuration validation; never connects.
        stage.rename(target);moved=True
        Instance.open(installation).profiles.attach(target,name=name,expected_revision=expected_revision,
                                                    description=manifest.get('description',''))
        return inspect(installation)
    except (zipfile.BadZipFile,KeyError,TypeError,ValueError) as error:
        raise ConfigError('invalid profile backup') from error
    finally:
        # Remove only the new candidate owned by this failed import, never existing data.
        registered = name in load_profiles(installation)['profiles']
        if stage.exists():shutil.rmtree(stage)
        if moved and not registered and target.exists():shutil.rmtree(target)


def delete(installation, data_root, *, name, expected_revision, confirm_name):
    """Remove registration and move its entire directory to private recovery storage."""
    if confirm_name!=name:raise ConfigError('profile confirmation does not match')
    from . import profile_root
    installation = Path(installation).resolve()
    with _locked(installation/'.opsfeast-profiles.json'):
        check_revision(installation,expected_revision)
        data = load_profiles(installation)
        if name=='main' or name==data['default_profile']:
            raise ConfigError('main/default profile cannot be deleted; switch default first')
        target = _root(installation,name)
        protected = [installation,Path(data_root).resolve()]
        protected += [profile_root(item['root'],installation) for other,item in data['profiles'].items() if other!=name]
        if any(target==p or p.is_relative_to(target) or target.is_relative_to(p) and p not in (installation,Path(data_root).resolve()) for p in protected):
            raise ConfigError('profile root overlaps protected data')
        trash = Path(data_root)/'profile-trash'
        if trash.is_symlink():raise ConfigError('profile recovery directory must not be a symlink')
        trash.mkdir(mode=0o700,parents=True,exist_ok=True)
        recovery = trash/(name+'-'+uuid4().hex)
        # rename is atomic on one filesystem; cross-filesystem roots must be detached instead.
        target.rename(recovery)
        try:
            del data['profiles'][name];save_profiles(data,installation)
        except Exception:
            recovery.rename(target);raise
    return {**inspect(installation),'deleted':{'name':name,'recovery_root':str(recovery),'permanently_removed':False}}
