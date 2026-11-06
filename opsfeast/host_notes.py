"""Profile-local host notes 0.1.0. No connections, history or model calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import UUID, uuid4

from . import ConfigError
from .core import Instance
from .identity import _locked
from .site import _atomic

VERSION = '0.1.0'
FILENAME = '.host-notes.json'
SOURCES = {'console', 'user', 'agent'}
MAX_BYTES = 16 * 1024 * 1024


class HostNotesError(ConfigError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _fail(code):
    raise HostNotesError(code)


def _text(value, limit, *, multiline=False):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        _fail('invalid_note_input')
    if any(ord(c) < 32 and not (multiline and c in '\n\r\t') for c in value):
        _fail('invalid_note_input')
    try:
        value.encode('utf-8')
    except UnicodeError:
        _fail('invalid_note_input')
    return value


def _uuid(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, AttributeError):
        _fail('invalid_note_uuid')
    return value


def _content(changes):
    if not isinstance(changes, dict) or not {'title', 'content', 'source'} <= set(changes) or set(changes)-{'title','content','source','recipe_references','tags'}:
        _fail('invalid_note_input')
    _text(changes['title'], 200)
    _text(changes['content'], 32000, multiline=True)
    if not isinstance(changes['source'], str) or changes['source'] not in SOURCES:
        _fail('invalid_note_source')
    result = dict(changes)
    for key in ('recipe_references','tags'):
        if key in changes: result[key] = _labels(changes[key], key)
    return result


def _labels(values, kind):
    if not isinstance(values, list) or len(values)>32: _fail('invalid_note_input')
    result=[]
    for value in values:
        _text(value, 500 if kind=='recipe_references' else 64)
        if value != value.strip(): _fail('invalid_note_input')
        if kind=='recipe_references':
            from recipe_settings import reference
            try: value=reference(value)
            except ConfigError: _fail('invalid_note_input')
        else:
            if ',' in value: _fail('invalid_note_input')
            value=value.lower()
        if value not in result: result.append(value)
    return sorted(result)


def _selected(installation, profile):
    _text(profile, 80)
    return Instance.open(installation).profile(profile)


def _path(selected):
    path = selected.root / FILENAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        _fail('note_storage_invalid')
    return path


def _read(selected):
    path = _path(selected)
    if not path.exists():
        raw = b''
        data = {'schema_version': VERSION, 'revision': str(uuid4()), 'notes': []}
    else:
        if path.stat().st_size > MAX_BYTES:
            _fail('note_storage_invalid')
        raw = path.read_bytes()
        try:
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        raise ValueError()
                    result[key] = value
                return result
            data = json.loads(raw, object_pairs_hook=pairs)
            if not isinstance(data, dict) or set(data) != {'schema_version', 'revision', 'notes'} or data['schema_version'] != VERSION or not isinstance(data['notes'], list):
                raise ValueError()
            _uuid(data['revision'])
            seen = set()
            for note in data['notes']:
                if not isinstance(note, dict) or not {'uuid','host_id','title','content','source','timestamp'} <= set(note) or set(note)-{'uuid','host_id','title','content','source','timestamp','recipe_references','tags'}:
                    raise ValueError()
                _uuid(note['uuid'])
                if note['uuid'] in seen:
                    raise ValueError()
                seen.add(note['uuid'])
                _text(note['host_id'], 200)
                metadata=_content({k:note[k] for k in ('title','content','source','recipe_references','tags') if k in note})
                note.update({key:metadata.get(key,[]) for key in ('recipe_references','tags')})
                stamp = datetime.fromisoformat(note['timestamp'])
                if stamp.utcoffset() is None or stamp.isoformat(timespec='seconds') != note['timestamp']:
                    raise ValueError()
        except (ValueError, TypeError, KeyError, HostNotesError):
            _fail('note_storage_invalid')
    # Opaque content revision includes a nonce so deleting/recreating identical notes
    # cannot accidentally accept a stale edit. No old revisions are retained.
    revision = hashlib.sha256(str(selected.root).encode() + b'\0' + raw).hexdigest()
    return data, revision


def inspect(installation, *, profile, host_id, query='', recipe_reference=None, tags=None, include_general=False):
    """Read selected host notes; missing storage stays absent, orphan notes readable."""
    selected = _selected(installation, profile)
    _text(host_id, 200)
    if not isinstance(query, str) or len(query) > 1000:
        _fail('invalid_note_input')
    if type(include_general) is not bool or (include_general and recipe_reference is None): _fail('invalid_note_input')
    if recipe_reference is not None: recipe_reference=_labels([recipe_reference],'recipe_references')[0]
    tags=_labels([] if tags is None else tags,'tags')
    data, revision = _read(selected)
    needle = query.casefold()
    notes = [n for n in data['notes'] if n['host_id'] == host_id and
             (not needle or needle in (n['title'] + '\n' + n['content']+'\n'+'\n'.join(n['recipe_references']+n['tags'])).casefold()) and
             (recipe_reference is None or recipe_reference in n['recipe_references'] or (include_general and not n['recipe_references'])) and
             set(tags)<=set(n['tags'])]
    return {'schema_version': VERSION, 'profile': profile, 'host_id': host_id,
            'host_present': host_id in selected.hosts._config.hosts, 'revision': revision,
            'notes': sorted(notes, key=lambda n: (n['timestamp'], n['uuid']), reverse=True)}


def mutate(installation, *, profile, host_id, action, expected_revision,
           note_uuid=None, changes=None, remove=None, confirmation=None):
    """Atomic latest-state mutation. Merge preserves the survivor UUID."""
    if not isinstance(action, str) or action not in {'create', 'update', 'delete', 'merge'}:
        _fail('invalid_note_action')
    _text(host_id, 200)
    _text(expected_revision, 64)
    if action != 'create':
        _uuid(note_uuid)
    if action != 'delete':
        changes = _content(changes)
    elif changes is not None:
        _fail('invalid_note_input')
    if action == 'merge':
        if not isinstance(remove, list) or not remove or len(remove) > 100 or any(not isinstance(x, str) for x in remove) or len(set(remove)) != len(remove):
            _fail('invalid_note_merge')
        for identifier in remove:
            _uuid(identifier)
        if note_uuid in remove:
            _fail('invalid_note_merge')
        if confirmation != remove:
            _fail('note_confirmation_required')
    elif remove is not None:
        _fail('invalid_note_input')
    if action == 'delete' and confirmation != note_uuid:
        _fail('note_confirmation_required')
    installation = Path(installation).resolve(strict=True)
    with _locked(installation / '.opsfeast-profiles.json'):
        selected = _selected(installation, profile)
        with _locked(selected.root / FILENAME):
            data, revision = _read(selected)
            if revision != expected_revision:
                _fail('note_revision_conflict')
            if action == 'create' and host_id not in selected.hosts._config.hosts:
                _fail('host_not_found')
            rows = {n['uuid']: n for n in data['notes'] if n['host_id'] == host_id}
            required = ([note_uuid] if action != 'create' else []) + (remove or [])
            if any(identifier not in rows for identifier in required):
                _fail('note_not_found')
            deleted = [note_uuid] if action == 'delete' else (remove or [])
            data['notes'] = [n for n in data['notes'] if n['uuid'] not in deleted]
            note = None
            if action != 'delete':
                identifier = str(uuid4()) if action == 'create' else note_uuid
                related = [] if action=='create' else [rows[x] for x in [note_uuid]+(remove or [])]
                changes=dict(changes)
                for key in ('recipe_references','tags'):
                    if key not in changes:
                        changes[key]=_labels(sorted({v for old in related for v in old[key]}),key)
                note = {'uuid': identifier, 'host_id': host_id, **changes,
                        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds')}
                data['notes'] = [n for n in data['notes'] if n['uuid'] != identifier] + [note]
            data['revision'] = str(uuid4())
            raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            if len(raw) > MAX_BYTES:
                _fail('note_storage_full')
            # Recheck even non-cooperating edits before atomic replacement.
            if _read(selected)[1] != revision:
                _fail('note_revision_conflict')
            _atomic(_path(selected), raw)
            return {'schema_version': VERSION, 'profile': profile, 'host_id': host_id,
                    'action': action, 'note': note, 'deleted': deleted,
                    'revision': hashlib.sha256(str(selected.root).encode() + b'\0' + raw).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read/write private host notes; no host connections. Writes replace current content, without history.')
    parser.add_argument('--installation', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--profile', required=True)
    parser.add_argument('--host', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    listing=sub.add_parser('list')
    listing.add_argument('--query', default='')
    listing.add_argument('--recipe', help='Exact source-qualified recipe reference; no execution or recipe resolution.')
    listing.add_argument('--tag', action='append', default=[], help='Require this tag; repeat for all-tag matching.')
    listing.add_argument('--include-general', action='store_true', help='With --recipe, also include notes without recipe associations.')
    for action in ('show', 'create', 'update', 'delete', 'merge'):
        command = sub.add_parser(action, description={
            'show': 'Read one note and its current revision; no writes or connections.',
            'create': 'Create a note. Read title/content/source JSON from stdin. No host connection.',
            'update': 'Replace title/content/source from stdin JSON; preserve UUID. No edit history.',
            'delete': 'Permanently delete the selected UUID after confirmation; no undo or remote effects.',
            'merge': 'Replace the survivor from title/content/source stdin JSON and atomically delete confirmed --remove UUIDs. No undo.',
        }[action])
        if action != 'create':
            command.add_argument('uuid')
        if action != 'show':
            command.add_argument('--expected-revision', required=True)
        if action in ('delete', 'merge'):
            command.add_argument('--confirm', action='append' if action == 'merge' else 'store', required=True)
        if action == 'merge':
            command.add_argument('--remove', action='append', required=True)
    args = parser.parse_args(argv)
    try:
        scope = dict(profile=args.profile, host_id=args.host)
        if args.action in ('list', 'show'):
            result = inspect(args.installation, **scope, query=getattr(args, 'query', ''), recipe_reference=getattr(args,'recipe',None), tags=getattr(args,'tag',None), include_general=getattr(args,'include_general',False))
            if args.action == 'show':
                _uuid(args.uuid)
                result['notes'] = [n for n in result['notes'] if n['uuid'] == args.uuid]
                if not result['notes']:
                    _fail('note_not_found')
        else:
            changes = None
            if args.action != 'delete':
                raw = sys.stdin.buffer.read(131073)
                if len(raw) > 131072:
                    _fail('invalid_note_input')
                changes = json.loads(raw)
            result = mutate(args.installation, **scope, action=args.action,
                expected_revision=args.expected_revision, note_uuid=getattr(args, 'uuid', None),
                changes=changes, remove=getattr(args, 'remove', None), confirmation=getattr(args, 'confirm', None))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ConfigError, OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({'error': getattr(exc, 'code', 'note_request_failed')}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
