"""Versioned presentation/delivery interfaces; platform owns all object mutation."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import format_datetime
import os
import math
import threading
from datetime import datetime, timedelta, timezone

from opsfeast import ConfigError
from opsfeast.services import ServiceError, VERSION, canonical, configuration, now

_DISPATCH = threading.local()


def validate_adapter(name, adapter, kind):
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,62}', name):
        raise ServiceError('invalid_adapter_name')
    if (not isinstance(adapter, dict) or set(adapter) - {'source', 'enabled', 'config', 'sha256', 'retry', 'destination'}
            or not {'source', 'enabled'} <= set(adapter) or type(adapter['enabled']) is not bool
            or not isinstance(adapter.get('config', {}), dict)):
        raise ServiceError('invalid_adapter_configuration')
    if adapter.get('destination', 'vault') not in ('vault', 'files') or kind == 'deliveries' and 'destination' in adapter:
        raise ServiceError('invalid_adapter_destination')
    retry = adapter.get('retry', {})
    if (not isinstance(retry, dict) or set(retry) - {'max_attempts', 'delay_seconds'}
            or type(retry.get('max_attempts', 5)) is not int or not 1 <= retry.get('max_attempts', 5) <= 100
            or type(retry.get('delay_seconds', 60)) is not int or not 0 <= retry.get('delay_seconds', 60) <= 86400):
        raise ServiceError('invalid_adapter_retry_policy')
    source = adapter['source']
    builtin = 'builtin:vault' if kind == 'presentations' else 'builtin:smtp'
    if source == builtin:
        if source == 'builtin:vault' and adapter.get('destination', 'vault') != 'vault':
            raise ServiceError('builtin_vault_destination_required')
        if 'sha256' in adapter:
            raise ServiceError('builtin_adapter_digest_not_configurable')
        if kind == 'presentations' and adapter.get('config'):
            raise ServiceError('invalid_vault_adapter_configuration')
        if kind == 'deliveries':
            validate_smtp(adapter.get('config', {}), required=adapter['enabled'])
    elif not isinstance(source, str) or not source.startswith('local:service-adapters/'):
        raise ServiceError('unsupported_adapter_source')
    elif not isinstance(adapter.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', adapter['sha256']):
        raise ServiceError('local_adapter_requires_reviewed_sha256')


def local_source(root, adapter):
    from retention_consumers import safe_path
    relative = adapter['source'].removeprefix('local:')
    path = safe_path(root, relative)
    if path.suffix != '.py' or not path.is_file():
        raise ServiceError('adapter_module_missing')
    code = path.read_bytes()
    if hashlib.sha256(code).hexdigest() != adapter['sha256']:
        raise ServiceError('adapter_source_changed')
    return path, code


def inspect_adapters(root, config):
    items = []
    for kind in ('presentations', 'deliveries'):
        for name, adapter in config[kind].items():
            item = {'id': name, 'kind': kind, 'source': adapter['source'], 'enabled': adapter['enabled'],
                    'status': 'available', 'contract_version': VERSION}
            try:
                if adapter['source'].startswith('local:'):
                    local_source(root, adapter)
                elif kind == 'deliveries':
                    validate_smtp(adapter.get('config', {}), required=True)
            except (OSError, ValueError) as exc:
                item.update(status='unavailable', reason_code=getattr(exc, 'code', 'adapter_unavailable'))
            items.append(item)
    return items


def module(root, adapter):
    path, code = local_source(root, adapter)
    # Compile exactly the reviewed entrypoint; candidate discovery never imports.
    namespace = {'__file__': str(path), '__name__': '_opsfeast_service_adapter'}
    exec(compile(code, str(path), 'exec'), namespace)
    if namespace.get('API_VERSION') != VERSION:
        raise ServiceError('unsupported_adapter_interface')
    return namespace


def validate_smtp(config, *, required=True):
    allowed = {'host', 'port', 'security', 'sender', 'recipients', 'username', 'password_env', 'timeout'}
    if set(config) - allowed:
        raise ServiceError('invalid_smtp_configuration')
    if not required and not config:
        return
    if (not isinstance(config.get('host'), str) or not config['host']
            or any(c in config['host'] for c in '\r\n\x00')
            or type(config.get('port', 587)) is not int or not 1 <= config.get('port', 587) <= 65535
            or config.get('security', 'starttls') not in ('starttls', 'tls', 'plain')
            or type(config.get('timeout', 15)) not in (int, float) or not math.isfinite(config.get('timeout', 15)) or not 0 < config.get('timeout', 15) <= 120):
        raise ServiceError('invalid_smtp_configuration')
    addresses = [config.get('sender'), *config.get('recipients', [])] if isinstance(config.get('recipients'), list) else []
    if len(addresses) < 2 or any(not isinstance(a, str) or not a or '@' not in a or any(c in a for c in '\r\n\x00') for a in addresses):
        raise ServiceError('invalid_mail_addresses')
    if 'username' in config:
        if (not isinstance(config['username'], str) or not config['username']
                or not isinstance(config.get('password_env'), str)
                or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', config['password_env'])
                or config.get('security', 'starttls') == 'plain'):
            raise ServiceError('smtp_credentials_require_tls_and_environment_reference')
    elif 'password_env' in config:
        raise ServiceError('smtp_username_required')


def smtp(notification, config, delivery_id):
    """Stable Message-ID aids tracing, but SMTP provides no exactly-once guarantee."""
    validate_smtp(config)
    secret = os.environ.get(config['password_env']) if config.get('username') else None
    if config.get('username') and secret is None:
        return {'status': 'failed', 'reason_code': 'smtp_credential_unavailable'}
    message = EmailMessage()
    message['From'] = config['sender']
    message['To'] = ', '.join(config['recipients'])
    # User-controlled titles cannot create arbitrary mail headers.
    message['Subject'] = notification['title'].replace('\r', ' ').replace('\n', ' ')
    message['Message-ID'] = '<' + delivery_id + '@opsfeast.local>'
    message['Date'] = format_datetime(datetime.now(timezone.utc))
    message.set_content(notification['body'] + '\n\nSource record: ' + notification['evidence']['record_id'])
    client = None
    submitted = False
    try:
        security = config.get('security', 'starttls')
        factory = smtplib.SMTP_SSL if security == 'tls' else smtplib.SMTP
        kwargs = {'host': config['host'], 'port': config.get('port', 465 if security == 'tls' else 587),
                  'timeout': config.get('timeout', 15)}
        if security == 'tls':
            kwargs['context'] = ssl.create_default_context()
        client = factory(**kwargs)
        if security == 'starttls':
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if config.get('username'):
            client.login(config['username'], secret)
        submitted = True
        refused = client.send_message(message)
        # Some recipients may have accepted it: do not blindly resend to everyone.
        return {'status': 'unknown' if refused else 'delivered',
                'reason_code': 'partial_recipient_refusal' if refused else 'smtp_accepted'}
    except (OSError, smtplib.SMTPException) as exc:
        return {'status': 'unknown' if submitted else 'failed', 'reason_code': 'smtp_delivery_unconfirmed', 'error_type': type(exc).__name__}
    finally:
        if client is not None:
            client.close()


def vault(snapshot, config, root=None):
    from vault_content import text, markdown_table
    entries = {}
    links = {}
    if root is not None:
        from host_vault import observation_report_locations
        links = observation_report_locations(root, {o['evidence']['record_id'] for o in snapshot['objects']})
    index = ['# Notifications and todos', '', 'Generated: ' + snapshot['generated_at'], '',
             'Object status changes through the service API/CLI; these pages are generated.', '']
    for kind, title in (('notification', 'Notifications'), ('todo', 'Todos')):
        objects = [o for o in snapshot['objects'] if o['kind'] == kind]
        index += ['## ' + title, '']
        index += markdown_table(['Object', 'Host', 'Status', 'Last observed'], [
            (f'[{text(o["title"])}]({kind}/{o["id"]}.md)', text(o['source']['host_id']),
             o['status'], o['last_observed_at']) for o in objects]) + ['']
        for obj in objects:
            key = obj['evidence']['record_id']
            lines = ['# ' + text(obj['title']), '', *markdown_table(['Field', 'Value'], [
                ('ID', obj['id']), ('Kind', kind), ('Host', text(obj['source']['host_id'])),
                ('Status', obj['status']), ('Revision', obj['revision']),
                ('Condition active', obj['condition_active']), ('Observed', obj['last_observed_at']),
                ('Assignee', text(obj['assignee'] or 'Unassigned')), ('Due', obj['due_at'] or 'Not scheduled'),
                ('Verified complete', obj['verified']), ('Source record', text(obj['evidence']['record_id']))]), '',
                '## Details', '', text(obj['body']), '', '## Human note', '', text(obj['note'] or 'None.'), '',
                '## History', '']
            if links.get(key):
                from urllib.parse import quote
                relative = os.path.relpath(links[key], Path(root) / 'vault/Services' / kind)
                lines += ['[Source observation report](' + quote(relative, safe='/.-_') + ')', '']
            else:
                from opsfeast.transfer import archived_reference
                archived = archived_reference(root, key) if root is not None else None
                lines += ['Evidence archived: ' + text(archived['package']) + ' (receipt ' + archived['receipt_id'] + ').' if archived else 'Source observation report unavailable; retain the source record ID above for lookup.', '']
            lines += markdown_table(['At', 'Actor', 'Action', 'Status'], [
                (h['at'], text(h['actor']), h['action'], h['object']['status'])
                for h in snapshot['history'] if h['object']['id'] == obj['id']])
            entries[f'Services/{kind}/{obj["id"]}.md'] = '\n'.join(lines) + '\n'
    index += ['## Notification delivery', ''] + markdown_table(['Channel', 'Notification', 'State', 'Attempts'], [
        (text(d['channel']), d['notification_id'], d['status'], d['attempts']) for d in snapshot['deliveries']])
    entries['Services/SUMMARY.md'] = '\n'.join(index) + '\n'
    return entries


@contextmanager
def dispatch_lock(root):
    import fcntl
    from retention_store import checked
    path = checked(root, 'services', '.dispatch.lock')
    active = getattr(_DISPATCH, 'roots', set())
    identity = str(root)
    if identity in active:
        raise ServiceError('recursive_service_dispatch')
    path.parent.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        _DISPATCH.roots = active | {identity}
        yield
    finally:
        _DISPATCH.roots = active
        os.close(fd)


def dispatch(services, *, retry_unknown=False):
    config = configuration(services.root)
    from retention_store import settings
    if not settings(services.root)['vault']['auto_refresh']:
        config['presentations'] = {k: v for k, v in config['presentations'].items() if v['source'] != 'builtin:vault'}
    receipts = []
    # No objects means no creation of a database or output directory.
    if not services._list():
        return {'status': 'success', 'adapters': []}
    with dispatch_lock(services.root):
        for delivery in services.deliveries():
            if delivery['status'] in ('delivered', 'cancelled'):
                continue
            if delivery['status'] in ('sending', 'unknown') and not retry_unknown:
                receipts.append({'id': delivery['id'], 'status': 'unknown', 'reason_code': 'explicit_retry_required'})
                continue
            adapter = config['deliveries'].get(delivery['channel'])
            if not adapter or not adapter['enabled']:
                receipts.append({'id': delivery['id'], 'status': 'skipped', 'reason_code': 'channel_disabled'})
                continue
            retry = adapter.get('retry', {})
            if delivery['attempts'] >= retry.get('max_attempts', 5):
                receipts.append({'id': delivery['id'], 'status': 'failed', 'reason_code': 'delivery_attempt_limit'})
                continue
            if (delivery['status'] == 'failed' and delivery['receipt'].get('next_attempt_at', '') > now()):
                receipts.append({'id': delivery['id'], 'status': 'failed', 'reason_code': 'retry_not_due'})
                continue
            with services._db(True) as db:
                current = db.execute('SELECT status,attempts FROM deliveries WHERE id=?', (delivery['id'],)).fetchone()
                if current != (delivery['status'], delivery['attempts']):
                    continue
                obj = json.loads(db.execute('SELECT payload FROM objects WHERE id=?', (delivery['notification_id'],)).fetchone()[0])
                if obj.get('muted_until') and obj['muted_until'] > now():
                    receipts.append({'id': delivery['id'], 'status': 'skipped', 'reason_code': 'notification_muted'})
                    continue
                started = {'started_at': now(), 'object_revision': obj['revision'], 'source_record_id': obj['evidence']['record_id']}
                db.execute("UPDATE deliveries SET status='sending',attempts=attempts+1,payload=? WHERE id=?", (canonical(started), delivery['id']))
            try:
                if adapter['source'] == 'builtin:smtp':
                    result = smtp(copy_object(obj), adapter.get('config', {}), delivery['id'])
                else:
                    result = module(services.root, adapter)['deliver'](copy_object(obj), copy_object(adapter.get('config', {})), delivery['id'])
                if not isinstance(result, dict) or result.get('status') not in ('delivered', 'failed', 'unknown'):
                    raise ServiceError('invalid_delivery_receipt')
                # Adapter receipts may contain secrets: retain only the enumerated state and safe type.
                receipt = {'status': result['status'], 'completed_at': now()}
                safe_reasons = {'smtp_accepted', 'partial_recipient_refusal', 'smtp_credential_unavailable', 'smtp_delivery_unconfirmed'}
                receipt['reason_code'] = result.get('reason_code') if result.get('reason_code') in safe_reasons else 'adapter_reported_status'
                if adapter['source'] == 'builtin:smtp' and result.get('error_type'):
                    receipt['error_type'] = result['error_type']
            except Exception as exc:
                receipt = {'status': 'unknown', 'error_type': type(exc).__name__, 'completed_at': now()}
            if receipt['status'] == 'failed':
                receipt['next_attempt_at'] = (datetime.now(timezone.utc) + timedelta(seconds=retry.get('delay_seconds', 60))).isoformat(timespec='microseconds')
            receipt.update(started)
            with services._db(True) as db:
                current_obj = json.loads(db.execute('SELECT payload FROM objects WHERE id=?', (delivery['notification_id'],)).fetchone()[0])
                if receipt['status'] == 'failed' and current_obj['status'] == 'resolved' and obj['status'] == 'active':
                    receipt.update(status='cancelled', provider_status='failed', reason_code='resolved_during_delivery')
                db.execute('UPDATE deliveries SET status=?,payload=? WHERE id=?',
                           (receipt['status'], canonical(receipt), delivery['id']))
            receipts.append(dict(receipt, adapter=delivery['channel'], id=delivery['id']))
        for name, adapter in config['presentations'].items():
            if not adapter['enabled']:
                continue
            try:
                snapshot = services.snapshot()
                entries = vault(snapshot, {}, services.root) if adapter['source'] == 'builtin:vault' else module(services.root, adapter)['render'](snapshot, copy_object(adapter.get('config', {})))
                if not isinstance(entries, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in entries.items()):
                    raise ServiceError('invalid_presentation_output')
                if adapter.get('destination', 'vault') == 'files':
                    publish_files(services.root, name, entries)
                else:
                    from host_vault import locked, publish
                    with locked(services.root):
                        publish(services.root, 'service-' + name, entries)
                receipt = {'status': 'success', 'completed_at': now()}
            except Exception as exc:
                receipt = {'status': 'failed', 'error_type': type(exc).__name__, 'completed_at': now()}
            with services._db(True) as db:
                db.execute('INSERT OR REPLACE INTO projections VALUES (?,?,?)', (name, 0, canonical(receipt)))
            receipts.append(dict(receipt, adapter=name))
    return {'status': 'failed' if any(r['status'] in ('failed', 'unknown') for r in receipts) else 'success', 'adapters': receipts}


def copy_object(value):
    return json.loads(canonical(value))


def publish_files(root, name, entries):
    """Owned UTF-8 presentation files, isolated per adapter; no arbitrary root writes."""
    import tempfile
    from retention_store import checked
    base = checked(root, 'services', 'presentations', name)
    manifest = checked(root, 'services', 'presentations', name, '.manifest.json')
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in entries.items()):
        raise ServiceError('invalid_presentation_output')
    def target(relative):
        if (not relative or relative.startswith('/') or '\\' in relative
                or any(p in ('', '.', '..') or p.startswith('.') for p in relative.split('/'))):
            raise ServiceError('unsafe_presentation_output')
        return checked(root, 'services', 'presentations', name, *relative.split('/'))
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    if not isinstance(old, dict):
        raise ServiceError('invalid_presentation_manifest')
    for relative in old:
        target(relative)
    for relative in entries:
        path = target(relative)
        if path.exists() and relative not in old:
            raise ServiceError('unmanaged_presentation_collision')
    def atomic(path, content):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    owned = dict(old)
    for relative, content in entries.items():
        path = target(relative)
        atomic(path, content)
        owned[relative] = hashlib.sha256(content.encode()).hexdigest()
        atomic(manifest, canonical(owned))
    for relative in old.keys() - entries.keys():
        target(relative).unlink(missing_ok=True)
        owned.pop(relative)
        atomic(manifest, canonical(owned))
    return str(base)
