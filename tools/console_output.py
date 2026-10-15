"""Checkout-level terminal presentation; structured data remains unchanged."""
import json
import sys


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


def table(headers, rows):
    return table_formatter()([[cell(v) for v in row] for row in rows], headers=headers,
                             tablefmt='rounded_outline', disable_numparse=True, preserve_whitespace=True)


def fields(value, prefix=''):
    if isinstance(value, dict) and value:
        return [row for key, item in value.items() for row in fields(item, f'{prefix}.{key}' if prefix else str(key))]
    return [[prefix or 'value', value]]


def details(value):
    return table(['field', 'value'], fields(value))


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


def execution(report, icons=None, host=None, recipe=None):
    if report.get('collection_started') is False:
        from access_check import format_summary
        return format_summary(report, icons)
    hosts = report.get('hosts', [report])
    result = table(['status', 'host', 'recipe', 'reason', 'retention', 'identity', 'result_path'], [
        [status(row), host_label(row.get('host', row.get('host_id', host)), icons) if row.get('host', row.get('host_id', host)) else '-', row.get('recipe_id', recipe or ''),
         row.get('reason_code', row.get('error', '')), status(row['retention']) if row.get('retention') else 'not_reported',
         row.get('identity_quality', 'not_reported'), row.get('result_path', '')] for row in hosts])
    for row in hosts:
        extra = {key: row[key] for key in ('message', 'data', 'artifacts', 'access') if key in row and row[key] is not None}
        if extra:
            result += '\n' + details(extra)
    if report.get('excluded_hosts'):
        result += '\n' + table(['excluded host', 'reason'], [
            [host_label(item['host'], icons), item['reason_code']] for item in report['excluded_hosts']])
    if report.get('counts'):
        result += '\n' + details({'counts': report['counts']})
    return result


def print_report(value, *, json_output=False, kind='details', icons=None, test='', user=None, host=None, recipe=None,
                 indent=2, ensure_ascii=False, allow_nan=True):
    if human_output(json_output):
        rendered = diagnostic(value, test, icons, user) if kind == 'diagnostic' else (
            execution(value, icons, host, recipe) if kind == 'execution' else details(value))
        print(rendered)
    else:
        print(json.dumps(value, indent=indent, ensure_ascii=ensure_ascii, allow_nan=allow_nan))
