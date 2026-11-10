"""Data-only projections of reviewed retained contracts; never import producers."""
import hashlib
import json

MISSING = object()


def lookup(value, path):
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return MISSING
        value = value[part]
    return value


def fingerprint(record):
    return hashlib.sha256(json.dumps(record['retention_definition'], ensure_ascii=False,
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def latest(records):
    selected = {}
    for record in records:
        key = (record['namespace'], record['host_id'], record['recipe_reference'], fingerprint(record))
        candidate = (record['observed_at'], record['record_id'])
        if key not in selected or candidate > selected[key][0]:
            selected[key] = (candidate, record)
    return [item[1] for item in selected.values()]


def project(record, provider, spec):
    """Return independently scoped evidence entries for one declared property."""
    data = record['data']
    if provider['adapter'] == 'mysql-replication':
        return mysql(record, spec)
    value = lookup(data, spec['path'])
    coverage = lookup(data, spec['coverage_path']) if spec['coverage_path'] else None
    reason = []
    if isinstance(coverage, dict):
        complete = coverage.get('complete') is True or coverage.get('status') == 'complete'
        reason = coverage.get('reason_codes') or ([coverage['reason']] if coverage.get('reason') else [])
        if not complete and not reason: reason = ['coverage_' + str(coverage.get('status', 'unknown'))]
    else:
        complete = coverage is None and value is not MISSING and value is not None
        if not complete: reason = ['coverage_missing']
    # not_applicable/unknown empty collections are not successful empty enumerations.
    present = value is not MISSING and value is not None
    values = value if isinstance(value, list) else [value] if present else []
    state = 'complete' if complete and present else 'partial' if values else 'unavailable'
    observed = lookup(data, spec['time_path'])
    if not isinstance(observed, str): observed = record['observed_at']
    samples = []
    for index, item in enumerate(values[:20]):
        keys = {key: item[key] for key in spec.get('keys', []) if isinstance(item, dict) and key in item}
        if not keys and isinstance(value, list): keys = {'source_row': index}
        samples.append(sample(spec['id'], keys, item, observed, record['record_id']))
    if not present: reason = [*reason, 'field_not_reported']
    entry = evidence(record, spec, observed, state, samples, len(values), reason)
    if isinstance(coverage, dict):
        if isinstance(coverage.get('scope'), str): entry['source_scope'] = coverage['scope']
        if isinstance(coverage.get('commands'), list): entry['commands'] = coverage['commands']
    return [entry]


def sample(name, keys, value, observed, source):
    result = {'property': name, 'keys': keys, 'value': value, 'status': 'success',
              'reason_code': None, 'observed_at': observed, 'source_id': source}
    if isinstance(value, dict) and value.get('basis') in ('configured', 'effective', 'runtime', 'context'):
        result['basis'] = value['basis']
    return result


def evidence(record, spec, observed, state, samples, count, reasons):
    result = {'namespace': record['namespace'], 'recipe_reference': record['recipe_reference'],
              'definition_sha256': fingerprint(record), 'record_id': record['record_id'],
              'source_id': record['record_id'], 'observed_at': observed, 'state': state,
              'sample_count': count, 'successful_sample_count': count,
              'reason_codes': sorted(set(reasons)), 'samples': samples, 'samples_truncated': count > 20,
              'definition': {'contract': record['retention_definition']['contract'],
                  'version': record['retention_definition']['version'], 'unit': spec['unit'],
                  'projection': spec, 'basis': 'current data-only projection of the saved versioned contract'}}
    return result


def mysql(record, spec):
    results = []
    data = record['data']
    instances = data.get('instances', []) if isinstance(data, dict) else []
    if not isinstance(instances, list) or any(not isinstance(i, dict) or
            not all(isinstance(i.get(k), str) for k in ('instance', 'observed_at', 'health', 'reason', 'cleanup')) or
            not isinstance(i.get('probes'), list) or not isinstance(i.get('channels'), list) or
            i.get('server') is not None and not isinstance(i['server'], dict) for i in instances):
        return [evidence(record, spec, record['observed_at'], 'unavailable', [], 0, ['unsupported_instance_shape'])]
    if not instances:
        return [evidence(record, spec, record['observed_at'], 'unavailable', [], 0, ['instances_not_reported'])]
    server_field = spec['id'] == 'mysql.servers'
    for instance in instances:
        name = instance['instance']
        observed = instance['observed_at']
        probes = instance.get('probes', [])
        # Query/parse evidence, never health or the outer recipe status, determines
        # whether the selected projection was actually acquired.
        def acquired(probe):
            if not isinstance(probe, dict): return False
            sql = probe.get('sql', '')
            if not isinstance(sql, str): return False
            return (probe.get('exitcode') == 0 and probe.get('error') is None
                    and (sql.startswith('SELECT ') and isinstance(probe.get('stdout'), dict) if server_field
                         else sql in ('SHOW REPLICA STATUS;', 'SHOW SLAVE STATUS;') and isinstance(probe.get('stdout'), list)))
        complete = any(acquired(probe) for probe in probes)
        value = instance.get('server') if server_field else {
            key: instance[key] for key in ('channels', 'health', 'reason', 'cleanup')}
        present = value is not None and (server_field or complete or bool(value['channels']))
        state = 'complete' if complete and present else 'partial' if present else 'unavailable'
        rows = [sample(spec['id'], {'instance': name}, value, observed, record['record_id'])] if present else []
        entry = evidence(record, spec, observed, state, rows, len(rows),
                         [] if complete else [instance.get('reason', 'query_evidence_missing')])
        entry['instance'] = name
        results.append(entry)
    return results
