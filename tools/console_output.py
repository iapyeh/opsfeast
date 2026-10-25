"""Checkout-level terminal presentation; structured data remains unchanged."""
import json
from pathlib import Path
import shutil
import sys
from display_time import human_times


class ConsoleDependencyError(RuntimeError):
    """Display prerequisites are missing; no operation should have started."""


def human_output(json_output=False):
    return not json_output and bool(sys.stdout.isatty())


def table_formatter():
    try:
        import tabulate
        if not tabulate.WIDE_CHARS_MODE:
            raise ImportError('wide character support unavailable')
    except ImportError:
        raise ConsoleDependencyError('terminal tables require tabulate[widechars]==0.10.0; '
                                     'install requirements-init.txt with the selected interpreter') from None
    return tabulate.tabulate


def prepare(json_output=False):
    """Check terminal dependencies before any authorized operation starts."""
    if human_output(json_output):
        table_formatter()


def cell(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)[1:-1]
    return json.dumps(value, ensure_ascii=False, default=str)


def render_table(headers, rows):
    """Render already escaped display strings; constrain tables only on terminal stdout."""
    formatter = table_formatter()
    options = dict(tablefmt='rounded_outline', disable_numparse=True, preserve_whitespace=True)
    if not sys.stdout.isatty():
        return formatter(rows, headers=headers, **options)

    from wcwidth import wcswidth
    columns = max(2, shutil.get_terminal_size().columns)
    count = max(len(headers), max((len(row) for row in rows), default=0))
    if not count:
        return formatter(rows, headers=headers, **options)
    labels = [*headers, *([''] * (count - len(headers)))]
    cells = [list(row) + [''] * (count - len(row)) for row in rows]
    # tabulate reserves two additional cells inside each header's content width.
    widths = [max([wcswidth(labels[index]) + 2, *(wcswidth(row[index]) for row in cells)])
              for index in range(count)]
    # Rounded-outline borders and padding use three cells per column plus one.
    budget = columns - (3 * count + 1)
    if sum(widths) <= budget:
        return formatter(rows, headers=headers, **options)
    if sum(min(width, 8) for width in widths) > budget:
        # More columns than can be read use labeled records, retaining every cell.
        records = []
        for index, row in enumerate(cells, 1):
            if records:
                records.append([''])
            records.append([f'Record {index}'])
            records.extend([[f'{label}: {value}'] for label, value in zip(labels, row)])
        if not cells:
            records = [[label] for label in labels]
        return formatter(records, tablefmt='plain', disable_numparse=True, preserve_whitespace=True,
                         maxcolwidths=[columns])

    # Cap wide columns fairly, leaving naturally short columns unchanged.
    low, high = 1, max(widths)
    while low < high:
        cap = (low + high + 1) // 2
        if sum(min(width, cap) for width in widths) <= budget:
            low = cap
        else:
            high = cap - 1
    limits = [min(width, low) for width in widths]
    remaining = budget - sum(limits)
    for index, width in enumerate(widths):
        if remaining and limits[index] < width:
            limits[index] += 1
            remaining -= 1
    return formatter(cells, headers=labels, maxcolwidths=limits, maxheadercolwidths=[max(2, limit - 2) for limit in limits], **options)


def table(headers, rows):
    return render_table([cell(header) for header in headers],
                        [[cell(human_times(v)) for v in row] for row in rows])


def fields(value, prefix=''):
    if isinstance(value, dict) and value:
        return [row for key, item in value.items() for row in fields(item, f'{prefix}.{key}' if prefix else str(key))]
    return [[prefix or 'value', value]]


def details(value):
    return table(['field', 'value'], fields(value))


def vertical(value):
    """One escaped field/value per line, without terminal-width dependencies."""
    return '\n'.join(f'{cell(key)}: {cell(item)}' for key, item in fields(human_times(value)))


