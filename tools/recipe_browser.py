"""Read-only source/directory recipe tree and provenance-matched run history."""
from pathlib import Path
from datetime import datetime
from display_time import local_datetime, human_times


def local_started(value):
    return local_datetime(value)


def display_started(value):
    """Convert recorded instants to OS local wall time, hiding offset/fractions."""
    if not value:
        return '(unknown)'
    local = local_started(value)
    return local.strftime('%Y-%m-%d %H:%M:%S') if local is not None else '(invalid or unzoned time)'


def started_column(values=()):
    offsets = {local.utcoffset() for value in values if (local := local_started(value)) is not None}
    if not offsets:
        offsets = {datetime.now().astimezone().utcoffset()}
    labels = []
    for offset in sorted(offsets):
        seconds = int(offset.total_seconds())
        hours, rest = divmod(abs(seconds), 3600)
        minutes, seconds_part = divmod(rest, 60)
        suffix = f':{minutes:02d}' if minutes or seconds_part else ''
        if seconds_part:
            suffix += f':{seconds_part:02d}'
        labels.append(f'GMT{"+" if seconds >= 0 else "-"}{hours}{suffix}')
    return 'Time (started, ' + '/'.join(labels) + ')'


def snapshot():
    from opsfeast import load_profiles, resolve_root
    from recipe_catalog import catalog
    from recipe_reports import results
    try:
        profiles = load_profiles()
        root = resolve_root() if profiles['default_profile'] is not None else None
        data = catalog(root)
        index = results(root) if root is not None else {'results': [], 'errors': [], 'status': 'success'}
        return {'catalog': data, 'history': index, 'root': str(root) if root else None,
                'profile_name': profiles['default_profile'],
                'message': 'Default Feast: ' + (str(root) if root else 'none (checkout catalog only)')}
    except Exception as exc:
        return {'catalog': {'sources': [], 'recipes': [], 'status': 'failed'},
                'history': {'results': [], 'errors': [], 'status': 'failed'}, 'root': None,
                'message': 'Recipe browser unavailable: ' + type(exc).__name__}


def directory_parts(item, source):
    return Path(item['directory']).relative_to(Path(source['root'])).parts


def history_for(item, records):
    return [record for record in records if record.get('recipe_source') == item['source']
            and record.get('recipe_reference') == item['reference']]


def describe(item):
    """Literal, read-only metadata; compatibility is not execution evidence."""
    import json
    if item is None:
        return 'Select a recipe directory to inspect its information.'
    descriptor = item.get('descriptor') or {}
    lines = []
    for label, key in [('Title','title'),('Description','description'),('Recipe ID','id'),('Version','version'),
                       ('Source','source'),('Reference','reference'),('Directory','directory'),('Kind','kind'),
                       ('Runner contract','contract'),('Static inspection','status')]:
        value = item.get(key)
        lines.extend([label, str(value) if value not in (None, '') else '(not declared)', ''])
    for label, value in [('Author',item.get('author')), ('License',item.get('license')), ('Inputs',item.get('inputs')), ('Dependencies',item.get('dependencies')),
                         ('Platforms',descriptor.get('platforms')), ('Permissions',descriptor.get('permissions')),
                         ('Side effects',descriptor.get('side_effects')), ('Output',descriptor.get('output')),
                         ('Verification',item.get('verification')), ('Inspection errors',item.get('errors'))]:
        lines.extend([label, json.dumps(human_times(value), indent=2, ensure_ascii=False, default=str) if value is not None else '(not declared)', ''])
    lines.append('Static metadata only; installed dependencies, host applicability and successful execution are not established.')
    return '\n'.join(lines)


def source_label(source, profile_name=None):
    if source['name'] == 'repository':
        name = 'OpsFeast Bundle'
    elif source['name'] == 'profile':
        name = profile_name or 'Profile'
    else:
        name = source['name']
    return name + ' (' + source['status'] + ')'


def execution_output(root, identifier, item):
    """Read one guarded saved result and verify its source/reference again."""
    from opsfeast import ConfigError
    from recipe_reports import result_path
    from recipe_inputs import parse_json_object
    import json
    path = result_path(Path(root), identifier)
    original = path.read_text(encoding='utf-8')
    document = parse_json_object(original)
    metadata = document.get('recipe')
    if not isinstance(metadata, dict) or document.get('status') not in ('success', 'partial', 'failed', 'skipped', 'unsupported'):
        raise ConfigError('unrecognized result envelope')
    if metadata.get('source_name') != item['source'] or metadata.get('reference') != item['reference']:
        raise ConfigError('result no longer belongs to the selected recipe')
    return {'details': json.dumps(human_times(document), indent=2, ensure_ascii=False), 'original': original}
