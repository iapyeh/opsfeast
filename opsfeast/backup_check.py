"""Daily backup-file presence and directory hygiene, without content reads/writes."""
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import PurePosixPath
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from opsfeast import ConfigError

VERSION = '0.1.0'


def descriptor(identity):
    """Descriptor for a profile-local recipe using this shipped implementation."""
    return {'descriptor_version': '0.3.0', 'id': 'daily-backups', 'version': VERSION,
            **identity, 'title': 'Daily backups',
            'description': 'Check dated backup presence, expired files and unexpected entries; never delete files.',
            'access_mode': 'read',
            'retention': {'contract': 'backup-files-check', 'version': VERSION,
                          'description': 'Presence-only backup checks, saved policy and complete or explicitly incomplete file lists.',
                          'schema': 'backup-files-check.schema.json'},
            'runner': {'contract': 'python-recipe', 'version': '0.1.0', 'entrypoint': 'main.py'},
            'platforms': {'implemented': ['linux', 'freebsd', 'macos'], 'tested': [], 'planned': []},
            'dependencies': {'controller': ['Python 3.11+', 'OpsFeast backup-files-check 0.1.0', 'SSHScript 7.0.0'], 'target': ['Python 3.8+']},
            'permissions': {'sudo': False, 'su': False},
            'side_effects': ['Read directory entries and file metadata over the supplied connection.',
                             'Save raw and retained observations and dispatch configured consumers.'],
            'inputs': {'variables': {
                'backups': {'type': 'array', 'required': True},
                'timezone': {'type': 'string', 'default': 'Asia/Taipei'},
                'retention_days': {'type': 'integer', 'default': 90, 'minimum': 0, 'maximum': 365000},
                'max_entries': {'type': 'integer', 'default': 10000, 'minimum': 1, 'maximum': 100000},
                'target_python': {'type': 'string', 'default': 'python3'}}},
            'output': {'schema_version': '0.1.0'}}
# Runs over the supplied session. Does not follow symlinks or open file contents.
SCAN = r'''
import json, os, stat, sys, pwd
if sys.version_info < (3, 8):
    raise RuntimeError('Python 3.8+ required')
request = json.load(sys.stdin)
output = []
class ScanLimit(Exception):
    pass
for directory in request['directories']:
    result = {'directory': directory, 'entries': [], 'scan_status': 'complete', 'reason_code': 'scanned'}
    def scan_directory(descriptor, prefix, depth):
        if depth > 64:
            raise ScanLimit('depth_limit')
        with os.scandir(descriptor) as iterator:
            for entry in iterator:
                if len(result['entries']) >= request['max_entries']:
                    raise ScanLimit('entry_limit')
                relative = prefix + entry.name
                relative.encode('utf-8')
                info = entry.stat(follow_symlinks=False)
                kind = 'directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode) else 'other'
                result['entries'].append({'path': relative, 'kind': kind, 'size_bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
                if kind == 'directory':
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    try:
                        scan_directory(child, relative + '/', depth + 1)
                    finally:
                        os.close(child)
    try:
        root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            scan_directory(root, '', 0)
        finally:
            os.close(root)
    except (OSError, ScanLimit, UnicodeError) as error:
        reason = str(error) if isinstance(error, ScanLimit) else 'unrepresentable_filename' if isinstance(error, UnicodeError) else 'directory_unreadable'
        result.update(scan_status='incomplete', reason_code=reason)
    output.append(result)
uid = os.geteuid()
try:
    username = pwd.getpwuid(uid).pw_name
except KeyError:
    username = None
json.dump({'backups': output, 'target_python_version': sys.version.split()[0],
           'actor': {'username': username, 'effective_uid': uid, 'mode': 'root' if uid == 0 else 'user'}},
          sys.stdout, ensure_ascii=True, allow_nan=False)
'''