def inspection(report):
    rows = []
    for recipe in report['recipes']:
        meta = recipe.get('descriptor') or {}
        coverage = meta.get('platforms') or {}
        rows.append([meta.get('id', recipe['directory']), meta.get('version'), meta.get('title'),
                     recipe['status'], coverage.get('implemented'), coverage.get('tested'), coverage.get('planned')])
    result = table(['recipe', 'version', 'purpose', 'status', 'implemented', 'declared tested', 'planned'], rows)
    for recipe in report['recipes']:
        if recipe.get('coverage') or recipe.get('errors'):
            result += '\n' + details({'recipe': (recipe.get('descriptor') or {}).get('id', recipe['directory']),
                                       'coverage': recipe.get('coverage'), 'errors': recipe.get('errors'),
                                       'implementations': recipe.get('implementations')})
    return result + '\nStatic inspection only; declared coverage does not verify host applicability.'


class DisplayIcons(dict):
    """Presentation metadata for a loaded Feast; dict entries remain host icons."""
    def __init__(self, config):
        super().__init__((host, item['icon']) for host, item in config.hosts.items())
        self.default_host = config.default_host_icon
        self.default_user = config.default_user_icon
        self.host_users = dict(config.host_user_icons)
        self.named_users = dict(config.user_icon_defaults)
        self.users = {host: {user: account['icon'] for user, account in item.get('users', {}).items()}
                      for host, item in config.hosts.items()}


def user_label(user, host=None, icons=None):
    from opsfeast import DEFAULT_USER_ICON
    default = getattr(icons, 'host_users', {}).get(host, getattr(icons, 'default_user', DEFAULT_USER_ICON))
    default = getattr(icons, 'named_users', {}).get(user, default)
    icon = getattr(icons, 'users', {}).get(host, {}).get(user, default)
    return f'{icon} {user}'


def host_label(host, icons=None):
    from opsfeast import DEFAULT_HOST_ICON
    return f"{(icons or {}).get(host, getattr(icons, 'default_host', DEFAULT_HOST_ICON))} {host}"


def configuration_summary(config):
    """Human-only check overview; derive labels without resolving SSH aliases."""
    from opsfeast import group_names
    from management_view import user_accounts
    icons = DisplayIcons(config)
    sections = [(group, config.groups[group]['hosts']) for group in sorted(config.groups)]
    ungrouped = [host for host, settings in config.hosts.items() if not settings.get('group', [])]
    if ungrouped:
        sections.append((None, ungrouped))
    rows, disabled, multiple = [], False, False
    for group, hosts in sections:
        definition = config.groups.get(group, {})
        label = definition.get('label', group)
        title = ('Ungrouped (no group)' if group is None else
                 f'{label} ({group})' if label != group else group)
        if definition.get('description'):
            title += ' — ' + definition['description']
        if not hosts:
            rows.append([title, '(no hosts)', '-'])
        for index, host in enumerate(hosts):
            settings = config.hosts[host]
            memberships = list(dict.fromkeys(group_names(settings.get('group', []), 'host group')))
            name = host_label(host, icons)
            if len(memberships) > 1:
                multiple = True
                if memberships[0] == group:
                    name += ' (primary)'
            if not settings.get('enabled', True):
                name += ' [disabled]'
                disabled = True
            login, users = user_accounts(settings)
            if login is not None:
                users = [login, *(user for user in users if user != login)]
            accounts = [user_label(user, host, icons) for user in users]
            if login is None:
                accounts.insert(0, 'login unresolved')
            rows.append([title if index == 0 else '', name, ', '.join(accounts) or '-'])
    output = table(['group', 'host', 'users'], rows)
    if multiple:
        output += '\n(primary) = first group membership; hosts may appear in multiple groups. Host total counts unique IDs.'
    if disabled:
        output += '\n[disabled] = host disabled in configuration.'
    return output


def display_icons(root):
    """Historical read views can still render when current config is absent/invalid."""
    from opsfeast import Validator, ConfigError
    try:
        config = Validator(root)
        config.load(config.root / 'hosts.yaml')
        return DisplayIcons(config)
    except (ConfigError, OSError, RecursionError):
        return {}


def status(item):
    state = item.get('status')
    if state is None and isinstance(item.get('success'), bool):
        state = 'success' if item['success'] else 'failed'
    return {'success': 'PASS', 'failed': '❌ FAIL', 'skipped': 'SKIP',
            'partial': 'PARTIAL', 'unsupported': 'UNSUPPORTED'}.get(state, state or 'UNKNOWN')


