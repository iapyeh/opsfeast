"""Profiling discovery/read model 0.1.0. Never acquire, execute or mutate data."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath

from . import ConfigError, REPOSITORY_ROOT

VERSION = '0.1.0'
REGISTRY = Path(__file__).with_name('profiling-catalog.json')


def _json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ConfigError('profiling resource must be a bounded regular file')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        raise ConfigError('invalid profiling resource JSON') from None


def _provider_catalog(provider):
    relative = PurePosixPath(provider['catalog_path'])
    if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):
        raise ConfigError('profiling provider catalog must stay inside product resources')
    path = Path(__file__).resolve().parent.parent if relative.parts[0]=='opsfeast' else REPOSITORY_ROOT
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ConfigError('profiling provider refuses symlink resources')
    data = _json(path)
    if not isinstance(data, dict) or not isinstance(data.get('jobs'), dict) or not isinstance(data.get('properties'), dict):
        raise ConfigError('invalid profiling provider property catalog')
    for name, spec in data['properties'].items():
        if not isinstance(spec, dict) or spec.get('id') != name or spec.get('job') not in data['jobs']:
            raise ConfigError('invalid profiling property/job binding')
        if provider['adapter'] != 'inventory-jobs':
            for key in ('path', 'coverage_path', 'time_path', 'keys'):
                if (not isinstance(spec.get(key), list)
                        or any(not isinstance(p, str) or not p for p in spec[key])):
                    raise ConfigError('invalid profiling data-only projection path')
            if not spec['path'] or not spec['time_path']:
                raise ConfigError('profiling projection requires value and source-time paths')
    return data


def _registry():
    data = _json(REGISTRY)
    if not isinstance(data, dict) or data.get('schema_version') != VERSION:
        raise ConfigError('unsupported profiling catalog')
    for key in ('domains', 'providers', 'capabilities'):
        if not isinstance(data.get(key), list):
            raise ConfigError('invalid profiling catalog collection')
        ids = [item.get('id') for item in data[key] if isinstance(item, dict)]
        if len(ids) != len(data[key]) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            raise ConfigError('invalid or duplicate profiling catalog ID')
    domains = {item['id'] for item in data['domains']}
    if any(set(item) != {'id', 'title'} or not isinstance(item['title'], str) or not item['title']
           for item in data['domains']):
        raise ConfigError('invalid profiling domain')
    providers = {}
    for provider in data['providers']:
        required = {'id', 'kind', 'recipe_reference', 'catalog_path', 'retention_contract',
                    'retention_version', 'adapter', 'scope_note'}
        if set(provider) != required or any(not isinstance(v, str) or not v for v in provider.values()):
            raise ConfigError('invalid profiling provider')
        if provider['kind'] not in ('recipe','meal') or provider['adapter'] not in ('inventory-jobs', 'retained-fields', 'mysql-replication'):
            raise ConfigError('profiling provider requires a reviewed read adapter')
        providers[provider['id']] = _provider_catalog(provider)
    assigned = {key: set() for key in providers}
    for capability in data['capabilities']:
        if (set(capability) != {'id', 'domain', 'title', 'observation_kind', 'scope_note', 'properties'}
                or not isinstance(capability['domain'], str) or capability['domain'] not in domains
                or capability['observation_kind'] not in ('inventory', 'configuration', 'state', 'metrics', 'events', 'analysis')
                or not isinstance(capability['title'], str) or not capability['title']
                or not isinstance(capability['scope_note'], str) or not capability['scope_note']
                or not isinstance(capability['properties'], dict)):
            raise ConfigError('invalid profiling capability')
        for provider_id, names in capability['properties'].items():
            if (provider_id not in providers or not isinstance(names, list) or not names
                    or any(not isinstance(n, str) for n in names) or len(names) != len(set(names))
                    or set(names) - set(providers[provider_id]['properties'])
                    or assigned[provider_id].intersection(names)):
                raise ConfigError('invalid or duplicate profiling property binding')
            assigned[provider_id].update(names)
    if any(assigned[key] != set(value['properties']) for key, value in providers.items()):
        raise ConfigError('profiling provider has unrouted properties')
    return data, providers


def provider_catalog(provider_id='system-inventory'):
    """Return the reviewed provider's unchanged native job/property definitions."""
    _, providers = _registry()
    if provider_id not in providers:
        raise ConfigError('unknown profiling provider')
    return copy.deepcopy(providers[provider_id])


def catalog(*, domain=None):
    """Static bundled integrations, not target applicability or collection success."""
    data, providers = _registry()
    if domain is not None and domain not in {d['id'] for d in data['domains']}:
        raise ConfigError('unknown profiling domain')
    capabilities = []
    for item in data['capabilities']:
        if domain is not None and item['domain'] != domain:
            continue
        specs = []
        for provider_id, names in item['properties'].items():
            for name in names:
                specs.append({'provider_id': provider_id, **providers[provider_id]['properties'][name]})
        capabilities.append({**item, 'integration': 'partial' if specs else 'not_integrated', 'properties': specs})
    return {'schema_version': VERSION, 'status': 'success',
            'domains': [d for d in data['domains'] if domain is None or d['id'] == domain],
            'providers': data['providers'], 'capabilities': capabilities,
            'limits': ['Integration is static and partial; it is not target applicability or full coverage.',
                       'Not integrated means no profiling adapter, not proof that no other bundled tool exists.',
                       'Discovery never connects, imports recipe code, enables jobs or installs dependencies.']}


