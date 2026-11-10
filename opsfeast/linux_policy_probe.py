"""Self-contained Linux policy probe; Python 3.8+ stdlib, fixed read queries.

Executed on stdin by the scoped Linux profile service. Raw tool output and
configuration contents never leave this process; only reviewed projections do.
"""
from datetime import datetime, timezone
import glob
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import time

MAX_CAPTURE = 262144
MAX_FILE = 65536
MAX_OUTPUT = 131072
MAX_FILES = 64
DATASETS = {
    'ssh-policy': ('ssh_policy',),
    'sudo-policy': ('sudo_policy',),
    'firewall-policy': ('nft_rules', 'iptables_rules', 'ip6tables_rules', 'firewalld_runtime', 'firewalld_permanent', 'ufw_runtime'),
    'time-sync': ('clock_state', 'chrony_state', 'chrony_sources', 'ntp_state', 'ntp_peers', 'timesyncd_state', 'time_configuration'),
    'logging-config': ('journald_configuration', 'journal_state', 'syslog_configuration', 'application_logs', 'log_rotation'),
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def section(source, scope):
    return {'source': source, 'scope': scope, 'observed_at': now(), 'complete': True,
            'items': [], 'reason_codes': [], 'attempted_count': 0, 'unavailable_count': 0, 'commands': []}


def gap(data, reason):
    data['complete'] = False
    if reason not in data['reason_codes']: data['reason_codes'].append(reason)


def item(data, name, value, basis, source, limit):
    if len(data['items']) >= limit:
        gap(data, 'item_limit'); return
    data['items'].append({'name': name, 'value': value, 'basis': basis, 'source': source})


def context(value):
    if not isinstance(value, dict) or set(value) - {'user', 'host', 'addr', 'laddr', 'lport'}:
        raise ValueError('invalid_ssh_context')
    if value and not {'user', 'host', 'addr', 'laddr', 'lport'} <= set(value):
        raise ValueError('ssh_context_requires_all_five_fields')
    result = {}
    for key, val in value.items():
        if key in ('addr', 'laddr'):
            if not isinstance(val, str) or '%' in val:
                raise ValueError('ssh_context_requires_unscoped_ip_literal')
            result[key] = str(ipaddress.ip_address(val))
        elif key == 'lport':
            if type(val) is not int or not 1 <= val <= 65535: raise ValueError('invalid_ssh_port')
            result[key] = str(val)
        else:
            if not isinstance(val, str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,255}', val):
                raise ValueError('invalid_ssh_context_text')
            result[key] = val
    return result


def run(argv, deadline):
    """Bound output and time while draining both pipes; reap only owned processes."""
    deadline = min(deadline, time.monotonic() + 3)
    evidence = {'argv': argv, 'started_at': now(), 'completed_at': now(),
                'exitcode': None, 'termination_status': 'not_started', 'reason_code': None}
    if time.monotonic() >= deadline:
        evidence['reason_code'] = 'time_limit'; evidence['completed_at'] = now(); return '', '', evidence
    path = shutil.which(argv[0])
    if path is None and argv[0] == 'sshd':
        path = next((p for p in ('/usr/sbin/sshd', '/sbin/sshd') if os.path.isfile(p) and os.access(p, os.X_OK)), None)
    if path is None:
        evidence['reason_code'] = 'tool_missing'; evidence['completed_at'] = now(); return '', '', evidence
    process = None; streams = {1: bytearray(), 2: bytearray()}
    try:
        env = dict(os.environ, LC_ALL='C', LANG='C', SYSTEMD_PAGER='cat', PAGER='cat')
        process = subprocess.Popen([path, *argv[1:]], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, env=env)
        evidence['termination_status'] = 'unknown'
        with selectors.DefaultSelector() as poll:
            poll.register(process.stdout, selectors.EVENT_READ, 1)
            poll.register(process.stderr, selectors.EVENT_READ, 2)
            while poll.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    evidence['reason_code'] = 'time_limit'; break
                for key, _ in poll.select(min(.1, remaining)):
                    block = os.read(key.fileobj.fileno(), 8192)
                    if not block:
                        poll.unregister(key.fileobj); continue
                    streams[key.data].extend(block)
                    if sum(len(v) for v in streams.values()) > MAX_CAPTURE:
                        evidence['reason_code'] = 'command_output_limit'; break
                if evidence['reason_code']: break
        if evidence['reason_code']:
            os.killpg(process.pid, signal.SIGKILL)
        try:
            evidence['exitcode'] = process.wait(timeout=max(.05, min(.5, deadline - time.monotonic())))
            evidence['termination_status'] = 'confirmed'
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            try:
                evidence['exitcode'] = process.wait(timeout=.5)
                evidence['termination_status'] = 'confirmed'
            except subprocess.TimeoutExpired: pass
            evidence['reason_code'] = evidence['reason_code'] or 'time_limit'
    except (OSError, ValueError):
        evidence['reason_code'] = evidence['reason_code'] or 'command_start_or_read_failed'
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=.5)
                    evidence['termination_status'] = 'confirmed'
                except (OSError, subprocess.TimeoutExpired): pass
            for stream in (process.stdout, process.stderr):
                if stream is not None: stream.close()
        evidence['completed_at'] = now()
    if evidence['reason_code']: return '', '', evidence
    try:
        out, err = (bytes(streams[n]).decode('utf-8') for n in (1, 2))
    except UnicodeError:
        evidence['reason_code'] = 'invalid_command_encoding'; return '', '', evidence
    if evidence['exitcode'] != 0:
        lower = (err if err.strip() else out).lower()
        evidence['reason_code'] = ('permission_denied' if any(s in lower for s in ('permission denied', 'operation not permitted', 'not authorized', 'not authorised'))
                                  else 'authentication_required' if 'password is required' in lower
                                  else 'policy_query_denied' if any(s in lower for s in ('not allowed to run sudo', 'may not run sudo'))
                                  else 'unsupported_tool_option' if any(s in lower for s in ('unknown option', 'unrecognized option', 'invalid option'))
                                  else 'invalid_configuration' if any(s in lower for s in ('bad configuration option', 'syntax error'))
                                  else 'daemon_unavailable' if any(s in lower for s in ('cannot talk to daemon', 'failed to connect to bus', 'connection refused'))
                                  else 'command_failed')
        return '', '', evidence
    return out, err, evidence