def diagnostic_rows(report, test='', user=None):
    """Read diagnostic evidence only; never infer success from missing fields."""
    rows = []
    nested_login = (report.get('tests') or {}).get('test-sudo', {})
    user = ((report.get('connection_identity') or {}).get('username') or report.get('connection_user') or
            (nested_login.get('connection_identity') or {}).get('username') or nested_login.get('connection_user') or user or 'unresolved')
    if isinstance(report.get('tests'), dict):
        for name, item in report['tests'].items():
            rows.extend(diagnostic_rows(item, name.removeprefix('test-'), user))
    elif isinstance(report.get('groups'), list):
        for group in report['groups']:
            for index, step in enumerate(group.get('steps', [])):
                operation = step.get('operation', test)
                actor = (group.get('accounts', [])[index] if index < len(group.get('accounts', [])) else
                         step.get('from_user', user)) if operation == 'sudo' else step.get('to_user', user)
                prerequisite = step.get('su_identity_verification')
                if operation == 'sudo' and actor != user:
                    if prerequisite:
                        su_status = status(prerequisite)
                        reason = '' if prerequisite.get('status') == 'success' else step.get('stage', 'su_identity') + '_failed'
                    else:
                        su_status = '❌ FAIL' if step.get('stage', '').startswith('su_') else 'SKIP'
                        reason = step.get('stage', '') + '_failed' if su_status == '❌ FAIL' else step.get('reason_code', 'su_unverified')
                    rows.append([su_status, 'su', actor, reason])
                    if not prerequisite or prerequisite.get('status') != 'success':
                        rows.append(['SKIP', 'sudo', actor, 'su_failed'])
                        continue
                rows.append([status(step), operation, actor,
                             step.get('reason_code') or (step['stage'] + '_failed' if step.get('stage') and step.get('status') == 'failed' else '')
                             or (step.get('error') or {}).get('reason', '')])
            parent = group.get('parent_identity_verification', {})
            if parent.get('status') != 'success':
                rows.append(['❌ FAIL' if group.get('status') == 'failed' else 'UNKNOWN', 'restoration', user,
                             parent.get('message', 'restoration_unverified')])
            if group.get('cleanup_error'):
                rows.append(['❌ FAIL', 'cleanup', user, 'cleanup_failed'])
        if not report['groups']:
            rows.append([status(report), test, user, (report.get('error') or {}).get('reason', 'not_run')])
    elif isinstance(report.get('commands'), list):
        rows.append(['PASS' if report.get('connected') else '❌ FAIL', 'connection', user,
                     '' if report.get('connected') else 'connection_failed'])
        for command in report['commands']:
            passed = command.get('exitcode') == 0 and not command.get('error')
            rows.append(['PASS' if passed else '❌ FAIL', command.get('command', 'command'), user,
                         '' if passed else 'command_failed'])
        if report.get('host_init'):
            rows.extend(diagnostic_rows(report['host_init'], 'host-init', user))
    else:
        rows.append([status(report), test or report.get('test', 'diagnostic'), user, report.get('reason_code', '')])
    if report.get('cleanup_error'):
        rows.append(['❌ FAIL', 'cleanup', user, 'cleanup_failed'])
    return rows


def diagnostic(report, test='', icons=None, user=None):
    host = report.get('host', report.get('host_id', 'unresolved'))
    result = table(['status', 'host', 'test', 'user', 'reason'],
                   [[state, host_label(host, icons), name, user_label(actor, host, icons), reason]
                    for state, name, actor, reason in diagnostic_rows(report, test, user)])
    facts_report = report if report.get('facts') else (report.get('tests') or {}).get('host-init', {})
    if facts_report.get('facts'):
        result += '\n' + details({'facts': facts_report['facts'], 'selection_source': facts_report.get('selection_source'),
                                  'observed_at': facts_report.get('observed_at')})
    connection = report if report.get('commands') else (report.get('tests') or {}).get('test-connection', {})
    if connection.get('commands'):
        result += '\n' + table(['command', 'stdout', 'stderr', 'exitcode', 'error'], [
            [row.get('command'), row.get('stdout'), row.get('stderr'), row.get('exitcode'), row.get('error')]
            for row in connection['commands']])
    return result


