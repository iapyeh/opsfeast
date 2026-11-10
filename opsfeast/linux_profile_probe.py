"""Self-contained Linux snapshot probe, sent on stdin; Python 3.8+ stdlib only.

No password/shadow, command-line, environment or process memory is emitted.
Test helpers accept a synthetic filesystem root; the command-line entrypoint
always uses / and supports only the two reviewed acquisition kinds.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from uuid import UUID

MAX_FILE = 1024 * 1024
MAX_OUTPUT = 131072


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def bounded(path, maximum):
    with path.open('rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('source_size_limit')
    return data.decode('utf-8')


def dataset(source, scope):
    return {'source': source, 'scope': scope, 'observed_at': now(), 'complete': True,
            'items': [], 'reason_codes': [], 'attempted_count': 0, 'unavailable_count': 0}


def gap(data, reason):
    data['complete'] = False
    if reason not in data['reason_codes']:
        data['reason_codes'].append(reason)


def identifier(value):
    if not value.isascii() or not value.isdigit() or not 0 <= int(value) <= 4294967295:
        raise ValueError('invalid_numeric_id')
    return int(value)


def accounts(root, kind, limit, deadline):
    path = root / 'etc' / ('passwd' if kind == 'users' else 'group')
    data = dataset('/etc/' + path.name, 'local-file-only; no NSS/LDAP or effective login/privilege claim')
    try:
        before = path.stat()
        text = bounded(path, MAX_FILE)
        seen = set()
        for line in text.splitlines():
            if not line or line.startswith('#'):
                continue
            if len(data['items']) >= limit or time.monotonic() >= deadline:
                gap(data, 'item_or_time_limit'); break
            data['attempted_count'] += 1
            fields = line.split(':')
            try:
                if len(fields) != (7 if kind == 'users' else 4) or not fields[0] or len(fields[0]) > 512:
                    raise ValueError('invalid_row')
                name = fields[0]
                if name in seen or name.startswith(('+', '-')) or '\x00' in line:
                    raise ValueError('duplicate_or_unsupported_row')
                if kind == 'users':
                    shell = fields[6]
                    if len(fields[5]) > 4096 or len(shell) > 4096:
                        raise ValueError('oversized_path')
                    row = {'name': name, 'uid': identifier(fields[2]), 'gid': identifier(fields[3]),
                           'home': fields[5], 'shell': shell,
                           'shell_hint': 'noninteractive_shell' if shell.rsplit('/', 1)[-1] in ('nologin', 'false')
                                         else 'shell_configured' if shell else 'default_shell'}
                else:
                    members = fields[3].split(',') if fields[3] else []
                    if any(not m or len(m) > 512 for m in members) or len(members) > 5000:
                        raise ValueError('invalid_group_members')
                    row = {'name': name, 'gid': identifier(fields[2]), 'members': members}
                # fields[1] can contain a legacy hash: never serialize it.
                data['items'].append(row); seen.add(name)
            except ValueError:
                data['unavailable_count'] += 1; gap(data, 'invalid_or_duplicate_rows')
        after = path.stat()
        if (before.st_ino, before.st_mtime_ns, before.st_size) != (after.st_ino, after.st_mtime_ns, after.st_size):
            gap(data, 'source_changed_during_read')
    except PermissionError:
        gap(data, 'permission_denied')
    except FileNotFoundError:
        gap(data, 'source_missing')
    except (ValueError, UnicodeError):
        gap(data, 'invalid_or_oversized_source')
    except OSError:
        gap(data, 'source_read_failed')
    data['observed_at'] = now()
    return data


def stat_identity(text, pid):
    prefix, separator, tail = text.rpartition(') ')
    if not separator or prefix.split(' (', 1)[0] != str(pid):
        raise ValueError('invalid_stat_identity')
    fields = tail.split()
    if len(fields) < 20:
        raise ValueError('incomplete_stat')
    return identifier(fields[1]), int(fields[19]), int(fields[11]), int(fields[12])


def processes(root, limit, deadline):
    proc = root / 'proc'
    data = dataset('/proc/[pid]/{stat,status,exe}', 'collector-visible procfs/PID namespace only; point-in-time snapshot')
    try:
        boot_id = str(UUID(bounded(proc / 'sys/kernel/random/boot_id', 128).strip()))
    except (OSError, ValueError, UnicodeError):
        boot_id = None
    data['boot_id'] = boot_id
    if boot_id is None:
        gap(data, 'boot_id_unavailable')
    try:
        # Stop enumerating once a limit is hit: even directory discovery is bounded.
        with os.scandir(proc) as entries:
            for entry in entries:
                if not entry.name.isascii() or not entry.name.isdigit():
                    continue
                if data['attempted_count'] >= limit or time.monotonic() >= deadline:
                    gap(data, 'item_or_time_limit'); break
                data['attempted_count'] += 1
                path = proc / entry.name
                try:
                    before = stat_identity(bounded(path / 'stat', 32768), entry.name)
                    status = {}
                    for line in bounded(path / 'status', 32768).splitlines():
                        key, sep, value = line.partition(':')
                        if sep: status[key] = value.strip()
                    after = stat_identity(bounded(path / 'stat', 32768), entry.name)
                    if before[1] != after[1]:
                        raise ValueError('pid_reused_during_read')
                    uids, gids = status['Uid'].split(), status['Gid'].split()
                    if status['Pid'] != entry.name or len(uids) != 4 or len(gids) != 4:
                        raise ValueError('inconsistent_process_identity')
                    def memory(key):
                        fields = status.get(key, '').split()
                        if not fields: return None
                        if len(fields) != 2 or fields[1] != 'kB' or not fields[0].isdigit():
                            raise ValueError('invalid_memory_field')
                        return int(fields[0]) * 1024
                    try:
                        executable = os.readlink(path / 'exe')
                        executable_state = 'observed'
                    except OSError:
                        executable, executable_state = None, 'unavailable'
                    row = {'pid': int(entry.name), 'start_ticks': before[1], 'ppid': before[0],
                           'name': status['Name'], 'state': status['State'],
                           'uid_real': identifier(uids[0]), 'uid_effective': identifier(uids[1]),
                           'gid_real': identifier(gids[0]), 'gid_effective': identifier(gids[1]),
                           'threads': identifier(status['Threads']), 'rss_bytes': memory('VmRSS'),
                           'virtual_bytes': memory('VmSize'), 'cpu_user_ticks': after[2],
                           'cpu_system_ticks': after[3], 'executable': executable,
                           'executable_state': executable_state,
                           'executable_deleted': executable.endswith(' (deleted)') if executable is not None else None}
                    data['items'].append(row)
                except PermissionError:
                    data['unavailable_count'] += 1; gap(data, 'permission_denied')
                except FileNotFoundError:
                    data['unavailable_count'] += 1; gap(data, 'process_disappeared')
                except (ValueError, KeyError, UnicodeError):
                    data['unavailable_count'] += 1; gap(data, 'invalid_or_changed_process')
                except OSError:
                    data['unavailable_count'] += 1; gap(data, 'process_read_failed')
    except PermissionError:
        gap(data, 'permission_denied')
    except OSError:
        gap(data, 'procfs_unavailable')
    data['observed_at'] = now()
    return data


def snapshot(kind, limit, budget, *, root=Path('/')):
    started = now(); deadline = time.monotonic() + budget
    names = ('users', 'groups') if kind == 'accounts' else ('processes',)
    data = {'contract_version': '0.1.0', 'kind': kind, 'platform': 'linux',
            'started_at': started, 'observed_at': started, 'effective_uid': os.geteuid(),
            'datasets': {name: accounts(root, name, limit, deadline) if kind == 'accounts'
                         else processes(root, limit, deadline) for name in names}}
    data['observed_at'] = now()
    while len(json.dumps(data, ensure_ascii=True).encode()) > MAX_OUTPUT:
        selected = max(data['datasets'].values(), key=lambda d: len(d['items']))
        if not selected['items']:
            raise ValueError('metadata_size_limit')
        selected['items'].pop(); gap(selected, 'output_size_limit')
    return data


def main():
    if sys.platform != 'linux':
        print(json.dumps({'platform': sys.platform})); return
    kind, limit, budget = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    if kind not in ('accounts', 'processes') or not 1 <= limit <= 5000 or not 0 < budget <= 120:
        raise ValueError('invalid_probe_arguments')
    print(json.dumps(snapshot(kind, limit, budget), ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