def query(data, argv, deadline):
    data['attempted_count'] += 1
    out, err, evidence = run(argv, deadline)
    data['commands'].append(evidence); data['observed_at'] = evidence['completed_at']
    if evidence['reason_code']:
        gap(data, evidence['reason_code']); data['unavailable_count'] += 1; return None
    # Stderr may carry a warning about incomplete results; never retain its text.
    if err.strip(): gap(data, 'command_warning')
    return out


SSH_FIELDS = set('port listenaddress addressfamily permitrootlogin passwordauthentication pubkeyauthentication '
    'kbdinteractiveauthentication challengeresponseauthentication authenticationmethods permitemptypasswords '
    'usepam allowusers denyusers allowgroups denygroups maxauthtries maxsessions logingracetime '
    'authorizedkeysfile authorizedprincipalsfile hostkeyalgorithms pubkeyacceptedalgorithms ciphers macs '
    'kexalgorithms allowtcpforwarding allowagentforwarding permitopen permitlisten gatewayports '
    'x11forwarding permittty chrootdirectory strictmodes loglevel syslogfacility'.split())


def ssh_policy(deadline, limit, options):
    selected = context(options)
    scope = 'sshd effective configuration for explicit Match context' if selected else 'sshd global/default configuration; no Match connection context'
    data = section('sshd -T', scope)
    argv = ['sshd', '-T']
    if selected: argv += ['-C', ','.join(k + '=' + selected[k] for k in sorted(selected))]
    out = query(data, argv, deadline)
    if out is None: return data
    values = {}
    for line in out.splitlines():
        key, separator, value = line.partition(' ')
        if not separator:
            gap(data, 'unrecognized_output'); continue
        if key in SSH_FIELDS: values.setdefault(key, []).append(value.strip())
    if not {'port', 'permitrootlogin'} <= set(values): gap(data, 'unrecognized_output')
    for name, value in values.items():
        item(data, name, value[0] if len(value) == 1 else value,
             'effective' if selected else 'configured', 'sshd -T', limit)
    item(data, 'match_context', selected, 'context', 'operator-selected context', limit)
    return data


