"""Remote stdlib helper. Receives secret JSON on stdin; emits only allowlisted evidence."""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

IDENTITY_SQL = 'SELECT @@version AS version, @@version_comment AS version_comment, @@hostname AS hostname, @@server_id AS server_id, CURRENT_USER() AS authenticated_user;'


def xml_rows(output):
    if len(output) > 2 * 1024 * 1024 or '<!DOCTYPE' in output.upper() or '<!ENTITY' in output.upper():
        raise ValueError('invalid client output')
    output = re.sub(r'<\?xml[^>]*\?>', '', output)
    root = ET.fromstring('<results>' + output + '</results>')
    if any(element.tag != 'resultset' for element in root):
        raise ValueError('unexpected client XML')
    rows = []
    for row in root.findall('./resultset/row'):
        fields = {}
        for field in row.findall('field'):
            name = field.attrib['name']
            if name in fields:
                raise ValueError('duplicate client field')
            fields[name] = None if field.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true' else (field.text or '')
        rows.append(fields)
    return rows


def option_text(value):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise ValueError('invalid credential option')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def number(value):
    if value is None or value == '' or value == 'NULL':
        return None
    if not re.fullmatch(r'\d+', str(value)):
        raise ValueError('invalid numeric status')
    return int(value)


def channel(row, options, delay):
    def field(new, old=None):
        return row.get(new, row.get(old)) if old else row.get(new)
    name = field('Channel_Name', 'Connection_name') or ''
    source = field('Source_Host', 'Master_Host')
    io = field('Replica_IO_Running', 'Slave_IO_Running')
    sql = field('Replica_SQL_Running', 'Slave_SQL_Running')
    lag = number(field('Seconds_Behind_Source', 'Seconds_Behind_Master'))
    io_error, sql_error = number(row.get('Last_IO_Errno')), number(row.get('Last_SQL_Errno'))
    expected = options.get('expected_sources', {}).get(name, options.get('expected_source'))
    reasons = []
    if io not in ('Yes', None) or sql not in ('Yes', None): reasons.append('thread_not_running')
    if io_error or sql_error or row.get('Last_IO_Error') or row.get('Last_SQL_Error'): reasons.append('replication_error')
    if expected and source != expected: reasons.append('unexpected_source')
    if lag is not None and lag > delay: reasons.append('delay_exceeded')
    unknown = not source or any(v is None for v in (io, sql, lag, io_error, sql_error))
    health = 'unhealthy' if reasons else 'unknown' if unknown else 'healthy'
    if unknown: reasons.append('incomplete_status')
    return {'channel': name, 'source_host': source, 'source_port': number(field('Source_Port', 'Master_Port')),
            'expected_source': expected or None, 'io_running': io, 'sql_running': sql,
            'delay_seconds': lag, 'configured_delay_seconds': number(row.get('SQL_Delay')),
            'last_io_errno': io_error, 'last_sql_errno': sql_error,
            'error_text': 'redacted' if row.get('Last_IO_Error') or row.get('Last_SQL_Error') else None,
            'source_log_file': field('Source_Log_File', 'Master_Log_File'),
            'read_source_log_pos': number(field('Read_Source_Log_Pos', 'Read_Master_Log_Pos')),
            'executed_source_log_file': field('Relay_Source_Log_File', 'Relay_Master_Log_File'),
            'exec_source_log_pos': number(field('Exec_Source_Log_Pos', 'Exec_Master_Log_Pos')),
            'retrieved_gtid_set': row.get('Retrieved_Gtid_Set'), 'executed_gtid_set': row.get('Executed_Gtid_Set'),
            'mariadb_gtid_io_pos': row.get('Gtid_IO_Pos'), 'mariadb_using_gtid': row.get('Using_Gtid'),
            'replicate_do_db': row.get('Replicate_Do_DB'), 'replicate_ignore_db': row.get('Replicate_Ignore_DB'),
            'replicate_do_table': row.get('Replicate_Do_Table'), 'replicate_ignore_table': row.get('Replicate_Ignore_Table'),
            'replicate_wild_do_table': row.get('Replicate_Wild_Do_Table'),
            'replicate_wild_ignore_table': row.get('Replicate_Wild_Ignore_Table'),
            'health': health, 'reasons': reasons}


