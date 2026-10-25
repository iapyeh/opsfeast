"""Profile-scoped notification/todo objects, lifecycle and durable adapter outboxes.

Contract 0.1.0. Reads never initialize storage or contact a provider. Mutations
are serialized SQLite transactions. Adapters cannot replace lifecycle rules.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from opsfeast import ConfigError

VERSION = '0.1.0'
STATES = {'notification': {'active', 'resolved'},
          'todo': {'open', 'in_progress', 'blocked', 'done', 'cancelled'}}
SEVERITIES = ('info', 'warning', 'error', 'critical')
TODO_TRANSITIONS = {
    'open': {'in_progress', 'blocked', 'done', 'cancelled'},
    'in_progress': {'open', 'blocked', 'done', 'cancelled'},
    'blocked': {'open', 'in_progress', 'done', 'cancelled'},
    'done': {'open'}, 'cancelled': {'open'},
}


class ServiceError(ConfigError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def instant(value):
    if not isinstance(value, str):
        raise ServiceError('invalid_timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except ValueError:
        raise ServiceError('invalid_timestamp') from None


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    except (ValueError, TypeError):
        raise ServiceError('invalid_json_data') from None


def nonblank(value, code='invalid_text'):
    if not isinstance(value, str) or not value.strip() or len(value) > 16384 or '\x00' in value:
        raise ServiceError(code)
    return value


def configuration(root):
    from opsfeast import definition_path, read_yaml
    path = definition_path(Path(root))
    raw = read_yaml(path) if path.is_file() else {}
    return validate_configuration(raw.get('services', {}))


def validate_configuration(value):
    from opsfeast.service_adapters import validate_adapter
    if not isinstance(value, dict) or set(value) - {'presentations', 'deliveries', 'routes'}:
        raise ServiceError('invalid_services_configuration')
    result = copy.deepcopy(value)
    result.setdefault('presentations', {'vault': {'source': 'builtin:vault', 'enabled': True}})
    result.setdefault('deliveries', {})
    result.setdefault('routes', [])
    for kind in ('presentations', 'deliveries'):
        if not isinstance(result[kind], dict):
            raise ServiceError('invalid_adapter_catalog')
        for name, adapter in result[kind].items():
            validate_adapter(name, adapter, kind)
    if not isinstance(result['routes'], list):
        raise ServiceError('invalid_notification_routes')
    for route in result['routes']:
        if (not isinstance(route, dict) or set(route) != {'minimum_severity', 'channels'}
                or route['minimum_severity'] not in SEVERITIES or not isinstance(route['channels'], list)
                or not route['channels'] or any(not isinstance(c, str) or c not in result['deliveries'] for c in route['channels'])):
            raise ServiceError('invalid_notification_route')
    return result


class Objects:
    def __init__(self, services, kind):
        self.services, self.kind = services, kind

    def list(self, *, host=None, status=None):
        return [o for o in self.services._list(self.kind)
                if (host is None or o['source']['host_id'] == host) and (status is None or o['status'] == status)]

    def show(self, object_id):
        with self.services._db(False) as db:
            row = db.execute('SELECT payload FROM objects WHERE id=? AND kind=?', (object_id, self.kind)).fetchone() if db else None
        if not row:
            raise ServiceError('object_not_found')
        return json.loads(row[0])

    def create(self, *, source, owner, observed_at, evidence, title, body, severity='warning'):
        """Create/update this kind for one stable source condition, idempotently."""
        outcome = self.services.reconcile(source=source, owner=owner, observed_at=observed_at,
            evidence=evidence, title=title, body=body, severity=severity, active=True,
            notification=self.kind == 'notification', todo=self.kind == 'todo')
        return outcome

    def update(self, object_id, *, expected_revision, actor, **changes):
        """CAS update; system observation fields cannot be overwritten by an editor."""
        nonblank(actor)
        if type(expected_revision) is not int:
            raise ServiceError('invalid_revision')
        allowed = {'read', 'acknowledged', 'muted_until'} if self.kind == 'notification' else {
            'status', 'assignee', 'start_at', 'due_at', 'timezone', 'note', 'priority'}
        if not changes or set(changes) - allowed:
            raise ServiceError('unsupported_object_update')
        with self.services._db(True) as db:
            row = db.execute('SELECT payload FROM objects WHERE id=? AND kind=?', (object_id, self.kind)).fetchone()
            if not row:
                raise ServiceError('object_not_found')
            obj = json.loads(row[0])
            if obj['revision'] != expected_revision:
                raise ServiceError('revision_conflict')
            if self.kind == 'notification':
                if any(type(v) is not bool for k, v in changes.items() if k != 'muted_until'):
                    raise ServiceError('invalid_notification_update')
                if changes.get('muted_until') is not None:
                    changes['muted_until'] = instant(changes['muted_until'])
                for name in ('read', 'acknowledged'):
                    if name in changes:
                        changes[name + '_at'] = now() if changes[name] else None
                        changes[name + '_by'] = actor if changes[name] else None
            else:
                if 'status' in changes and (not isinstance(changes['status'], str) or changes['status'] not in STATES['todo']):
                    raise ServiceError('invalid_todo_state')
                if ('status' in changes and changes['status'] != obj['status']
                        and changes['status'] not in TODO_TRANSITIONS[obj['status']]):
                    raise ServiceError('invalid_todo_transition')
                if 'priority' in changes and changes['priority'] not in SEVERITIES:
                    raise ServiceError('invalid_priority')
                from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
                if 'timezone' in changes:
                    try:
                        ZoneInfo(changes['timezone'])
                    except (ValueError, TypeError, ZoneInfoNotFoundError):
                        raise ServiceError('invalid_timezone') from None
                for name in ('start_at', 'due_at'):
                    if name in changes and changes[name] is not None:
                        changes[name] = instant(changes[name])
                for name in ('assignee', 'note'):
                    if name in changes and changes[name] is not None:
                        nonblank(changes[name])
                if changes.get('status') == 'done':
                    changes['verified'] = not obj['condition_active']
                elif 'status' in changes:
                    changes['verified'] = False
            obj.update(copy.deepcopy(changes))
            if obj.get('start_at') and obj.get('due_at') and obj['start_at'] > obj['due_at']:
                raise ServiceError('due_before_start')
            self.services._save(db, obj, actor, 'edited')
            return obj


class Services:
    def __init__(self, root, *, guard=None, permitted_records=None):
        self.root = Path(root).resolve(strict=True)
        self.guard = guard
        self.permitted_records = permitted_records
        self.notifications = Objects(self, 'notification')
        self.todos = Objects(self, 'todo')

    @contextmanager
    def _db(self, write):
        if self.guard:
            self.guard()
        from retention_store import checked, settings
        path = checked(self.root, 'services', 'objects.sqlite3')
        if not write and not path.exists():
            yield None
            return
        if write:
            if settings(self.root) is None:
                raise ServiceError('services_require_namespace')
            path.parent.mkdir(mode=0o700, exist_ok=True)
            # Create without a permissive-umask interval; reject symlink races.
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        db = sqlite3.connect(str(path) if write else path.as_uri() + '?mode=ro', uri=not write, timeout=30)
        try:
            if write:
                db.execute('BEGIN IMMEDIATE')
                for sql in (
                    'CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS conditions(key TEXT PRIMARY KEY,payload TEXT NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS history(sequence INTEGER PRIMARY KEY,id TEXT NOT NULL,payload TEXT NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY,notification TEXT NOT NULL,channel TEXT NOT NULL,status TEXT NOT NULL,attempts INTEGER NOT NULL,payload TEXT NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS projections(adapter TEXT PRIMARY KEY,sequence INTEGER NOT NULL,payload TEXT NOT NULL)',
                    'CREATE TABLE IF NOT EXISTS metadata(version TEXT NOT NULL)',
                ):
                    db.execute(sql)
                version = db.execute('SELECT version FROM metadata').fetchone()
                if version and version[0] != VERSION:
                    raise ServiceError('unsupported_service_storage')
                if not version:
                    db.execute('INSERT INTO metadata VALUES (?)', (VERSION,))
                # A failed first object mutation must leave a valid empty store.
                db.commit()
                db.execute('BEGIN IMMEDIATE')
            elif db.execute('SELECT version FROM metadata').fetchone()[0] != VERSION:
                raise ServiceError('unsupported_service_storage')
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def _list(self, kind=None):
        with self._db(False) as db:
            rows = db.execute('SELECT payload FROM objects ORDER BY id').fetchall() if db else []
        return [json.loads(row[0]) for row in rows if kind is None or json.loads(row[0])['kind'] == kind]

    def _save(self, db, obj, actor, action):
        obj['revision'] += 1
        obj['updated_at'] = now()
        db.execute('INSERT OR REPLACE INTO objects VALUES (?,?,?)', (obj['id'], obj['kind'], canonical(obj)))
        event = {'at': obj['updated_at'], 'actor': actor, 'action': action, 'object': obj}
        db.execute('INSERT INTO history(id,payload) VALUES (?,?)', (obj['id'], canonical(event)))

    def history(self, object_id=None):
        with self._db(False) as db:
            rows = db.execute('SELECT id,payload FROM history ORDER BY sequence').fetchall() if db else []
        return [json.loads(p) for i, p in rows if object_id is None or i == object_id]

    def inspect(self):
        from opsfeast.service_adapters import inspect_adapters
        config = configuration(self.root)
        with self._db(False) as db:
            initialized = db is not None
            counts = {k: len([o for o in self._list() if o['kind'] == k]) for k in STATES}
            projections = {name: json.loads(payload) for name, payload in
                           (db.execute('SELECT adapter,payload FROM projections').fetchall() if db else [])}
        return {'contract_version': VERSION, 'status': 'success', 'initialized': initialized,
                'notifications': {'available': True, 'contract_version': VERSION},
                'todos': {'available': True, 'contract_version': VERSION},
                'objects': counts, 'adapters': inspect_adapters(self.root, config),
                'presentation_receipts': projections,
                'automatic_wakeup': False, 'lifecycle': 'platform', 'verification': 'static; no provider probes'}

    def reconcile(self, *, source, owner, observed_at, evidence, active,
                  title, body, severity='warning', notification=False, todo=False,
                  effects=True, recovery_notification=False):
        """Atomically reconcile a condition and its notification/todo effects.

        active=None records no new claim: failed/incomplete observations cannot
        resolve an issue. effects=False seeds historical state without alerts.
        """
        if (not isinstance(source, dict) or set(source) != {'host_id', 'recipe_reference', 'subject', 'rule'}):
            raise ServiceError('invalid_condition_source')
        for v in (*source.values(), owner, title):
            nonblank(v)
        if not isinstance(body, str) or len(body) > 1048576:
            raise ServiceError('invalid_body')
        if severity not in SEVERITIES or active is not None and type(active) is not bool:
            raise ServiceError('invalid_condition_state')
        if any(type(v) is not bool for v in (notification, todo, effects, recovery_notification)):
            raise ServiceError('invalid_effect_policy')
        observed_at = instant(observed_at)
        if not isinstance(evidence, dict) or not isinstance(evidence.get('record_id'), str):
            raise ServiceError('invalid_evidence')
        canonical(evidence)
        if self.permitted_records is not None and evidence['record_id'] not in self.permitted_records:
            return {'status': 'skipped', 'reason_code': 'historical_service_effects_disabled'}
        config = configuration(self.root)
        key = hashlib.sha256(canonical(source).encode()).hexdigest()
        with self._db(True) as db:
            row = db.execute('SELECT payload FROM conditions WHERE key=?', (key,)).fetchone()
            old = json.loads(row[0]) if row else None
            if old and old['owner'] != owner:
                raise ServiceError('condition_owner_conflict')
            supplement = old and observed_at == old['observed_at'] and active == old['active'] and evidence == old['evidence'] and (
                notification and 'notification' not in old['objects'] or todo and 'todo' not in old['objects'])
            if old and (observed_at, evidence['record_id']) <= (old['observed_at'], old['evidence']['record_id']) and not supplement:
                return {'status': 'skipped', 'reason_code': 'duplicate_or_stale_observation'}
            if active is None:
                watermark = dict(old or {'key': key, 'owner': owner, 'source': source,
                    'active': False, 'episode': 0, 'objects': {}})
                watermark.update(observed_at=observed_at, evidence=evidence)
                db.execute('INSERT OR REPLACE INTO conditions VALUES (?,?)', (key, canonical(watermark)))
                return {'status': 'skipped', 'reason_code': 'unknown_observation'}
            condition = {'key': key, 'owner': owner, 'source': source, 'observed_at': observed_at,
                         'active': active, 'evidence': evidence, 'episode': old['episode'] if old else 0,
                         'objects': copy.deepcopy(old['objects']) if old else {}}
            opening = active and (not old or not old['active'])
            if opening:
                condition.update(episode=condition['episode'] + 1, objects={})
            for kind, requested in (('notification', notification), ('todo', todo)):
                object_id = condition['objects'].get(kind)
                obj = json.loads(db.execute('SELECT payload FROM objects WHERE id=?', (object_id,)).fetchone()[0]) if object_id else None
                if obj is not None and supplement:
                    continue
                # Historical seeding records the condition but creates no pending actions.
                if not effects:
                    continue
                if obj is None and active and requested:
                    obj = {'contract_version': VERSION, 'id': str(uuid4()), 'kind': kind,
                           'condition_key': key, 'episode': condition['episode'], 'source': source,
                           'created_at': now(), 'first_observed_at': observed_at, 'revision': 0,
                           'status': 'active' if kind == 'notification' else 'open',
                           'read': False, 'acknowledged': False, 'read_at': None, 'read_by': None,
                           'acknowledged_at': None, 'acknowledged_by': None,
                           'muted_until': None, 'assignee': None, 'start_at': None,
                           'due_at': None, 'timezone': 'UTC', 'note': None, 'priority': severity,
                           'verified': False}
                    condition['objects'][kind] = obj['id']
                if obj is None:
                    continue
                obj.update(title=title, body=body, severity=severity, evidence=evidence,
                           last_observed_at=observed_at, condition_active=active)
                if not active:
                    obj['resolved_at'] = observed_at
                    if kind == 'notification':
                        obj['status'] = 'resolved'
                        db.execute("UPDATE deliveries SET status='cancelled' WHERE notification=? AND status IN ('pending','failed')", (obj['id'],))
                    elif obj['status'] != 'cancelled':
                        obj.update(status='done', verified=True)
                elif kind == 'todo' and obj['status'] == 'done':
                    obj.update(status='open', verified=False)
                self._save(db, obj, owner, 'observed' if active else 'resolved')
                if kind == 'notification' and active:
                    for channel in self._channels(config, severity):
                        self._queue(db, obj, channel)
                elif kind == 'notification' and recovery_notification and old and old['active']:
                    recovery = copy.deepcopy(obj)
                    recovery.update(id=str(uuid4()), revision=0, title='Recovered: ' + title, status='resolved',
                        read=False, acknowledged=False, read_at=None, read_by=None,
                        acknowledged_at=None, acknowledged_by=None, created_at=now())
                    self._save(db, recovery, owner, 'recovery')
                    for channel in self._channels(config, severity):
                        self._queue(db, recovery, channel)
            db.execute('INSERT OR REPLACE INTO conditions VALUES (?,?)', (key, canonical(condition)))
        return {'status': 'success', 'condition_key': key, 'objects': condition['objects']}

    @staticmethod
    def _channels(config, severity):
        return sorted({name for route in config['routes']
                       if SEVERITIES.index(severity) >= SEVERITIES.index(route['minimum_severity'])
                       for name in route['channels'] if config['deliveries'][name]['enabled']})

    @staticmethod
    def _queue(db, obj, channel):
        identity = hashlib.sha256((obj['id'] + ':' + channel).encode()).hexdigest()
        db.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?)',
                   (identity, obj['id'], channel, 'pending', 0, canonical({'created_at': now()})))

    def deliveries(self):
        with self._db(False) as db:
            rows = db.execute('SELECT id,notification,channel,status,attempts,payload FROM deliveries ORDER BY id').fetchall() if db else []
        return [dict(zip(('id', 'notification_id', 'channel', 'status', 'attempts', 'receipt'), (*r[:5], json.loads(r[5])))) for r in rows]

    def snapshot(self):
        """One coherent read transaction for independent presentation adapters."""
        with self._db(False) as db:
            if db is None:
                return {'contract_version': VERSION, 'generated_at': now(), 'objects': [], 'history': [], 'deliveries': []}
            db.execute('BEGIN')
            objects = [json.loads(r[0]) for r in db.execute('SELECT payload FROM objects ORDER BY id')]
            history = [json.loads(r[0]) for r in db.execute('SELECT payload FROM history ORDER BY sequence')]
            rows = db.execute('SELECT id,notification,channel,status,attempts,payload FROM deliveries ORDER BY id').fetchall()
            deliveries = [dict(zip(('id','notification_id','channel','status','attempts','receipt'), (*r[:5],json.loads(r[5])))) for r in rows]
            return {'contract_version': VERSION, 'generated_at': now(), 'objects': objects, 'history': history, 'deliveries': deliveries}

    def dispatch(self, *, retry_unknown=False):
        """Explicit dispatch; unknown outcomes require an explicit retry choice."""
        from opsfeast.service_adapters import dispatch
        return dispatch(self, retry_unknown=retry_unknown)
