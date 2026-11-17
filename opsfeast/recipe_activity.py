"""Read-only recipe activity labels, shared with Web execution snapshots."""
from . import ConfigError


def meal_labels(profile, selected):
    from .menu_preferences import inspect, meal_catalog
    catalog = meal_catalog(inspect(profile)['sets']) if selected else {}
    labels = {}
    for identifier in selected:
        meal = catalog.get(identifier)
        if meal is None:
            continue
        title = meal['title']
        visited = set()
        def visit(key):
            if key in visited or key not in catalog:
                return
            visited.add(key)
            for ref in catalog[key]['recipes']:
                names = labels.setdefault(ref, [])
                if title not in names:
                    names.append(title)
            for child in catalog[key]['meals']:
                visit(child)
        visit(identifier)
    return labels


def history_labels(profile, service):
    """Map observation IDs to saved selection labels; never execute/rewrite history."""
    from recipe_catalog import catalog
    from .recipe_menu import display_title
    titles = {item['reference']: display_title(item['reference'], item.get('title'))
              for item in catalog(profile.root)['recipes']}
    observations = {}
    if service.directory.is_symlink():
        raise ConfigError('recipe_run_directory_must_be_real')
    for path in service.directory.glob('*.json'):
        try:
            record = service.show(path.stem, profile.name)
            current = None
            for task in record['tasks']:
                identifier = (task.get('result') or {}).get('observation_run_id')
                if not identifier:
                    continue
                reference = task['reference']
                title = task.get('title') or titles.get(reference, reference)
                meals = task.get('meal_titles')
                if meals is None:
                    if current is None:
                        current = meal_labels(profile, record.get('selected_meals', []))
                    meals = current.get(reference, [])
                previous = observations.get(identifier, {'recipe_titles': [], 'meal_titles': []})
                recipe_titles = list(dict.fromkeys([*previous['recipe_titles'], title]))
                meal_titles = list(dict.fromkeys([*previous['meal_titles'], *meals]))
                observations[identifier] = {'title': ' · '.join([*meal_titles, *recipe_titles]),
                                           'recipe_title': ' · '.join(recipe_titles),
                                           'recipe_titles': recipe_titles, 'meal_titles': meal_titles,
                                           'web_run_id': record['id']}
        except (ConfigError, OSError, ValueError, KeyError, TypeError):
            continue
    return titles, observations


def activity_summary(run, results=()):
    """Bounded human-summary projection of saved run/known result evidence."""
    targets = run.get('targets') or []
    good = sum(row.get('status') == 'success' and row.get('retention_status') not in ('failed', 'error') for row in targets)
    issues = []
    by_host = {row.get('host_id'): row for row in results}
    for row in targets:
        if row.get('status') == 'success' and row.get('retention_status') not in ('failed', 'error'):
            continue
        item = {key: row.get(key) for key in ('host_id', 'status', 'reason_code', 'retention_status')}
        saved = by_host.get(row.get('host_id'))
        if saved:
            raw = saved['raw'];data = raw.get('data') or {}
            item['result_id'] = saved['result_id']
            item['stages'] = [{key: stage.get(key) for key in ('stage', 'status', 'reason_code')}
                              for stage in (data.get('stages') or [])[:10] if isinstance(stage, dict)]
            snapshot = data.get('package_snapshot') or (data if data.get('kind') == 'os-package-inventory' else {})
            if snapshot:
                item['packages'] = {key: snapshot.get(key) for key in ('collected_count', 'complete')}
            reasons = [*(data.get('gaps') or []), *(snapshot.get('gaps') or []),
                       *((snapshot.get('platform_details') or {}).get('gaps') or [])]
            item['gaps'] = list(dict.fromkeys(str(reason)[:256] for reason in reasons))[:10]
            item['receipts'] = {key: (raw.get(key) or {}).get('status') for key in ('retention', 'content_update')}
        if len(issues) < 20:
            issues.append(item)
    return {'total_hosts': len(targets), 'completed_hosts': good,
            'incomplete_hosts': len(targets) - good, 'issues': issues,
            'omitted_hosts': max(0, len(targets) - good - len(issues))}