def collect(payload):
    options, budget, delay = payload['options'], payload['budget'], payload['delay']
    result = {'health': 'unknown', 'reason': 'query_failed', 'server': None, 'channels': [], 'probes': [], 'cleanup': 'confirmed'}
    temporary = None
    deadline = time.monotonic() + budget
    try:
        client = options.get('client', 'auto')
        if client == 'auto': client = shutil.which('mysql') or shutil.which('mariadb')
        else: client = shutil.which(client)
        if not client:
            result['reason'] = 'client_unavailable'
            return result
        option_file = options.get('option_file')
        if option_file:
            info = os.lstat(option_file)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
                raise ValueError('unsafe option file')
        else:
            fd, temporary = tempfile.mkstemp(prefix='opsfeast-mysql-', suffix='.cnf')
            with os.fdopen(fd, 'w') as handle:
                handle.write('[client]\nuser=' + option_text(options['user']) + '\npassword=' + option_text(options['password']) + '\n')
            option_file = temporary
        argv = [client, '--defaults-file=' + option_file, '--batch', '--xml', '--skip-auto-rehash',
                '--connect-timeout=' + str(max(1, min(30, int(budget))))]
        if options.get('transport', 'socket') == 'socket':
            argv += ['--protocol=SOCKET']
            if options.get('socket'): argv += ['--socket=' + options['socket']]
        else:
            argv += ['--protocol=TCP', '--host=' + options['host'], '--port=' + str(options.get('port', 3306))]
        safe_argv = [arg if not arg.startswith('--defaults-file=') else '--defaults-file=<protected option file>' for arg in argv]

        def query(sql, extra=()):
            input_description = 'fixed SQL on stdin; credentials in protected option file; expectations=' + json.dumps({
                'expected_source': options.get('expected_source'),
                'expected_sources': options.get('expected_sources', {}), 'max_delay_seconds': delay}, sort_keys=True)
            evidence = {'operation': safe_argv + list(extra), 'input': input_description,
                        'sql': sql, 'exitcode': None, 'stdout': None, 'error': None}
            result['probes'].append(evidence)
            try:
                completed = subprocess.run(argv + list(extra), input=sql + '\n', text=True,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           timeout=max(.01, deadline-time.monotonic()), check=False)
                evidence['exitcode'] = completed.returncode
                if completed.returncode:
                    # Never copy arbitrary stderr: it can contain SQL, data, option files or secrets.
                    error = re.search(r'ERROR\s+(\d+)', completed.stderr)
                    evidence['error'] = 'mysql_error_' + error[1] if error else 'client_failed'
                    raise RuntimeError('client failed')
                return xml_rows(completed.stdout), evidence
            except subprocess.TimeoutExpired:
                evidence['error'] = 'timeout'
                raise

        # Identify the product without guessing from the executable's filename.
        # A TLS-enabled probe requires product-specific verification flags from the start.
        tls = options.get('tls')
        if tls:
            # Use --version (no database connection) to select the client syntax only.
            version_evidence = {'operation': [client, '--no-defaults', '--version'], 'input': 'none',
                                'sql': None, 'exitcode': None, 'stdout': None, 'error': None}
            result['probes'].append(version_evidence)
            version = subprocess.run([client, '--no-defaults', '--version'], capture_output=True, text=True,
                                     timeout=max(.01, deadline-time.monotonic()), check=False)
            version_evidence.update(exitcode=version.returncode, stdout=version.stdout[:4096])
            if version.returncode: raise ValueError('client version unavailable')
            argv += ['--ssl-ca=' + tls['ca']]
            argv += ['--ssl', '--ssl-verify-server-cert'] if 'mariadb' in version.stdout.lower() else ['--ssl-mode=VERIFY_IDENTITY']
            safe_argv = [arg if not arg.startswith('--defaults-file=') else '--defaults-file=<protected option file>' for arg in argv]
        rows, evidence = query(IDENTITY_SQL)
        if len(rows) != 1 or set(rows[0]) != {'version', 'version_comment', 'hostname', 'server_id', 'authenticated_user'}:
            raise ValueError('invalid server identity')
        server = rows[0]
        product = 'mariadb' if 'mariadb' in (server['version'] + server['version_comment']).lower() else 'mysql'
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', server['version'])
        if not match: raise ValueError('invalid server version')
        release = tuple(map(int, match.groups()))
        server['product'] = product
        evidence['stdout'] = dict(server)
        result['server'] = server
        if (product == 'mysql' and release < (5, 7, 0)) or (product == 'mariadb' and release < (10, 2, 0)):
            result['reason'] = 'unsupported_server_version'
            return result
        sql = 'SHOW ALL SLAVES STATUS;' if product == 'mariadb' else 'SHOW REPLICA STATUS;' if release >= (8, 0, 22) else 'SHOW SLAVE STATUS;'
        rows, evidence = query(sql)
        channels = [channel(row, options, delay) for row in rows]
        if len({c['channel'] for c in channels}) != len(channels): raise ValueError('duplicate channel')
        evidence['stdout'] = channels
        result['channels'] = channels
        missing = set(options.get('expected_sources', {})) - {c['channel'] for c in channels}
        if missing:
            result.update(health='unhealthy', reason='expected_channel_missing')
        elif not channels:
            result.update(health='not_configured', reason='no_replication_channels')
        elif any(c['health'] == 'unhealthy' for c in channels):
            result.update(health='unhealthy', reason='channel_unhealthy')
        elif any(c['health'] == 'unknown' for c in channels):
            result.update(health='unknown', reason='channel_unknown')
        else:
            result.update(health='healthy', reason='replica_side_healthy')
    except Exception as exc:
        result.update(health='unknown', reason='timeout' if isinstance(exc, subprocess.TimeoutExpired) else 'query_failed')
        if result['probes'] and not result['probes'][-1]['error']:
            result['probes'][-1]['error'] = type(exc).__name__
    finally:
        if temporary:
            try: os.unlink(temporary)
            except OSError:
                result.update(health='unknown', reason='credential_cleanup_failed', cleanup='unknown')
    return result


def main():
    payload = json.load(sys.stdin)
    result = collect(payload)
    # Scrub even allowlisted text if it happens to contain the supplied password.
    secret = payload['options'].get('password')
    content = json.dumps(result, ensure_ascii=True, allow_nan=False)
    if secret: content = content.replace(json.dumps(secret)[1:-1], '[REDACTED]')
    print(content)


if __name__ == '__main__':
    main()