def sudo_policy(deadline, limit):
    data = section('sudo -n -ll', 'selected actor only; no other-user enumeration or privileged command execution')
    out = query(data, ['sudo', '-n', '-ll'], deadline)
    if out is None: return data
    entry = None; commands = False; recognized = False
    for line in out.splitlines():
        text = line.strip()
        if not text: continue
        if text == 'Sudoers entry:':
            if entry: item(data, 'entry-' + str(len(data['items']) + 1), entry, 'effective', 'sudo -n -ll', limit)
            entry = {'run_as_users': [], 'run_as_groups': [], 'options': [], 'commands': []}
            commands = False; recognized = True
        elif entry is not None:
            if text.startswith(('RunAsUsers:', 'RunAsGroups:')):
                key = 'run_as_users' if text.startswith('RunAsUsers:') else 'run_as_groups'
                values = [v.strip() for v in text.split(':', 1)[1].split(',')]
                if any(not re.fullmatch(r'[A-Za-z0-9_%!#.@+*-]+', v) for v in values):
                    gap(data, 'sudo_details_omitted')
                else: entry[key] = values
                commands = False
            elif text.startswith('Options:'):
                allowed = {'authenticate', '!authenticate', 'noexec', '!noexec', 'setenv', '!setenv', 'log_input', 'log_output', 'use_pty', 'requiretty'}
                values = [v.strip() for v in text.split(':', 1)[1].split(',')]
                entry['options'] = [v for v in values if v in allowed]
                if len(entry['options']) != len(values): gap(data, 'sudo_details_omitted')
                commands = False
            elif text == 'Commands:': commands = True
            elif commands:
                try:
                    tokens = shlex.split(text)
                    if not tokens: continue
                    executable = tokens[0]
                    if not (executable.lstrip('!').startswith('/') or executable in ('ALL', '!ALL', 'sudoedit', '!sudoedit')):
                        raise ValueError('unrecognized_command')
                    entry['commands'].append({'executable': executable, 'arguments_omitted': len(tokens) > 1})
                    if len(tokens) > 1: gap(data, 'sudo_arguments_omitted')
                except ValueError: gap(data, 'sudo_details_omitted')
            else: gap(data, 'sudo_details_omitted')
    if entry: item(data, 'entry-' + str(len(data['items']) + 1), entry, 'effective', 'sudo -n -ll', limit)
    if not recognized: gap(data, 'unrecognized_output')
    # Defaults and arbitrary command arguments may contain secret values.
    gap(data, 'sudo_defaults_not_projected')
    return data


def strip_nft(value):
    if isinstance(value, dict):
        return {k: strip_nft(v) for k, v in value.items() if k not in ('comment', 'prefix', 'userdata')}
    if isinstance(value, list): return [strip_nft(v) for v in value]
    return value


