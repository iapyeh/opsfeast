"""Portable catalog 0.1.0; static inspection, no entrypoint imports or connections."""

from opsfeast import ConfigError, Validator, REPOSITORY_RECIPES
from recipe_inspection import inspect_one

VERSION = '0.1.0'


def configuration(root):
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    return config


def catalog(root=None, query=None, kind=None):
    sources = [{'name': 'repository', 'root': REPOSITORY_RECIPES.resolve(), 'enabled': True, 'prefix': ''}]
    if root is not None:
        config = configuration(root)
        sources[0].update(config.default_recipe_sources['bundle'])
        sources.append({'name': 'profile', 'root': config.root / 'recipes', 'prefix': ':',
                        **config.default_recipe_sources['profile']})
        sources.extend({'name': name, 'prefix': name + ':', **settings} for name, settings in config.recipe_sources.items())
    result = {'catalog_version': VERSION, 'status': 'success', 'sources': [], 'recipes': []}
    for source in sources:
        base = source['root']
        record = {'name': source['name'], 'root': str(base), 'enabled': source['enabled'], 'status': 'available', 'errors': []}
        result['sources'].append(record)
        if not source['enabled']:
            record['status'] = 'disabled'
            continue
        if not base.exists():
            record['status'] = 'absent' if source['name'] == 'profile' else 'unavailable'
            if source['name'] != 'profile':
                record['errors'].append('source directory is missing')
                result['status'] = 'failed'
            continue
        if not base.is_dir():
            record.update(status='unavailable', errors=['source is not a directory'])
            result['status'] = 'failed'
            continue
        ids = {}
        try:
            descriptors = sorted(base.rglob('recipe.yaml'))
        except OSError:
            record.update(status='unavailable', errors=['source cannot be read'])
            result['status'] = 'failed'
            continue
        for descriptor in descriptors:
            directory = descriptor.parent
            reference = source['prefix'] + directory.relative_to(base).as_posix()
            inspected = inspect_one(directory, []) if directory.resolve().is_relative_to(base.resolve()) else {
                'status': 'failed', 'errors': ['recipe escapes source root'], 'descriptor': None, 'runner_contract': 'not-validated'}
            meta = inspected.get('descriptor') or {}
            contract = inspected['runner_contract']
            recipe_kind = 'report' if isinstance(meta.get('runner'), dict) and meta['runner'].get('contract') == 'python-report' else 'operation'
            item = {'reference': reference, 'source': source['name'], 'directory': str(directory),
                    'id': meta.get('id'), 'version': meta.get('version'), 'title': meta.get('title', ''),
                    'description': meta.get('description', ''), 'kind': recipe_kind,
                    'contract': contract, 'status': inspected['status'], 'errors': list(inspected['errors']),
                    'runnable': inspected['status'] == 'success' and contract in ('valid-python-session', 'valid-python-report', 'valid-inventory-system'),
                    'inputs': meta.get('inputs', {}), 'dependencies': meta.get('dependencies', {}),
                    'verification': meta.get('verification', {}), 'descriptor': meta,
                    'availability_evidence': 'static-only; dependencies, data and host applicability are not verified'}
            from recipe_identity import normalized
            try:
                item.update(normalized(meta))
            except ConfigError:
                item.update(author={'name':'Unknown','contacts':['Unknown']}, license='Unknown')
            result['recipes'].append(item)
            if isinstance(item['id'], str):
                ids.setdefault(item['id'], []).append(item)
        for duplicates in ids.values():
            if len(duplicates) > 1:
                for item in duplicates:
                    item.update(status='failed', runnable=False)
                    item['errors'].append('duplicate recipe ID within source')
        if any(item['status'] == 'failed' for item in result['recipes'] if item['source'] == source['name']):
            result['status'] = 'failed'
    # Same IDs across different sources remain distinct; resolving by ID must be explicit.
    if query:
        needle = query.casefold()
        result['recipes'] = [item for item in result['recipes'] if needle in ' '.join(str(item.get(key, '')) for key in ('reference', 'id', 'title', 'description')).casefold()]
    if kind:
        result['recipes'] = [item for item in result['recipes'] if item['kind'] == kind]
    return result


def choose(root, selector):
    data = catalog(root)
    exact = [item for item in data['recipes'] if item['reference'] == selector]
    candidates = exact or [item for item in data['recipes'] if item['id'] == selector]
    if len(candidates) > 1:
        raise ConfigError('recipe selector is ambiguous; use an explicit source/path reference')
    if not candidates:
        raise ConfigError('recipe not found in active catalog; check sources and use an explicit reference')
    return candidates[0]
