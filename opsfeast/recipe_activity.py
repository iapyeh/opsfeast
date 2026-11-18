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


def group_web_activity(items, requested_id=None):
    """Use the persisted Web invocation ID as the activity row identity."""
    groups, standalone = {}, []
    for item in items:
        parent = item.get('web_run_id')
        if parent and item['id'] != requested_id:
            groups.setdefault(parent, []).append(item)
        else:
            standalone.append(item)
    for parent, members in groups.items():
        entry = members[0].copy()
        refs = {member['recipe_reference'] for member in members}
        titles = list(dict.fromkeys(title for member in members for title in
                                    [*member['meal_titles'], *member['recipe_titles']]))
        targets = {}
        for member in members:
            for target in member['details'].get('targets', []):
                host = target['host_id']
                if host not in targets or not completed_target(target):
                    targets[host] = target
        unique_links = {row['result_id']: {**row, **({'recipe_reference': member['recipe_reference']} if len(refs) > 1 else {})}
                        for member in members for row in member['result_links']}
        states = {member['status'] for member in members}
        entry.update(id=parent, time=min(member['time'] for member in members),
                     title=' · '.join(titles), recipe_reference=next(iter(refs)) if len(refs) == 1 else None,
                     recipe_references=sorted(refs),
                     status=next(iter(states)) if len(states) == 1 else 'partial',
                     details={**entry['details'], 'targets': list(targets.values())},
                     result_links=list(unique_links.values()))
        # A staged plate and its grouped observation batches share one UUID.
        # Keep the detailed group once, carrying the parent's river/stage links.
        for existing in standalone:
            if existing['id'] == parent:
                entry.update({key: existing[key] for key in ('river_url', 'stage') if key in existing})
        standalone = [existing for existing in standalone if existing['id'] != parent]
        standalone.append(entry)
    return standalone


def completed_target(row):
    return row.get('status') == 'success' and row.get('retention_status') not in ('failed', 'error')


def activity_summary(run, results=()):
    """Bounded human-summary projection of saved run/known result evidence."""
    targets = run.get('targets') or []
    good = sum(completed_target(row) for row in targets)
    issues = []
    by_host = {row.get('host_id'): row for row in results}
    for row in targets:
        if completed_target(row):
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