def execution_identities(row):
    """Project recorded identities by role; never read configured credentials/users."""
    def name(value):
        return (isinstance(value, str) and bool(value.strip()) and len(value) <= 256
                and all(ord(c) >= 32 and ord(c) != 127 for c in value))
    if isinstance(row.get('identity_evidence'), list):
        # Only the read-only batch projection supplies this precomputed evidence.
        return row['identity_evidence']
    identities = []
    actor = (row.get('access') or {}).get('actual_identity') or {}
    username, uid = actor.get('username'), actor.get('effective_uid')
    if name(username) and type(uid) is int and uid >= 0:
        identities.append({'role': 'os', 'username': username, 'effective_uid': uid})
    if (row.get('recipe') or {}).get('id') == 'mysql-replication':
        instances = (row.get('data') or {}).get('instances')
        if isinstance(instances, list):
            for instance in instances:
                if not isinstance(instance, dict) or not name(instance.get('instance')):
                    continue
                server = instance.get('server') or {}
                username = server.get('authenticated_user') if isinstance(server, dict) else None
                identities.append({'role': 'database', 'instance': instance['instance'],
                                   'username': username if name(username) else None,
                                   'source': 'CURRENT_USER()' if name(username) else None})
    login = row.get('login_identity') or {}
    if (row.get('connected') is True and isinstance(login, dict)
            and login.get('source') == 'ssh_connection' and name(login.get('username'))):
        identities.append({'role': 'ssh', 'username': login['username'], 'source': 'ssh_connection'})
    return identities


def execution_identity(row):
    identities = execution_identities(row)
    os_actors = [i for i in identities if i.get('role') == 'os']
    databases = [i for i in identities if i.get('role') == 'database']
    logins = [i for i in identities if i.get('role') == 'ssh']
    labels = []
    if any(i.get('username') for i in databases):
        labels.extend(f"DB{' ' + i['instance'] if len(databases) > 1 else ''}: {i.get('username') or 'unknown'}" for i in databases)
    if os_actors:
        labels.extend(f"{i['username']} (uid={i['effective_uid']})" for i in os_actors)
    elif logins:
        labels.extend(f"SSH: {i['username']}" for i in logins)
    return '; '.join(labels) or 'unknown'


def replication_health(row):
    """Project saved replica findings, never configuration or fresh queries."""
    labels = {'HEALTHY', 'UNHEALTHY', 'UNKNOWN', 'NOT CONFIGURED', 'ERROR'}
    if row.get('replication_health') in labels:
        return row['replication_health']
    if (row.get('recipe') or {}).get('id') != 'mysql-replication':
        return None
    if row.get('status') in ('skipped', 'unsupported'):
        return None
    if row.get('status') == 'failed':
        return 'ERROR'
    instances = (row.get('data') or {}).get('instances')
    if not isinstance(instances, list) or not instances:
        return 'UNKNOWN'
    errors = {'query_failed', 'probe_failed', 'timeout', 'client_unavailable',
              'unsupported_server_version'}
    if any(i.get('reason') in errors for i in instances):
        return 'ERROR'
    states = [i.get('health') for i in instances]
    if 'unhealthy' in states:
        return 'UNHEALTHY'
    if any(i.get('cleanup') != 'confirmed' for i in instances):
        return 'UNKNOWN'
    if all(s == 'not_configured' for s in states):
        return 'NOT CONFIGURED'
    if row.get('status') == 'success' and all(s == 'healthy' for s in states):
        return 'HEALTHY'
    return 'UNKNOWN'


def execution_result(row):
    """Shared completion/history outcome; keep collection and receipt failures distinct."""
    access = row.get('access') or {}
    state = row.get('status', 'unknown')
    outcome = replication_health(row) or status(row)
    if state != 'success':
        reason = row.get('reason_code') or row.get('error')
        if reason:
            outcome += f' ({reason})'
    if (row.get('content_update') or {}).get('status') == 'failed':
        outcome = f'❌ FAIL (content_update_failed; collection={outcome})'
        state = 'failed'
    if (row.get('retention') or {}).get('status') == 'failed':
        outcome = f'❌ FAIL (retention_failed; collection={outcome})'
        state = 'failed'
    elif access.get('degraded'):
        outcome = ('PARTIAL' if state == 'success' else outcome) + ' (fallback_user)'
        if state == 'success':
            state = 'partial'
    return {'status': state, 'text': outcome}


