"""Read recipe metadata and inspect entrypoints without executing recipe code."""
import json
from pathlib import Path

from opsfeast import ConfigError, REPOSITORY_RECIPES, plain_values, read_yaml
from recipe_dispatch import declared_version, validate
import recipe_contract


def recipe_path(value):
    if value is None:
        return REPOSITORY_RECIPES
    path = Path(value).expanduser()
    if path.is_absolute() or value.startswith(('./', '../', '~')):
        return path.resolve()
    if value == 'recipes' or value.startswith('recipes/'):
        path = Path(value).relative_to('recipes')
    result = (REPOSITORY_RECIPES / path).resolve()
    if not result.is_relative_to(REPOSITORY_RECIPES.resolve()):
        raise ConfigError('recipe short path escapes the checkout recipes directory')
    return result


def inspect_one(directory, requested):
    report = {'directory': str(directory), 'status': 'success', 'errors': [],
              'descriptor': None, 'implementations': [], 'coverage': None,
              'runner_contract': 'not-validated'}
    try:
        descriptor = directory / 'recipe.yaml'
        if not descriptor.resolve().is_relative_to(directory.resolve()):
            raise ConfigError('recipe descriptor escapes recipe directory')
        metadata = read_yaml(descriptor)
        if not isinstance(metadata, dict):
            raise ConfigError('recipe descriptor must be a mapping')
        plain_values(metadata, 'recipe descriptor')
        report['descriptor'] = metadata
        platforms = metadata.get('platforms', {})
        if not isinstance(platforms, dict):
            raise ConfigError('platforms must be a mapping')
        for key in ('planned', 'implemented', 'tested'):
            values = platforms.get(key, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                raise ConfigError(f'platforms.{key} must be a list of nonempty strings')
        implemented = platforms.get('implemented', [])
        report['coverage'] = {
            'requested': requested,
            'not_declared_implemented': [p for p in requested if p not in implemented],
            'planned_not_implemented': [p for p in platforms.get('planned', []) if p not in implemented],
            'implemented_not_declared_tested': [p for p in implemented if p not in platforms.get('tested', [])],
        }
        entries = metadata.get('implementations', [])
        if not isinstance(entries, list):
            raise ConfigError('implementations must be a list')
        for entry in entries:
            if not isinstance(entry, dict):
                report['errors'].append('implementation descriptor must be a mapping')
                continue
            item = {'declaration': entry, 'file_status': 'invalid', 'declared_code_version': None, 'error': None}
            report['implementations'].append(item)
            try:
                name = entry.get('entrypoint')
                if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
                    raise ConfigError('implementation entrypoint must be recipe-relative')
                path = (directory / name).resolve()
                if not path.is_relative_to(directory.resolve()):
                    raise ConfigError('implementation entrypoint escapes recipe directory')
                if not path.is_file():
                    raise ConfigError('implementation entrypoint is missing')
                if path.suffix != '.py':
                    raise ConfigError('implementation entrypoint must be a Python file')
                item['declared_code_version'] = declared_version(path)
                if item['declared_code_version'] != entry.get('version'):
                    raise ConfigError('implementation VERSION differs from descriptor')
                item['file_status'] = 'valid'
            except (ConfigError, OSError, UnicodeError) as exc:
                item['error'] = str(exc)
                report['errors'].append(f"{entry.get('id', '<unnamed>')}: {exc}")
        # This is the existing runner's exact contract, not a general descriptor schema.
        if metadata.get('id') == 'inventory-system':
            try:
                validate(directory, metadata)
                report['runner_contract'] = 'valid-inventory-system'
            except (ConfigError, OSError, UnicodeError) as exc:
                report['runner_contract'] = 'invalid-inventory-system'
                report['errors'].append(str(exc))
        elif 'runner' in metadata:
            try:
                recipe_contract.validate(directory, metadata)
                report['runner_contract'] = 'valid-' + metadata['runner']['contract']
            except (ConfigError, OSError, UnicodeError) as exc:
                report['runner_contract'] = 'invalid-' + str((metadata.get('runner') or {}).get('contract', 'python-session')) if isinstance(metadata.get('runner'), dict) else 'invalid-python-session'
                report['errors'].append(str(exc))
        else:
            report['runner_contract'] = 'unsupported-recipe-id'
    except (ConfigError, OSError, UnicodeError) as exc:
        report['errors'].append(str(exc))
    if report['errors']:
        report['status'] = 'failed'
    return report


def inspect_recipes(value=None, requested=()):
    directory = recipe_path(value)
    if not directory.is_dir():
        raise ConfigError(f'recipe directory does not exist: {directory}')
    requested = list(dict.fromkeys(requested))
    if value is not None:
        candidates = [directory]
    else:
        candidates = sorted({p.parent for p in directory.rglob('recipe.yaml')})
        if not candidates:
            raise ConfigError('no recipe descriptors found in checkout recipes directory')
    reports = []
    for candidate in candidates:
        if not candidate.resolve().is_relative_to(directory.resolve()):
            reports.append({'directory': str(candidate), 'status': 'failed',
                            'errors': ['recipe directory escapes discovery root'], 'descriptor': None,
                            'implementations': [], 'coverage': None, 'runner_contract': 'not-validated'})
        else:
            reports.append(inspect_one(candidate, requested))
    return {'inspection_version': '0.1.0', 'status': 'failed' if any(r['status'] == 'failed' for r in reports) else 'success',
            'recipes': reports}


def format_details(report):
    lines = []
    for recipe in report['recipes']:
        meta = recipe['descriptor'] or {}
        lines.append(f"{meta.get('id', '<unknown>')} — {meta.get('title', '')} (version {meta.get('version', 'unknown')})")
        lines.append(f"  Directory: {recipe['directory']}")
        lines.append(f"  Inspection: {recipe['status']}; runner contract: {recipe['runner_contract']}")
        lines.append(f"  Description: {meta.get('description', 'not declared')}")
        platforms = meta.get('platforms', {})
        if isinstance(platforms, dict):
            for key in ('planned', 'implemented', 'tested'):
                lines.append(f"  Platforms {key}: {platforms.get(key, 'not declared')}")
        for item in recipe['implementations']:
            entry = item['declaration']
            lines.append(f"  Implementation {entry.get('id', '<unnamed>')}: {entry.get('entrypoint')} version={entry.get('version')} file={item['file_status']}")
            lines.append(f"    Match: {entry.get('match')}; priority={entry.get('priority', 0)}")
            lines.append(f"    Verification: {entry.get('verification', 'not declared')}")
        if recipe['coverage']:
            for key, values in recipe['coverage'].items():
                lines.append(f"  {key}: {values}")
        for key in ('runner', 'dependencies', 'permissions', 'side_effects', 'inputs', 'output', 'verification'):
            lines.append(f'  {key}:')
            lines.extend('    ' + line for line in json.dumps(meta.get(key, 'not declared'), indent=2, ensure_ascii=False).splitlines())
        for error in recipe['errors']:
            lines.append(f'  ERROR: {error}')
        lines.append('')
    lines.append('Metadata/static inspection only; no recipe execution, host connection or platform discovery. Declared coverage is not proof of host applicability or successful execution.')
    return '\n'.join(lines)


def format_report(report, details=False):
    if details:
        return format_details(report)
    lines = []
    for recipe in report['recipes']:
        meta = recipe['descriptor'] or {}
        lines.append(f"{meta.get('id', '<unknown>')} {meta.get('version', '?')} — {meta.get('title', '')}")
        platforms = meta.get('platforms', {})
        platforms = platforms if isinstance(platforms, dict) else {}
        implemented = platforms.get('implemented', [])
        tested = platforms.get('tested', [])
        planned = platforms.get('planned', [])
        requested = (recipe['coverage'] or {}).get('requested', [])
        if requested:
            for platform in requested:
                if platform not in implemented:
                    state = 'planned; not implemented' if platform in planned else 'not declared supported'
                    lines.append(f'  {platform}: {state}')
                    continue
                lines.append(f"  {platform}: implemented; {'declared tested' if platform in tested else 'not declared tested'}")
                candidates = [item for item in recipe['implementations']
                              if isinstance(item['declaration'].get('match'), dict)
                              and item['declaration']['match'].get('os_name', platform) == platform]
                if not candidates:
                    lines.append('    No entrypoint declared for this OS; inspect --details.')
                for item in candidates:
                    entry = item['declaration']
                    conditions = {k: v for k, v in entry['match'].items() if k != 'os_name'}
                    limits = ', '.join(f'{k}={v}' for k, v in conditions.items()) or 'no additional platform conditions'
                    lines.append(f"    {entry.get('id', '<unnamed>')}: file {item['file_status']}; {limits}")
                    evidence = entry.get('verification')
                    if isinstance(evidence, dict) and evidence:
                        lines.append('    Evidence: ' + '; '.join(f'{k}: {v}' for k, v in evidence.items()))
        else:
            description = meta.get('description')
            if description:
                lines.append(f'  {description}')
            for label, values in (
                ('Implemented', implemented),
                ('Declared tested', tested),
                ('Planned only', [v for v in planned if v not in implemented] if isinstance(planned, list) and isinstance(implemented, list) else []),
            ):
                if label == 'Planned only' and not values:
                    continue
                summary = ', '.join(values) if isinstance(values, list) and all(isinstance(v, str) for v in values) else 'invalid declaration'
                lines.append(f"  {label}: {summary or 'none declared'}")
        if recipe['runner_contract'] == 'unsupported-recipe-id':
            lines.append('  Runner: this recipe ID is not supported.')
        for error in dict.fromkeys(recipe['errors']):
            lines.append(f'  ERROR: {error}')
        lines.append('')
    lines.append('Metadata/static inspection only. Use --details or --json for the full report.')
    return '\n'.join(lines)
