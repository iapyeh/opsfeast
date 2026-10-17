"""Offline report execution, raw-run lookup and escaped basic HTML views."""
from dataclasses import dataclass
import hashlib
import html
import json
from pathlib import Path
import re
import runpy
import sys
from uuid import uuid4

from opsfeast import ConfigError
from recipe_catalog import configuration
from recipe_contract import validate, validate_result
from recipe_dispatch import bundle_digest
from recipe_inputs import cli_variables, json_object, prepare_vars, parse_json_object
from host_runtime import now
from display_time import format_time

VERSION = '0.1.0'


def safe_directory(root, relative, create=False):
    path = root / relative
    for component in [path, *path.parents]:
        if component == root.parent:
            break
        if component.is_symlink():
            raise ConfigError('managed storage cannot contain symlinks')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ConfigError('storage escapes management root')
    if path.exists() and not path.is_dir():
        raise ConfigError('managed storage must be a directory')
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    from run_recipe import save_report
    save_report(path, value)


def page(title, headers, rows, note=''):
    escape = lambda value: html.escape(str(format_time(value)), quote=True)
    cells = ''.join('<tr>' + ''.join('<td>' + escape(value) + '</td>' for value in row) + '</tr>' for row in rows)
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>' + escape(title) + '</title><style>body{font:16px system-ui;margin:2em;line-height:1.5}table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:.5em;text-align:left;vertical-align:top}td{overflow-wrap:anywhere}th{background:#eee}</style>'
            '<h1>' + escape(title) + '</h1><p>' + escape(note) + '</p><table><thead><tr>' + ''.join('<th>' + escape(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + cells + '</tbody></table></html>')


def export_html(path, content):
    path = path.expanduser()
    if path.is_symlink():
        raise ConfigError('HTML destination cannot be a symlink')
    with path.open('x', encoding='utf-8') as output:
        output.write(content)
    return str(path.resolve())


@dataclass
class ReportContext:
    vars: dict
    inputs: list
    artifact_dir: Path


def validate_artifacts(directory, declarations):
    if not isinstance(declarations, list):
        raise ConfigError('report artifacts must be a list')
    output, names = [], set()
    for item in declarations:
        if not isinstance(item, dict) or set(item) != {'path', 'title', 'media_type'}:
            raise ConfigError('artifact requires path, title and media_type')
        if any(not isinstance(item[key], str) or not item[key] for key in item):
            raise ConfigError('artifact metadata must contain nonempty strings')
        name = Path(item['path'])
        if name.is_absolute() or '..' in name.parts or name.as_posix() in names:
            raise ConfigError('artifact paths must be unique relative paths')
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
            raise ConfigError('artifact is missing or escapes output directory')
        if any(part.is_symlink() for part in [path, *path.parents] if part.is_relative_to(directory)):
            raise ConfigError('artifact symlinks are not supported')
        names.add(name.as_posix())
        output.append(dict(item, size_bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return output


def run_report(root, item, inputs, values=None, assignments=(), timeout=30):
    directory = Path(item['directory'])
    config = configuration(root)
    info = config.recipe_location(item['reference'], config.root / 'hosts.yaml', cli=True)
    if not info['enabled']:
        raise ConfigError('report source is disabled')
    metadata = item['descriptor']
    validate(directory, metadata)
    effective = prepare_vars(metadata, info['vars'], {}, cli_variables(metadata, values, assignments))
    documents, sources = [], []
    for path in inputs:
        path = path.expanduser().resolve(strict=True)
        content = path.read_bytes()
        document = parse_json_object(content)
        documents.append(document)
        sources.append({'name': path.name, 'sha256': hashlib.sha256(content).hexdigest()})
    run_id = uuid4().hex
    destination = safe_directory(config.root, 'reports/' + run_id, create=True)
    artifacts = safe_directory(config.root, 'reports/' + run_id + '/artifacts', create=True)
    report = {'report_contract': VERSION, 'run_id': run_id, 'host_id': None,
              'started_at': now(), 'completed_at': None, 'status': 'failed', 'reason_code': 'execution_failed',
              'message': 'Report execution failed.', 'data': {}, 'artifacts': [], 'sources': sources,
              'schema_version': metadata['output']['schema_version'], 'evidence_kind': 'local-report',
              'recipe': {'id': metadata['id'], 'version': metadata['version'], 'reference': item['reference'],
                         'source_name': item['source'], 'variable_names': sorted(effective),
                         'descriptor_sha256': hashlib.sha256((directory / 'recipe.yaml').read_bytes()).hexdigest(),
                         'bundle_sha256': bundle_digest(directory)},
              'runtime': {'python': sys.version.split()[0], 'interpreter': sys.executable},
              'execution_errors': [], 'retention': {'status': 'skipped', 'reason_code': 'report-not-inventory'}}
    stage = 'implementation_loading'
    try:
        # Same lock as host recipe loading: runpy alters process import state.
        from run_recipe import _implementation_lock
        with _implementation_lock:
            selected = runpy.run_path(str(directory / metadata['runner']['entrypoint']))
        if selected.get('VERSION') != metadata['version'] or not callable(selected.get('execute')):
            raise ConfigError('report runtime VERSION or execute differs from contract')
        stage = 'execution'
        result = selected['execute'](context=ReportContext(effective, documents, artifacts), timeout=timeout)
        stage = 'result_validation'
        if not isinstance(result, dict) or set(result) != {'status', 'reason_code', 'message', 'data', 'artifacts'}:
            raise ConfigError('report result requires common result fields plus artifacts')
        declared = validate_artifacts(artifacts, result['artifacts'])
        validated = validate_result({key: value for key, value in result.items() if key != 'artifacts'})
        report.update(validated, artifacts=declared)
    except (Exception, SystemExit) as exc:
        report['reason_code'] = 'invalid_result' if stage == 'result_validation' else 'execution_failed'
        report['execution_errors'].append({'stage': stage, 'type': type(exc).__name__})
    report['completed_at'] = now()
    safe_directory(config.root, destination.relative_to(config.root))
    safe_directory(config.root, artifacts.relative_to(config.root))
    path = destination / 'result.json'
    write_json(path, report)
    return report, path


def _result_files(root):
    for relative, pattern in (('observations', '*.json'), ('reports', '*/result.json')):
        base = safe_directory(root, relative)
        if not base.exists():
            continue
        for path in sorted(base.glob(pattern)):
            yield path.relative_to(root).as_posix(), path


def _result_key(identifier):
    return hashlib.sha256(identifier.encode('utf-8')).hexdigest()


def _short_result_ids(identifiers):
    ordered = sorted((_result_key(identifier), identifier) for identifier in identifiers)
    short = {}
    for index, (key, identifier) in enumerate(ordered):
        neighbors = [ordered[i][0] for i in (index - 1, index + 1) if 0 <= i < len(ordered)]
        length = 8
        while any(other.startswith(key[:length]) for other in neighbors):
            length += 1
            if length > len(key):
                raise ConfigError('result ID digest collision; use full storage-relative IDs')
        short[identifier] = key[:length]
    return short


def collection_user(raw):
    """Return only a supported, observed collection actor; never guess from login."""
    if not isinstance(raw, dict) or not isinstance(raw.get('recipe'), dict) or raw['recipe'].get('id') != 'inventory-system':
        return None
    access = raw.get('access')
    observations = raw.get('observations')
    if not isinstance(access, dict) or not isinstance(observations, dict):
        return None
    attempted = {'success', 'unavailable', 'unsupported', 'permission_denied',
                 'timeout', 'command_failed', 'parsing_failed'}
    if not any(isinstance(item, dict) and isinstance(item.get('status'), str)
               and item['status'] in attempted for item in observations.values()):
        return None
    actor = access.get('actual_identity')
    mode = access.get('mode')
    if not isinstance(actor, dict) or mode not in ('root', 'user', 'fallback_user'):
        return None
    name, uid = actor.get('username'), actor.get('effective_uid')
    if (not isinstance(name, str) or not name.strip() or any(ord(c) < 32 or ord(c) == 127 for c in name)
            or type(uid) is not int or uid < 0 or (mode == 'root') != (uid == 0)):
        return None
    return name


def results(root, recipe=None, host=None, status=None):
    records, errors = [], []
    files = list(_result_files(root))
    short_ids = _short_result_ids(identifier for identifier, path in files)
    for identifier, path in files:
        try:
            safe_directory(root, path.parent.relative_to(root))
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ConfigError('result escapes storage root')
            raw = json_object(path)
            meta = raw.get('recipe', {})
            if not isinstance(meta, dict) or raw.get('status') not in ('success', 'partial', 'failed', 'skipped', 'unsupported'):
                raise ConfigError('unrecognized result envelope')
            row = {'result_id': identifier, 'short_id': short_ids[identifier],
                   'recipe_id': meta.get('id'), 'recipe_version': meta.get('version'),
                   'recipe_reference': meta.get('reference'), 'recipe_source': meta.get('source_name'),
                   'host_id': raw.get('host_id'), 'status': raw['status'], 'reason_code': raw.get('reason_code'),
                   'started_at': raw.get('started_at'), 'completed_at': raw.get('completed_at', raw.get('finished_at')),
                   'identity_quality': raw.get('identity', {}).get('quality') if isinstance(raw.get('identity'), dict) else None,
                   'collection_user': collection_user(raw),
                   'identity_warnings': raw.get('identity', {}).get('warnings', []) if isinstance(raw.get('identity'), dict) else [],
                   'retention': raw.get('retention'), 'kind': 'report' if 'report_contract' in raw else 'operation'}
            if recipe and row['recipe_id'] != recipe or host and row['host_id'] != host or status and row['status'] != status:
                continue
            records.append(row)
        except (ConfigError, OSError, ValueError, TypeError):
            errors.append({'result_id': identifier, 'short_id': short_ids[identifier],
                           'reason_code': 'invalid-result-file'})
    records.sort(key=lambda row: (str(row['started_at'] or ''), row['result_id']), reverse=True)
    return {'results_version': VERSION, 'status': 'partial' if errors else 'success', 'results': records, 'errors': errors}


def result_path(root, identifier):
    if re.fullmatch(r'[0-9a-f]{8,64}', identifier):
        matches = [name for name, path in _result_files(root) if _result_key(name).startswith(identifier)]
        if not matches:
            raise ConfigError('unknown short result ID')
        if len(matches) != 1:
            raise ConfigError('ambiguous short result ID; use a longer prefix or full result ID')
        identifier = matches[0]
    relative = Path(identifier)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] not in ('observations', 'reports'):
        raise ConfigError('result ID must be relative to observations/ or reports/')
    path = root / relative
    if not ((len(relative.parts) == 2 and relative.parts[0] == 'observations' and path.suffix == '.json') or
            (len(relative.parts) == 3 and relative.parts[0] == 'reports' and relative.parts[-1] == 'result.json')):
        raise ConfigError('result ID must identify a raw observation or report result.json')
    safe_directory(root, relative.parent)
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ConfigError('result file is missing or escapes management root')
    return path


def show_result(root, identifier):
    path = result_path(root, identifier)
    document = json_object(path)
    if not isinstance(document.get('recipe'), dict) or document.get('status') not in ('success', 'partial', 'failed', 'skipped', 'unsupported'):
        raise ConfigError('unrecognized result envelope')
    return document


def show_artifact(root, identifier, name):
    path = result_path(root, identifier)
    report = json_object(path)
    if report.get('report_contract') != VERSION or path.parent.parent != root / 'reports':
        raise ConfigError('artifact selection requires a report result ID')
    declared = [item for item in report.get('artifacts', []) if isinstance(item, dict) and item.get('path') == name]
    if len(declared) != 1:
        raise ConfigError('artifact not declared by report')
    info = declared[0]
    checked = validate_artifacts(path.parent / 'artifacts', [{key: info[key] for key in ('path', 'title', 'media_type')}])[0]
    if checked['sha256'] != info.get('sha256') or checked['size_bytes'] != info.get('size_bytes'):
        raise ConfigError('artifact content changed after generation')
    return {**checked, 'relative_path': checked['path'], 'path': str((path.parent / 'artifacts' / name).resolve())}