def inspect_host(profile, host_id, *, domain=None, offset=0, limit=100):
    """Project latest retained attempts. Values and times come only from saved data.

    Rows preserve namespace/reference/definition boundaries. Pagination applies to
    properties; sample previews are bounded independently. Raw-only failures remain
    in saved-result diagnosis rather than being invented as retained observations.
    """
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 250:
        raise ConfigError('profiling offset/limit must be nonnegative / 1-250')
    profile.hosts.get(host_id)
    result = catalog(domain=domain)
    records = profile.retention.query(hosts=[host_id], kind='observation')['records']
    # Reuse the tested latest-attempt semantics, including newer failed samples.
    from inventory_jobs import latest_groups
    accepted = [r for r in records
                if (r.get('retention_definition') or {}).get('contract') in ('inventory-job-observations','inventory-routine-observations')
                and (r.get('retention_definition') or {}).get('version') == '0.1.0']
    inventory_records = accepted
    groups = latest_groups(inventory_records)
    record_index = {r['record_id']: r for r in accepted}
    bindings = {(spec['provider_id'], spec['id']): item['id'] for item in result['capabilities'] for spec in item['properties']}
    attempts = {}
    for group in groups:
        record = record_index[group['source_record_id']]
        for coverage in group['coverage']:
            name = coverage['property']
            if ('system-inventory', name) not in bindings:
                continue
            rows = [s for s in group['samples'] if s['property'] == name]
            success = sum(s['status'] == 'success' for s in rows)
            state = 'complete' if coverage['complete'] else 'partial' if success else 'unavailable'
            # No commands, stream output or host/account configuration in this view.
            attempts.setdefault(('system-inventory', name), []).append({
                'namespace': record['namespace'], 'recipe_reference': record['recipe_reference'],
                'definition_sha256': group['definition_sha256'], 'record_id': record['record_id'],
                'source_id': coverage['source_id'], 'observed_at': coverage['observed_at'],
                'state': state, 'sample_count': len(rows), 'successful_sample_count': success,
                'reason_codes': sorted({s['reason_code'] for s in rows if s.get('reason_code')} | ({'connection_restoration_unverified'} if record['data'].get('connection_evidence') and not record['data']['connection_evidence'].get('restoration_verified') else set()) | ({'connection_cleanup_unverified'} if record['data'].get('connection_evidence') and not record['data']['connection_evidence'].get('cleanup_verified') else set())),
                'routine_evidence':[r for r in record['data'].get('routine_evidence',[]) if name in r['properties']],
                'connection_evidence':record['data'].get('connection_evidence'),
                'samples': [_sample(s) for s in rows[:20]], 'samples_truncated': len(rows) > 20,
                'definition': group['property_definitions'][name],
            })
    from .profiling_sources import latest, project
    for provider in result['providers']:
        if provider['adapter'] == 'inventory-jobs':
            continue
        candidates = [r for r in records if (r.get('retention_definition') or {}).get('contract') == provider['retention_contract']
                      and (r.get('retention_definition') or {}).get('version') == provider['retention_version']]
        accepted.extend(candidates)
        specs = [spec for item in result['capabilities'] for spec in item['properties'] if spec['provider_id'] == provider['id']]
        for record in latest(candidates):
            for spec in specs:
                entries = project(record, provider, spec)
                for entry in entries:
                    entry['samples'] = [_sample(sample) for sample in entry['samples']]
                attempts.setdefault((provider['id'], spec['id']), []).extend(entries)
    items = []
    for capability in result['capabilities']:
        states = []
        for spec in capability['properties']:
            evidence = sorted(attempts.get((spec['provider_id'], spec['id']), []), key=lambda e: (e['namespace'], e['recipe_reference'], e['definition_sha256'], e.get('instance', '')))
            state = ('not_collected' if not evidence else 'complete' if all(e['state'] == 'complete' for e in evidence)
                     else 'partial' if any(e['state'] == 'complete' or e['successful_sample_count'] for e in evidence) else 'unavailable')
            states.append(state)
            items.append({'capability_id': capability['id'], 'domain': capability['domain'],
                          'property_id': spec['id'], 'provider_id': spec['provider_id'],
                          'job': spec['job'], 'unit': spec['unit'], 'state': state, 'evidence': evidence})
        capability['evidence_counts'] = {state: states.count(state) for state in ('complete', 'partial', 'unavailable', 'not_collected')}
    result.update(profile=profile.name, host_id=host_id,
                  read_at=datetime.now(timezone.utc).isoformat(),
                  items=items[offset:offset + limit], total=len(items),
                  next_offset=offset + limit if offset + limit < len(items) else None,
                  retained_record_count=len(accepted))
    result['limits'].extend([
        'Complete means complete for one declared property scope, not the host or capability.',
        'Latest attempts may have mixed ages; complete does not mean fresh or healthy.',
        'Only registered contract versions are projected; raw-only failures require saved-result inspection.',
        'At most 20 samples per property attempt are previewed; retention show provides the full record.',
    ])
    return result


def _sample(sample):
    result = copy.deepcopy(sample)
    value = result['value']
    # Keep the response useful for large package/endpoint lists without unbounded
    # text. Explicit preview metadata prevents truncation masquerading as a value.
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    result['value_preview'] = encoded[:2000]
    result['value_truncated'] = len(encoded) > 2000
    del result['value']
    return result