def inputs(values):
    if not isinstance(values, dict) or set(values) - {'timezone', 'retention_days', 'backups', 'max_entries', 'target_python'}:
        raise ConfigError('invalid backup-check inputs')
    try:
        zone = ZoneInfo(values.get('timezone', 'Asia/Taipei'))
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        raise ConfigError('unknown backup timezone') from None
    days = values.get('retention_days', 90)
    maximum = values.get('max_entries', 10000)
    if type(days) is not int or not 0 <= days <= 365000 or type(maximum) is not int or not 1 <= maximum <= 100000:
        raise ConfigError('invalid backup age or entry limit')
    python = values.get('target_python', 'python3')
    if not isinstance(python, str) or not python or '\x00' in python:
        raise ConfigError('target_python must identify the reviewed target interpreter')
    backups = values.get('backups')
    if not isinstance(backups, list) or not backups:
        raise ConfigError('backups must be a nonempty list')
    names = set()
    for backup in backups:
        if (not isinstance(backup, dict) or set(backup) - {'name', 'directory', 'patterns', 'ready_after', 'grace_minutes'}
                or not {'name', 'directory', 'patterns'} <= set(backup)
                or not isinstance(backup['name'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}', backup['name'])
                or backup['name'] in names):
            raise ConfigError('invalid or duplicate backup group')
        names.add(backup['name'])
        directory = backup['directory']
        if (not isinstance(directory, str) or not directory.startswith('/') or directory == '/'
                or '\x00' in directory or '..' in PurePosixPath(directory).parts):
            raise ConfigError('backup directory requires a bounded absolute target path')
        patterns = backup['patterns']
        if not isinstance(patterns, list) or not patterns or any(not isinstance(p, str) for p in patterns) or len(set(patterns)) != len(patterns):
            raise ConfigError('patterns must be unique filenames')
        for pattern in patterns:
            if (not isinstance(pattern, str) or pattern.count('{date}') != 1 or '\x00' in pattern
                    or pattern.startswith('/') or any(p in ('', '.', '..') for p in pattern.split('/'))
                    or any('{date}' in p for p in pattern.split('/')[:-1])
                    or '{' in pattern.replace('{date}', '') or '}' in pattern.replace('{date}', '')):
                raise ConfigError('each pattern needs one {date} and a safe relative path')
        ready = backup.get('ready_after', '00:00')
        if not isinstance(ready, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', ready):
            raise ConfigError('ready_after must be HH:MM')
        if type(backup.get('grace_minutes', 0)) is not int or not 0 <= backup.get('grace_minutes', 0) <= 1439:
            raise ConfigError('invalid backup grace period')
        if int(ready[:2]) * 60 + int(ready[3:]) + backup.get('grace_minutes', 0) >= 1440:
            raise ConfigError('daily backup deadline must fall within its filename date')
    return zone, days, maximum, python, backups


def classify(backup, scan, instant, zone, days):
    today = instant.astimezone(zone).date()
    cutoff = today - timedelta(days=days)
    expressions = [re.compile('^' + re.escape(p).replace(re.escape('{date}'), r'(\d{4}-\d{2}-\d{2})') + '$') for p in backup['patterns']]
    directories = {str(parent) for p in backup['patterns'] for parent in PurePosixPath(p).parents if str(parent) != '.'}
    expected = [p.replace('{date}', today.isoformat()) for p in backup['patterns']]
    files, unexpected = [], []
    for entry in scan['entries']:
        name = entry['path']
        if entry['kind'] == 'directory' and name in directories:
            continue
        matched_date = None
        for expression in expressions:
            match = expression.fullmatch(name)
            if match:
                try:
                    matched_date = date.fromisoformat(match.group(1))
                except ValueError:
                    pass
                break
        if entry['kind'] == 'file' and matched_date is not None:
            age = (today - matched_date).days
            files.append(dict(entry, backup_date=matched_date.isoformat(), age_days=age))
        else:
            unexpected.append(dict(entry, reason_code='unexpected_path_type_or_date'))
    by_name = {f['path']: f for f in files}
    complete = scan['scan_status'] == 'complete'
    daily = [{'path': name, 'present': True if name in by_name else False if complete else None,
              'size_bytes': by_name[name]['size_bytes'] if name in by_name else None,
              'mtime_ns': by_name[name]['mtime_ns'] if name in by_name else None} for name in expected]
    deadline = datetime.combine(today, time.fromisoformat(backup.get('ready_after', '00:00')), zone) + timedelta(minutes=backup.get('grace_minutes', 0))
    health = 'healthy' if all(f['present'] is True for f in daily) else 'unknown' if not complete else 'pending' if instant < deadline else 'missing'
    return {'name': backup['name'], 'directory': backup['directory'], 'observed_at': instant.astimezone(timezone.utc).isoformat(timespec='microseconds'),
            'scan_status': scan['scan_status'], 'reason_code': scan['reason_code'], 'health': health,
            'patterns': backup['patterns'], 'ready_after': backup.get('ready_after', '00:00'),
            'grace_minutes': backup.get('grace_minutes', 0), 'deadline': deadline.astimezone(timezone.utc).isoformat(timespec='microseconds'),
            'expected_files': daily, 'expired_files': sorted([f for f in files if f['age_days'] > days], key=lambda f:f['path']),
            'unexpected_entries': sorted(unexpected, key=lambda f:f['path']), 'backup_count': len(files),
            'scanned_entries': len(scan['entries']), 'cutoff_exclusive': cutoff.isoformat()}


def execute(recipe):
    zone, days, maximum, python, backups = inputs(recipe.vars)
    instant = datetime.now(timezone.utc)
    actor = {'username': None, 'effective_uid': None, 'mode': 'unverified'}
    target_python_version = None
    request = {'directories': [b['directory'] for b in backups], 'max_entries': maximum}
    try:
        result = recipe.session.exec_command([python, '-c', SCAN], input=json.dumps(request),
                                             command_timeout=recipe.timeout, check=False)
        if result.exitcode != 0 or result.stdout_truncated or result.stderr_truncated:
            raise ValueError('scan command incomplete')
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict) or set(payload) != {'backups', 'actor', 'target_python_version'}:
            raise ValueError('invalid scan envelope')
        from collection_evidence import validate as validate_evidence
        validate_evidence({'contract_version':'0.1.0', 'actor':payload['actor'], 'probes':[]})
        if not isinstance(payload['target_python_version'], str) or not re.fullmatch(r'\d+\.\d+\.\d+', payload['target_python_version']):
            raise ValueError('invalid target runtime evidence')
        scans = payload['backups']
        if not isinstance(scans, list) or len(scans) != len(backups):
            raise ValueError('invalid scan result')
        for backup, scan in zip(backups, scans):
            if scan.get('directory') != backup['directory'] or scan.get('scan_status') not in ('complete', 'incomplete') or not isinstance(scan.get('entries'), list):
                raise ValueError('invalid scan result')
            if len(scan['entries']) > maximum or len({e['path'] for e in scan['entries']}) != len(scan['entries']):
                raise ValueError('invalid scan entries')
            for e in scan['entries']:
                if (set(e) != {'path', 'kind', 'size_bytes', 'mtime_ns'} or not isinstance(e['path'], str)
                        or e['path'].startswith('/') or any(p in ('', '.', '..') for p in e['path'].split('/'))
                        or e['kind'] not in ('file', 'directory', 'symlink', 'other')
                        or type(e['size_bytes']) is not int or e['size_bytes'] < 0 or type(e['mtime_ns']) is not int):
                    raise ValueError('invalid scan entry')
        groups = [classify(b, s, instant, zone, days) for b, s in zip(backups, scans)]
        actor = payload['actor']
        target_python_version = payload['target_python_version']
    except Exception as error:
        # Output/errors may expose paths or file content from a substituted interpreter.
        # Preserve the safe error class and do not report absence from a failed scan.
        groups = [classify(b, {'entries': [], 'scan_status': 'incomplete', 'reason_code': type(error).__name__}, instant, zone, days) for b in backups]
    status = 'success' if all(g['health'] == 'healthy' and g['scan_status'] == 'complete' for g in groups) else 'partial'
    data = {'check_date': instant.astimezone(zone).date().isoformat(), 'actor': actor, 'target_python_version': target_python_version,
            'policy': {'timezone': zone.key, 'retention_days': days, 'age_basis': 'filename_date', 'comparison': 'strictly_greater', 'max_entries': maximum},
            'backups': groups}
    return {'status': status, 'reason_code': 'checked' if status == 'success' else 'backup_attention',
            'message': 'Read-only daily backup-file check; presence only, no integrity or restore verification.', 'data': data}