def firewall(deadline, limit):
    result = {}
    commands = {'nft_rules': ['nft', '-j', '-n', '-a', 'list', 'ruleset'],
                'iptables_rules': ['iptables-save'], 'ip6tables_rules': ['ip6tables-save'],
                'firewalld_runtime': ['firewall-cmd', '--list-all-zones'],
                'firewalld_permanent': ['firewall-cmd', '--permanent', '--list-all-zones'],
                'ufw_runtime': ['ufw', 'status', 'verbose']}
    for name, argv in commands.items():
        data = section(' '.join(argv), 'visible network namespace; ' + ('configured frontend policy' if name == 'firewalld_permanent' else 'runtime query; frontends may describe the same kernel rules'))
        result[name] = data
        out = query(data, argv, deadline)
        if out is None: continue
        if name == 'nft_rules':
            try:
                parsed = json.loads(out)
                if not isinstance(parsed, dict) or not isinstance(parsed.get('nftables'), list): raise ValueError('invalid_nft')
                for index, row in enumerate(parsed['nftables']):
                    if not isinstance(row, dict): raise ValueError('invalid_nft_row')
                    safe = strip_nft(row)
                    if safe != row: gap(data, 'firewall_text_omitted')
                    item(data, 'object-' + str(index), safe, 'runtime', 'nft JSON', limit)
            except (ValueError, TypeError):
                data['items'] = []; gap(data, 'unrecognized_output')
        elif name in ('iptables_rules', 'ip6tables_rules'):
            if not out.strip() or any(line.startswith('*') for line in out.splitlines()):
                table = None
                for index, line in enumerate(out.splitlines()):
                    if not line or line.startswith('#'): continue
                    if line.startswith('*'):
                        if table is not None: gap(data, 'unrecognized_output')
                        table = line[1:]
                    elif line == 'COMMIT':
                        if table is None: gap(data, 'unrecognized_output')
                        table = None
                    elif table is None or not line.startswith((':', '-A ', '-I ')):
                        gap(data, 'unrecognized_output')
                    try:
                        tokens = shlex.split(line)
                        safe = []; i = 0
                        while i < len(tokens):
                            if tokens[i].split('=', 1)[0] in ('--comment', '--log-prefix', '--nflog-prefix', '--string', '--hex-string'):
                                gap(data, 'firewall_text_omitted'); i += 1 if '=' in tokens[i] else 2; continue
                            safe.append(tokens[i]); i += 1
                        item(data, 'line-' + str(index + 1), safe, 'runtime', argv[0], limit)
                    except ValueError: gap(data, 'unrecognized_output')
                if table is not None: gap(data, 'unrecognized_output')
            else: gap(data, 'unrecognized_output')
        else:
            # Source-native frontend view, not a parser claiming rule equivalence.
            for index, line in enumerate(out.splitlines()):
                safe = line.split('#', 1)[0].strip()
                redacted = re.sub(r'''prefix=(?:"[^"]*"|'[^']*'|\S+)''', 'prefix=[omitted]', safe)
                if redacted != safe: gap(data, 'firewall_text_omitted')
                safe = redacted
                if safe: item(data, 'line-' + str(index + 1), safe, 'configured' if name == 'firewalld_permanent' else 'runtime', argv[0], limit)
            if not out.strip(): gap(data, 'unrecognized_output')
    return result


def scan_files(data, root, patterns, allowed, parse, deadline, limit):
    """Bounded include discovery. Never execute scripts or dump source contents."""
    queue = [(pattern, False) for pattern in patterns]; seen = set(); count = 0; found = False
    boundaries = [(root / p.lstrip('/')).resolve() for p in allowed]
    while queue:
        pattern, required = queue.pop(0)
        if time.monotonic() >= deadline:
            gap(data, 'time_limit'); break
        if not pattern.startswith('/') or any(c in pattern for c in ('$', '\x00', '\n')):
            gap(data, 'unsupported_include'); continue
        matched = False
        for native in glob.iglob(str(root / pattern.lstrip('/'))):
            if time.monotonic() >= deadline:
                gap(data, 'time_limit'); queue.clear(); break
            matched = True; path = Path(native)
            try:
                real = path.resolve()
                if not any(os.path.commonpath((str(real), str(b))) == str(b) for b in boundaries):
                    gap(data, 'include_outside_scope'); continue
                if re.search(r'(?:shadow|passwd|password|secret|\.key$|\.pem$|\.p12$)', real.name, re.I):
                    gap(data, 'sensitive_include_omitted'); continue
                if real in seen: continue
                seen.add(real); count += 1
                if count > MAX_FILES:
                    gap(data, 'file_limit'); queue.clear(); break
                if required and real.is_dir():
                    queue.append((pattern.rstrip('/') + '/*', True)); continue
                if not real.is_file():
                    gap(data, 'unsupported_source'); continue
                data['attempted_count'] += 1
                before = real.stat()
                with real.open('rb') as stream: raw = stream.read(MAX_FILE + 1)
                if len(raw) > MAX_FILE: gap(data, 'file_size_limit'); continue
                text = raw.decode('utf-8')
                source = '/' + path.relative_to(root).as_posix()
                for include in parse(text, source, data, limit): queue.append((include, True))
                after = real.stat()
                if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                    gap(data, 'source_changed_during_read')
                found = True
            except PermissionError:
                data['unavailable_count'] += 1; gap(data, 'permission_denied')
            except (OSError, ValueError, UnicodeError, RuntimeError):
                data['unavailable_count'] += 1; gap(data, 'source_read_or_parse_failed')
        if required and not matched: gap(data, 'included_source_missing')
    if not found: gap(data, 'source_missing')
    data['observed_at'] = now()