def execution_locations(report, result_root=None, host=None):
    """Human completion destinations. JSON and execution/storage receipts stay unchanged."""
    hosts = report.get('hosts', [report])
    if not hosts:
        return ''
    lines = []
    saved = [Path(row['result_path']) for row in hosts if row.get('result_path') and Path(row['result_path']).is_file()]
    if len(hosts) == 1:
        missing = 'saved file unavailable' if hosts[0].get('result_path') else 'not saved'
        lines.append('Raw JSON: ' + (cell(str(saved[0].resolve())) if saved else missing))
    elif saved:
        lines.extend('Raw results directory: ' + cell(str(path)) for path in sorted({p.resolve().parent for p in saved}))
    elif any(row.get('result_path') for row in hosts):
        lines.append('Raw JSON: saved files unavailable')
    else:
        lines.append('Raw JSON: no result files saved')
    receipts = [row.get('content_update') or {} for row in hosts]
    successful_vault = any(any(
        consumer.get('status') == 'success' and consumer.get('consumer') == 'vault'
        and consumer.get('source') == 'builtin:vault' for consumer in receipt.get('consumers', [])) for receipt in receipts)
    if successful_vault and result_root is not None:
        try:
            from host_vault import result_locations
            row = hosts[0]
            target = row.get('host', row.get('host_id', host)) if len(hosts) == 1 else None
            locations = result_locations(result_root, host=target,
                                         record_id=(row.get('retention') or {}).get('record_id') if len(hosts) == 1 else None)
            if locations.get('current'):
                lines.append('Vault current (latest state): ' + cell(locations['current']))
            elif locations.get('host'):
                lines.append('Vault host results: ' + cell(locations['host']))
            elif locations.get('index'):
                lines.append('Vault index: ' + cell(locations['index']))
            else:
                lines.append('Vault: publication succeeded; entrypoint unavailable')
        except Exception as exc:
            # Result lookup must not replace a valid execution outcome or disclose config errors.
            lines.append('Vault: publication succeeded; entrypoint unavailable (' + type(exc).__name__ + ')')
    elif successful_vault:
        lines.append('Vault: publication succeeded; result root unavailable')
    elif any(receipt.get('status') == 'failed' for receipt in receipts):
        lines.append('Vault: not confirmed for this run (content update failed)')
    elif receipts:
        lines.append('Vault: no successful publication recorded for this run')
    return '\n'.join(lines)


def execution(report, icons=None, host=None, recipe=None, result_root=None):
    if report.get('collection_started') is False:
        from access_check import format_summary
        return format_summary(report, icons)
    hosts = report.get('hosts', [report])
    identifiers={}
    if result_root is not None:
        from recipe_reports import result_short_ids
        identifiers=result_short_ids(result_root)
    rows = []
    for row in hosts:
        target = row.get('host', row.get('host_id', host))
        actor_text = execution_identity(row)
        outcome = execution_result(row)['text']
        saved=row.get('result_path')
        identifier=identifiers.get(str(Path(saved).resolve()),'-') if saved and identifiers else '-'
        rows.append([host_label(target, icons) if target else '-', actor_text, outcome, identifier])
    rows.extend([host_label(item['host'], icons), '-', f"SKIP ({item['reason_code']})", '-']
                for item in report.get('excluded_hosts', []))
    rendered=table(['host', 'collection identity', 'result', 'result id'], rows)
    if report.get('observation_run_id'):
        rendered += '\nObservation ID: '+cell(report['observation_run_id'])
    destinations = execution_locations(report, result_root, host)
    if destinations:
        rendered += '\n\n' + destinations
    return rendered


def print_report(value, *, json_output=False, kind='details', icons=None, test='', user=None, host=None, recipe=None,
                 indent=2, ensure_ascii=False, allow_nan=True, result_root=None):
    if human_output(json_output):
        rendered = diagnostic(value, test, icons, user) if kind == 'diagnostic' else (
            execution(value, icons, host, recipe, result_root) if kind == 'execution' else details(value))
        print(rendered)
    else:
        print(json.dumps(value, indent=indent, ensure_ascii=ensure_ascii, allow_nan=allow_nan))
