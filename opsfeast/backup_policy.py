"""Deterministic backup findings -> shared services; no remote operations."""


def consume(context):
    services = context.services
    events = getattr(context, 'events', (getattr(context, 'event', None),))
    keys = {(e['host_id'], e['recipe_reference']) for e in events if e and e['event'] == 'retention.observation.created'}
    outcomes = []
    for host, reference in sorted(keys):
        records = context.retention.query(hosts=[host], recipe=reference)['records']
        records = [r for r in records if r.get('retention_definition', {}).get('contract') == 'backup-files-check']
        if not records:
            continue
        record = max(records, key=lambda r:(r['observed_at'], r['record_id']))
        for group in record['data']['backups']:
            source = {'host_id': host, 'recipe_reference': reference, 'subject': group['name']}
            evidence = {'record_id': record['record_id'], 'directory': group['directory'],
                        'check_date': record['data']['check_date'], 'retention_days': record['data']['policy']['retention_days']}
            complete = group['scan_status'] == 'complete'
            rules = [
                ('daily-missing', None if group['health'] in ('unknown', 'pending') else group['health'] == 'missing', True, False, 'error',
                 'Daily backup files missing', ', '.join(f['path'] for f in group['expected_files'] if f['present'] is not True)),
                ('expired-files', bool(group['expired_files']) if complete else None, False, True, 'warning',
                 'Review expired backup files', str(len(group['expired_files'])) + ' files exceed the saved age threshold.'),
                ('unexpected-entries', bool(group['unexpected_entries']) if complete else None, False, True, 'warning',
                 'Review unexpected backup entries', str(len(group['unexpected_entries'])) + ' unexpected entries.'),
                ('scan-failed', not complete, True, False, 'error', 'Backup directory scan incomplete', group['reason_code']),
            ]
            for rule, active, notify, todo, severity, title, details in rules:
                outcomes.append(services.reconcile(source=dict(source, rule=rule), owner='backup-check',
                    observed_at=record['observed_at'], evidence=evidence, active=active,
                    title=group['name'] + ': ' + title, body=group['directory'] + '\n' + details,
                    severity=severity, notification=notify, todo=todo))
    return {'status': 'success', 'conditions': outcomes}