TIME_FIELDS = set('server pool peer makestep rtcsync local allow deny restrict driftfile maxupdateskew minsources '
                  'NTP FallbackNTP RootDistanceMaxSec PollIntervalMinSec PollIntervalMaxSec ConnectionRetrySec'.split())
JOURNAL_FIELDS = set('Storage Compress Seal SplitMode SyncIntervalSec RateLimitIntervalSec RateLimitBurst '
    'SystemMaxUse SystemKeepFree SystemMaxFileSize SystemMaxFiles RuntimeMaxUse RuntimeKeepFree RuntimeMaxFileSize '
    'RuntimeMaxFiles MaxRetentionSec MaxFileSec ForwardToSyslog ForwardToKMsg ForwardToConsole ForwardToWall '
    'MaxLevelStore MaxLevelSyslog MaxLevelKMsg MaxLevelConsole MaxLevelWall ReadKMsg Audit'.split())


def settings_parser(fields):
    def parse(text, source, data, limit):
        includes = []
        for number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', ';', '[')): continue
            try: tokens = shlex.split(stripped, comments=True)
            except ValueError:
                gap(data, 'unrecognized_configuration'); continue
            if not tokens: continue
            if tokens[0] in ('include', 'confdir', 'sourcedir'):
                if len(tokens) != 2: gap(data, 'unsupported_include'); continue
                includes.append(tokens[1] + ('/*.conf' if tokens[0] == 'confdir' else '/*.sources' if tokens[0] == 'sourcedir' else '')); continue
            name, sep, value = stripped.partition('=')
            if sep and name.strip() in fields:
                item(data, name.strip() + '@' + str(number), value.split('#', 1)[0].strip(), 'configured', source, limit)
            elif tokens[0] in fields:
                # NTP authentication keys/PSKs are deliberately not emitted.
                values = tokens[1:]
                for sensitive in ('key', 'keyfile', 'password', 'secret', 'token'):
                    while sensitive in values:
                        at = values.index(sensitive); values = values[:at] + values[at+2:]
                        gap(data, 'configuration_fields_omitted')
                item(data, tokens[0] + '@' + str(number), values, 'configured', source, limit)
        return includes
    return parse


def timed(deadline, limit, root):
    result = {}
    specs = {
        'clock_state': (['timedatectl', 'show', '--property=Timezone', '--property=LocalRTC', '--property=NTP', '--property=NTPSynchronized', '--property=TimeUSec', '--property=RTCTimeUSec'], '='),
        'chrony_state': (['chronyc', '-n', 'tracking'], ':'),
        'chrony_sources': (['chronyc', '-n', 'sources'], 'columns'),
        'ntp_state': (['ntpq', '-n', '-c', 'rv'], None),
        'ntp_peers': (['ntpq', '-pn'], 'columns'),
        'timesyncd_state': (['timedatectl', 'show-timesync', '--all'], '='),
    }
    for name, (argv, delimiter) in specs.items():
        data = section(' '.join(argv), 'runtime daemon report; not proof of every configured time provider')
        result[name] = data; out = query(data, argv, deadline)
        if out is None: continue
        if delimiter == 'columns':
            header = False
            for index, line in enumerate(out.splitlines()):
                s = line.strip()
                if (name == 'chrony_sources' and s.startswith('MS Name/IP')) or (name == 'ntp_peers' and s.startswith('remote') and 'refid' in s):
                    header = True; continue
                if not s or set(s) <= {'=', '-'}: continue
                if not header: gap(data, 'unrecognized_output'); continue
                values = s.split()
                if len(values) < (7 if name == 'chrony_sources' else 10):
                    gap(data, 'unrecognized_output'); continue
                item(data, 'source-' + str(index), values, 'runtime', argv[0], limit)
            if not header: gap(data, 'unrecognized_output')
            continue
        fields = ({'Timezone', 'LocalRTC', 'NTP', 'NTPSynchronized', 'TimeUSec', 'RTCTimeUSec'} if name == 'clock_state'
                  else {'Reference ID', 'Stratum', 'Ref time (UTC)', 'System time', 'Last offset', 'RMS offset', 'Frequency', 'Residual freq', 'Skew', 'Root delay', 'Root dispersion', 'Update interval', 'Leap status'} if name == 'chrony_state'
                  else {'ServerName', 'ServerAddress', 'RootDistanceMaxUSec', 'PollIntervalMinUSec', 'PollIntervalMaxUSec', 'PollIntervalUSec', 'Frequency', 'PacketCount', 'NTPMessage'} if name == 'timesyncd_state'
                  else {'associd', 'status', 'leap', 'stratum', 'precision', 'rootdelay', 'rootdisp', 'refid', 'reftime', 'clock', 'peer', 'tc', 'mintc', 'offset', 'frequency', 'sys_jitter', 'clk_jitter', 'clk_wander', 'version', 'processor', 'system'})
        for index, line in enumerate(out.splitlines()):
            if not line.strip(): continue
            if delimiter:
                key, sep, value = line.partition(delimiter)
                if not sep: gap(data, 'unrecognized_output'); continue
                if key.strip() in fields: item(data, key.strip(), value.strip(), 'runtime', argv[0], limit)
                else: gap(data, 'unrecognized_output')
            else:
                for key, value in re.findall(r'([A-Za-z_]+)=("[^"]*"|[^,\n]+)', line):
                    if key in fields: item(data, key, value.strip(), 'runtime', argv[0], limit)
        if not data['items']: gap(data, 'unrecognized_output')
    data = section('time configuration files', 'selected configured sources/options; no keys, defaults or effective merge inferred')
    result['time_configuration'] = data
    scan_files(data, root, ['/etc/chrony.conf', '/etc/chrony/chrony.conf', '/etc/ntp.conf',
        '/etc/systemd/timesyncd.conf', '/etc/systemd/timesyncd.conf.d/*.conf'], ['/etc'],
        settings_parser(TIME_FIELDS), deadline, limit)
    return result


def syslog_parser(text, source, data, limit):
    includes = []
    for number, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith('#'): continue
        if s.startswith('$IncludeConfig '):
            includes.append(s.split(None, 1)[1]); continue
        include = re.fullmatch(r'include\(\s*file="([^"]+)"(?:\s+mode="optional")?\s*\)', s)
        if include: includes.append(include.group(1)); continue
        action = re.fullmatch(r'action\((.*)\)\s*', s)
        if action:
            values = dict(re.findall(r'([A-Za-z][A-Za-z0-9_.]*)="([^"]*)"', action.group(1)))
            safe = {k: v for k, v in values.items() if k in ('type', 'file', 'target', 'port', 'protocol', 'template')}
            if any('://' in v and '@' in v.split('://', 1)[1].split('/', 1)[0] for v in safe.values()):
                safe = {k: v for k, v in safe.items() if not ('://' in v and '@' in v.split('://', 1)[1].split('/', 1)[0])}
                gap(data, 'configuration_fields_omitted')
            if safe: item(data, 'action@' + str(number), safe, 'configured', source, limit)
            gap(data, 'syslog_partial_projection'); continue
        legacy = re.match(r'^([A-Za-z0-9*.,;!=_-]+)\s+(-?/[^\s;]+|@@?[^\s;]+)\s*(?:;[^\s]+)?$', s)
        if legacy:
            destination = legacy.group(2)
            if destination.startswith('@') and ('@' in destination.lstrip('@') or '://' in destination):
                gap(data, 'configuration_fields_omitted'); continue
            item(data, 'route@' + str(number), {'selector': legacy.group(1), 'destination': destination}, 'configured', source, limit)
        elif s.startswith(('$', 'module(', 'input(', 'global(', 'template(')):
            # No arbitrary module inputs, URLs, credentials or template bodies.
            gap(data, 'syslog_partial_projection')
        elif not s.startswith(('{', '}')): gap(data, 'syslog_partial_projection')
    return includes


def application_parser(text, source, data, limit):
    includes = []; group = ''
    for number, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(('#', ';')): continue
        if source.startswith('/etc/nginx/'):
            try: tokens = shlex.split(s, comments=True)
            except ValueError: gap(data, 'unrecognized_configuration'); continue
            if tokens and tokens[0] == 'include' and len(tokens) == 2 and tokens[1].endswith(';'):
                value = tokens[1][:-1]; includes.append(value if value.startswith('/') else '/etc/nginx/' + value)
            elif tokens and tokens[0] in ('access_log', 'error_log'):
                if len(tokens) < 2 or not s.endswith(';') or s.count(';') != 1: gap(data, 'unrecognized_configuration'); continue
                value = tokens[1].rstrip(';')
                if re.search(r'(?:password|token|secret)=|://[^/]*@', value, re.I):
                    gap(data, 'configuration_fields_omitted'); continue
                item(data, tokens[0] + '@' + str(number), value, 'configured', source, limit)
            elif re.search(r'\b(?:access_log|error_log|include)\b', s): gap(data, 'unrecognized_configuration')
        else:
            if s.startswith('['): group = s.strip('[]'); continue
            if s.startswith('!includedir '): includes.append(s.split(None, 1)[1] + '/*.cnf'); continue
            if s.startswith('!include '): includes.append(s.split(None, 1)[1]); continue
            key, sep, value = s.partition('='); key = key.strip().replace('_', '-')
            if group in ('mysqld', 'server', 'mariadb', 'mariadbd') and key in (
                    'log-error', 'slow-query-log', 'slow-query-log-file', 'general-log', 'general-log-file', 'log-output', 'log-timestamps'):
                item(data, key + '@' + str(number), value.split('#', 1)[0].strip() if sep else 'enabled', 'configured', source, limit)
    return includes


def rotation_parser(text, source, data, limit):
    includes = []; script = False
    options = set('rotate daily weekly monthly yearly hourly size maxsize minsize maxage compress nocompress '
                  'delaycompress missingok notifempty ifempty copytruncate create su dateext dateformat sharedscripts '.split())
    for number, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith('#'): continue
        if script:
            if s == 'endscript': script = False
            continue
        try: tokens = shlex.split(s, comments=True)
        except ValueError: gap(data, 'unrecognized_configuration'); continue
        if not tokens: continue
        if tokens[0] in ('prerotate', 'postrotate', 'firstaction', 'lastaction', 'preremove'):
            script = True; continue
        if tokens[0] == 'include' and len(tokens) == 2:
            includes.append(tokens[1]); continue
        if s == '}': continue
        if tokens[0].startswith('/'):
            paths = tokens[:tokens.index('{')] if '{' in tokens else tokens
            if any(not path.startswith('/') for path in paths):
                gap(data, 'rotation_partial_projection'); continue
            if '{' in tokens and tokens.index('{') != len(tokens) - 1: gap(data, 'rotation_partial_projection')
            item(data, 'paths@' + str(number), paths, 'configured', source, limit)
        elif tokens[0] in options:
            item(data, tokens[0] + '@' + str(number), tokens[1:], 'configured', source, limit)
        else: gap(data, 'rotation_partial_projection')
    if script: gap(data, 'unrecognized_configuration')
    return includes


def logging(deadline, limit, root):
    result = {}
    configs = {
        'journald_configuration': (['/etc/systemd/journald.conf', '/run/systemd/journald.conf', '/usr/lib/systemd/journald.conf', '/usr/local/lib/systemd/journald.conf',
            '/etc/systemd/journald.conf.d/*.conf', '/run/systemd/journald.conf.d/*.conf', '/usr/lib/systemd/journald.conf.d/*.conf', '/usr/local/lib/systemd/journald.conf.d/*.conf'],
            ['/etc/systemd', '/run/systemd', '/usr/lib/systemd', '/usr/local/lib/systemd'], settings_parser(JOURNAL_FIELDS)),
        'syslog_configuration': (['/etc/rsyslog.conf', '/etc/rsyslog.d/*.conf'], ['/etc/rsyslog.conf', '/etc/rsyslog.d'], syslog_parser),
        'application_logs': (['/etc/nginx/nginx.conf', '/etc/nginx/conf.d/*.conf', '/etc/nginx/sites-enabled/*', '/etc/my.cnf', '/etc/my.cnf.d/*.cnf', '/etc/mysql/my.cnf'],
            ['/etc/nginx', '/etc/my.cnf', '/etc/my.cnf.d', '/etc/mysql'], application_parser),
        'log_rotation': (['/etc/logrotate.conf', '/etc/logrotate.d/*'], ['/etc/logrotate.conf', '/etc/logrotate.d'], rotation_parser),
    }
    for name, (patterns, allowed, parser) in configs.items():
        data = section(name, 'selected configured directives only; no defaults, inheritance/effective merge or file-content logs')
        result[name] = data; scan_files(data, root, patterns, allowed, parser, deadline, limit)
    data = section('journalctl --disk-usage', 'runtime disk-usage metadata only; no journal messages')
    result['journal_state'] = data; out = query(data, ['journalctl', '--disk-usage', '--no-pager'], deadline)
    if out is not None:
        if re.fullmatch(r'Archived and active journals take up [^\n]+ in the file system\.\s*', out):
            item(data, 'disk_usage', out.strip(), 'runtime', 'journalctl --disk-usage', limit)
        else: gap(data, 'unrecognized_output')
    return result


def snapshot(kind, limit, budget, *, options=None, root=Path('/')):
    started = now(); deadline = time.monotonic() + budget
    if kind not in DATASETS: raise ValueError('unknown_policy_kind')
    if kind == 'ssh-policy': datasets = {'ssh_policy': ssh_policy(deadline, limit, options or {})}
    elif kind == 'sudo-policy': datasets = {'sudo_policy': sudo_policy(deadline, limit)}
    elif kind == 'firewall-policy': datasets = firewall(deadline, limit)
    elif kind == 'time-sync': datasets = timed(deadline, limit, root)
    else: datasets = logging(deadline, limit, root)
    data = {'contract_version': '0.1.0', 'kind': kind, 'platform': 'linux',
            'started_at': started, 'observed_at': now(), 'effective_uid': os.geteuid(), 'datasets': datasets}
    while len(json.dumps(data, ensure_ascii=True).encode()) > MAX_OUTPUT:
        selected = max(datasets.values(), key=lambda d: len(d['items']))
        if not selected['items']: raise ValueError('metadata_size_limit')
        selected['items'].pop(); gap(selected, 'output_size_limit')
    return data


def main():
    if sys.platform != 'linux': print(json.dumps({'platform': sys.platform})); return
    kind, limit, budget = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    options = json.loads(sys.argv[4])
    if kind not in DATASETS or not 1 <= limit <= 5000 or not 0 < budget <= 120:
        raise ValueError('invalid_probe_arguments')
    print(json.dumps(snapshot(kind, limit, budget, options=options), ensure_ascii=True, allow_nan=False))


if __name__ == '__main__': main()
