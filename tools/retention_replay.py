"""Offline raw retention snapshots and replay; never imports recipe executable code."""
import copy
import hashlib
import sqlite3
from pathlib import Path
from uuid import UUID

from opsfeast import ConfigError, read_yaml

VERSION = '0.1.0'
SNAPSHOT_VERSION = '0.2.0'


def digest(value):
    from retention_store import canonical
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def raw_digest(report):
    return digest({k: v for k, v in report.items() if k not in ('retention', 'content_update')})


def source_identity(report, fallback=None):
    value = report.get('source_observation_id')
    if value is not None:
        try:
            if not isinstance(value, str) or str(UUID(value)) != value:
                raise ValueError()
        except (ValueError, AttributeError):
            raise ConfigError('source_observation_id must be a canonical UUID') from None
        return value
    # Old files are not rewritten. Their IDs remain content-based until recollection.
    return fallback or raw_digest(report)


def execution_mode(report):
    mode = report.get('execution_access_mode')
    if mode is not None and mode not in ('read', 'write', 'unknown'):
        raise ConfigError('invalid recorded execution_access_mode')
    if report.get('operation_intent_id'):
        return 'write' if mode == 'write' else 'unknown'
    if mode is not None:
        return mode
    return 'read' if report.get('recipe', {}).get('id') == 'inventory-system' else 'unknown'


def producer_identity(report):
    """Replay cannot infer an old producer from the installation doing the replay."""
    from observation_store import uuid_text
    instance = report.get('instance', {})
    fallback = instance.get('id') if isinstance(instance, dict) else None
    return uuid_text(report.get('producer_instance_id', fallback or '00000000-0000-0000-0000-000000000000'))


def snapshot(metadata, directory):
    from retention_store import validate_retention
    declaration = validate_retention(metadata, directory)
    mode = metadata.get('access_mode', 'unknown')
    if mode not in ('read', 'write', 'unknown'):
        raise ConfigError('access_mode must be read, write or unknown')
    value = {'contract_version': SNAPSHOT_VERSION, 'recipe_id': metadata['id'], 'recipe_version': metadata['version'],
             'access_mode': mode, 'retention': copy.deepcopy(declaration)}
    if declaration and declaration['contract'] != 'host-values':
        from retention_contracts import normalizer_digest, schema_digest
        value['normalizer_sha256'] = normalizer_digest(declaration)
        value['schema_sha256'] = schema_digest(declaration)
    value['sha256'] = digest(value)
    return validate_snapshot(value)


def validate_snapshot(value):
    from retention_store import validate_retention
    keys = {'contract_version', 'recipe_id', 'recipe_version', 'access_mode', 'retention', 'sha256'}
    if not isinstance(value, dict) or not keys.issubset(value) or set(value) - keys - {'normalizer_sha256', 'schema_sha256'} or value['contract_version'] != SNAPSHOT_VERSION:
        raise ConfigError('incompatible retention snapshot; select a reviewed data-only definition with --recipe-dir')
    if value['access_mode'] not in ('read', 'write', 'unknown'):
        raise ConfigError('invalid snapshot access mode')
    if any(not isinstance(value[k], str) or not value[k] for k in ('recipe_id', 'recipe_version')):
        raise ConfigError('invalid snapshot recipe identity')
    if value['sha256'] != digest({k: v for k, v in value.items() if k != 'sha256'}):
        raise ConfigError('retention snapshot digest mismatch')
    declaration = validate_retention({'retention': value['retention']})
    if declaration and declaration['contract'] != 'host-values':
        from retention_contracts import normalizer_digest, schema_digest
        if value.get('schema_sha256') != schema_digest(declaration):
            raise ConfigError('saved retention schema differs from the installed registered contract; select an explicit reviewed --recipe-dir')
        if value.get('normalizer_sha256') != normalizer_digest(declaration):
            raise ConfigError('saved retention normalizer differs from the installed registered contract; select an explicit reviewed --recipe-dir')
    elif {'normalizer_sha256', 'schema_sha256'} & set(value):
        raise ConfigError('unexpected structured normalizer digest')
    return value


def provenance(report, fallback, selected_snapshot=None):
    return {'contract_version': VERSION, 'source_observation_id': source_identity(report, fallback),
            'raw_sha256': raw_digest(report), 'execution_access_mode': execution_mode(report),
            'snapshot_sha256': selected_snapshot['sha256'] if selected_snapshot else None,
            'retention_recipe_version': selected_snapshot['recipe_version'] if selected_snapshot else None}


def select_snapshot(report, directory=None):
    recipe = report.get('recipe', {})
    if directory is not None:
        directory = Path(directory).expanduser().resolve(strict=True)
        path = directory / 'recipe.yaml'
        if path.is_symlink():
            raise ConfigError('replay refuses a symlink descriptor')
        value = snapshot(read_yaml(path), directory)
    elif 'retention_snapshot' in report:
        value = validate_snapshot(report['retention_snapshot'])
        version = recipe.get('recipe_version', recipe.get('version'))
        if value['recipe_version'] != version:
            raise ConfigError('saved snapshot differs from executed recipe version')
        if report.get('execution_access_mode', value['access_mode']) != value['access_mode']:
            raise ConfigError('saved snapshot differs from recorded execution mode')
    else:
        raise ConfigError('raw has no retention snapshot; supply --recipe-dir explicitly')
    if value['recipe_id'] != recipe.get('id'):
        raise ConfigError('retention descriptor recipe ID differs from raw result')
    return value


def ingest(root, files=(), *, all_files=False, recipe_directory=None, dry_run=False):
    from retention_store import checked, settings, retain, retain_general
    from recipe_inputs import json_object
    if settings(root) is None:
        raise ConfigError('retention ingest requires namespace; initialize the profile first')
    if all_files and files:
        raise ConfigError('choose files or --all, not both')
    if all_files:
        directory = checked(root, 'observations')
        paths = sorted(directory.glob('*.json')) if directory.exists() else []
    else:
        paths = [Path(name).expanduser().absolute() for name in files]
        if not paths:
            raise ConfigError('ingest requires files or --all')
    results = []
    for path in paths:
        try:
            if path.is_symlink():
                raise ConfigError('replay refuses raw symlinks')
            report = json_object(path)
            source_identity(report)
            if not isinstance(report.get('recipe', {}), dict):
                raise ConfigError('raw recipe must be an object')
            if report.get('status') not in ('success', 'partial') or report.get('evidence_kind') not in ('local', 'ssh'):
                result = {'status': 'skipped', 'reason_code': 'result_not_retained'}
            elif not report.get('host_id') or 'report_contract' in report:
                result = {'status': 'skipped', 'reason_code': 'not_host_observation'}
            else:
                selected = select_snapshot(report, recipe_directory)
                if selected['retention'] and selected['retention']['contract'] == 'host-values':
                    if not isinstance(report.get('data'), dict):
                        raise ConfigError('general raw data must be an object')
                    result = retain_general(root, report, None, None, saved_snapshot=selected, dry_run=dry_run)
                else:
                    result = retain(root, report, dry_run=dry_run, saved_snapshot=selected)
            results.append(dict(result, file=str(path)))
        except (ConfigError, OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
            results.append({'file': str(path), 'status': 'failed', 'error_type': type(exc).__name__,
                            'message': str(exc) if isinstance(exc, ConfigError) else 'raw replay failed'})
    return {'status': 'failed' if any(item['status'] == 'failed' or item.get('content_update', {}).get('status') == 'failed' for item in results) else 'success',
            'dry_run': dry_run, 'files': results}
