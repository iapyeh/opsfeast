"""Read-only Web views of existing catalogs, services and saved evidence."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from fastapi import HTTPException, Query, Request

from opsfeast import ConfigError
from opsfeast.core import Instance


def document_files(product):
    """Only bundled Markdown guides; never mount the repository or profile root."""
    paths = [product / 'README.md']
    for directory in ('docs', 'skills', 'recipes'):
        paths.extend((product / directory).rglob('*.md'))
    return {path.relative_to(product).as_posix(): path for path in paths
            if path.is_file() and not any(part.is_symlink() for part in (path, *path.parents))
            and path.resolve().is_relative_to(product.resolve())}


def page(items, offset, limit):
    return {'items': items[offset:offset + limit], 'total': len(items),
            'next_offset': offset + limit if len(items) > offset + limit else None}


def install(app, *, product, require_admin):
    @app.get('/api/v1/profiling/catalog')
    def profiling_catalog(request: Request, domain: str | None = None):
        require_admin(request)
        from opsfeast.profiling import catalog
        try:
            return catalog(domain=domain)
        except OSError:
            raise HTTPException(503, 'profiling_storage_unavailable') from None

    @app.get('/api/v1/profiling/host')
    def profiling_host(request: Request, host_id: str, profile: str | None = None,
                       domain: str | None = None, offset: int = Query(0, ge=0),
                       limit: int = Query(100, ge=1, le=250)):
        require_admin(request)
        from opsfeast.profiling import inspect_host
        selected = Instance.open(product).profile(profile)
        try:
            return inspect_host(selected, host_id, domain=domain, offset=offset, limit=limit)
        except (OSError, sqlite3.Error):
            raise HTTPException(503, 'profiling_storage_unavailable') from None

    @app.get('/api/v1/results/latest')
    def latest_result(request: Request, host_id: str, profile: str | None = None):
        require_admin(request)
        selected = Instance.open(product).profile(profile)
        selected.hosts.get(host_id)
        from recipe_reports import results
        listing = results(selected.root, host=host_id, kind='operation')
        rows = [row for row in listing['results'] if row['recipe_reference'] == 'system/inventory/overview']
        rows.sort(key=lambda row: row.get('started_at') or '', reverse=True)
        return {'profile': selected.name, 'host_id': host_id,
                'result': {key: rows[0].get(key) for key in ('result_id','short_id','status','started_at')} if rows else None,
                'invalid_result_count': len(listing['errors'])}

    @app.get('/api/v1/results/diagnosis')
    def diagnosis(request: Request, result_id: str, profile: str | None = None,
                  limit: int = Query(5, ge=1, le=50), sample_offset: int = Query(0, ge=0)):
        require_admin(request)
        selected = Instance.open(product).profile(profile)
        from result_diagnostics import diagnose
        try: return {'profile': selected.name, **diagnose(selected.root, result_id, limit=limit, kind='operation', sample_offset=sample_offset)}
        except (OSError, sqlite3.Error): raise HTTPException(503, 'result_diagnosis_unavailable') from None

    @app.get('/api/v1/library')
    def library(kind: str = 'docs'):
        if kind not in ('docs', 'learn', 'skills'):
            raise HTTPException(422, 'invalid_library_kind')
        def selected(name):
            if kind == 'learn': return name.startswith('docs/textbook/')
            if kind == 'skills': return name.startswith('skills/')
            return name == 'README.md' or name.startswith('recipes/') or (name.startswith('docs/') and not name.startswith('docs/textbook/'))
        return {'items': [{'path': name, 'title': path.stem} for name, path in sorted(document_files(product).items()) if selected(name)]}

    @app.get('/api/v1/library/content')
    def document(path: str):
        target = document_files(product).get(path)
        if target is None:
            raise HTTPException(404, 'document_not_found')
        if target.stat().st_size > 2 * 1024 * 1024:
            raise HTTPException(413, 'document_too_large')
        return {'path': path, 'content': target.read_text(encoding='utf-8')}

    @app.get('/api/v1/workspace/{section}')
    def read_section(section: str, request: Request, profile: str | None = None,
                     item_id: str | None = None, host_id: str | None = None,
                     q: str = Query('', max_length=1000), kind: str | None = None,
                     scope: str = 'all',
                     offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=250)):
        require_admin(request)
        if section not in ('summary', 'recipes', 'work', 'retention', 'logs'):
            raise HTTPException(404, 'workspace_section_not_found')
        if scope not in ('all', 'bundle', 'user'):
            raise HTTPException(422, 'invalid_recipe_scope')
        if host_id is not None and (section != 'logs' or item_id is None):
            raise HTTPException(422, 'host_filter_requires_activity_entry')
        instance = Instance.open(product)
        selected = None if section == 'recipes' and scope == 'bundle' else instance.profile(profile)
        if kind not in (None, 'notification', 'todo'):
            raise HTTPException(422, 'invalid_workspace_kind')
        def selected_page(items):
            needle = q.strip().casefold()
            if needle:
                fields = ('reference', 'title', 'description', 'host_id', 'recipe_reference', 'recipe_references', 'kind', 'status', 'source', 'body', 'time', 'observed_at')
                items = [item for item in items if any(needle in str(item.get(key, '')).casefold() for key in fields)]
            return page(items, offset, limit)
        result = {'schema_version': '0.1.0', 'profile': selected.name if selected else None,
                  'read_at': datetime.now(timezone.utc).isoformat(), 'status': 'success'}
        try:
            if section == 'recipes':
                from recipe_catalog import catalog
                data = catalog(selected.root if selected else None)
                fields = ('reference', 'source', 'id', 'version', 'title', 'description', 'kind', 'contract',
                          'status', 'errors', 'runnable', 'inputs', 'dependencies', 'verification',
                          'availability_evidence', 'author', 'license')
                items = [{key: item.get(key) for key in fields} for item in data['recipes']]
                sources = data['sources']
                status = data['status']
                if scope == 'user':
                    items = [item for item in items if item['source'] != 'repository']
                    sources = [item for item in sources if item['name'] != 'repository']
                    status = 'failed' if any(item['status'] == 'failed' for item in items) or any(item['status'] == 'unavailable' for item in sources) else 'success'
                items.sort(key=lambda item: (item['source'] == 'repository', item['reference']))
                if item_id is not None: items = [item for item in items if item['reference'] == item_id]
                result.update(selected_page(items), status=status,
                              sources=[{key: source[key] for key in ('name', 'enabled', 'status', 'errors')} for source in sources])
            elif section == 'work':
                items = [*selected.services.notifications.list(), *selected.services.todos.list()]
                if kind is not None: items = [item for item in items if item['kind'] == kind]
                items.sort(key=lambda item: (item.get('updated_at', ''), item['id']), reverse=True)
                result.update(selected_page(items))
            elif section == 'summary':
                result['host_count'] = len(selected.hosts.list())
                result['components'] = {}
                for name, read in (
                    ('notifications', lambda: selected.services.notifications.list(status='active')),
                    ('todos', lambda: [item for item in selected.services.todos.list() if item['status'] in ('open', 'in_progress', 'blocked')]),
                ):
                    try:
                        items = read()
                        items.sort(key=lambda item: item.get('updated_at', ''), reverse=True)
                        result['components'][name] = {'status': 'success', **page(items, 0, 5)}
                    except (ConfigError, OSError, sqlite3.Error):
                        result['status'] = 'partial'
                        result['components'][name] = {'status': 'unavailable'}
            elif section == 'retention':
                records = selected.retention.query()['records']
                items = [{'record_id': item['record_id'], 'host_id': item['host_id'],
                          'recipe_reference': item['recipe_reference'], 'observed_at': item['observed_at'],
                          'kind': item['kind'], 'status': item['data'].get('status', 'unknown'),
                          'retention_definition': item.get('retention_definition')} for item in records]
                items.sort(key=lambda item: (item['observed_at'], item['record_id']), reverse=True)
                result.update(selected_page(items))
            elif section == 'logs':
                items, errors, saved, labels = [], [], {'results': [], 'errors': []}, {}
                try:
                    from recipe_reports import results
                    saved = results(selected.root, kind='operation', collapse_successful_wrappers=True) if item_id is not None else {'results': [], 'errors': []}
                    if saved['errors']: errors.append('some_saved_results_invalid')
                    from opsfeast.recipe_activity import history_labels
                    titles, labels = history_labels(selected, app.state.recipe_runs)
                    for run in selected.retention.runs():
                        reference = run['recipe_reference']
                        naming = labels.get(run['run_id'], {'title': titles.get(reference, reference), 'recipe_title': titles.get(reference, reference), 'meal_titles': []})
                        items.append({'id': run['run_id'], 'source': 'recipe', 'time': run['started_at'],
                                      **naming, 'recipe_reference': reference, 'status': run['status'], 'details': run,
                                      'results_loaded': item_id is not None, 'result_links':[{key: row[key] for key in ('host_id','status','result_id','short_id')}
                                                      for row in saved['results'] if row.get('observation_run_id') == run['run_id']]})
                except (ConfigError, OSError, sqlite3.Error):
                    errors.append('recipe_history_unavailable')
                observations = {item['id']: item for item in items}
                staged_ids, covered_observations, rivers_by_observation = set(), set(), {}
                try:
                    from opsfeast.staged_execution import Executions
                    store = Executions(selected.root, installation=product)
                    executions = store.list()
                    staged_ids = {entry['id'] for entry in executions}
                    for entry in executions:
                        active = entry['completed_at'] is None
                        river = '/console/' + entry['id'] + ('' if active else '/history')
                        stage = entry['stages'][entry['cursor']] if active else None
                        observation_ids = {s['observation_run_id'] for s in entry['stages'] if s.get('observation_run_id')}
                        for observation_id in observation_ids:
                            for host in entry['hosts']:
                                rivers_by_observation[(observation_id, entry['reference'], host)] = river
                        belongs_to_web = any(observations.get(observation_id, {}).get('web_run_id')
                                             for observation_id in observation_ids)
                        if (belongs_to_web and entry['id'] != item_id) or (host_id is not None and host_id not in entry['hosts']):
                            continue
                        for observation_id in observation_ids:
                            observation = observations.get(observation_id)
                            if (observation and observation_id != item_id
                                    and observation['recipe_reference'] == entry['reference']
                                    and {target['host_id'] for target in observation['details'].get('targets', [])}
                                    == set(entry['hosts'])):
                                covered_observations.add(observation_id)
                        result_links = [{key: row[key] for key in ('host_id','status','result_id','short_id')}
                                        for row in saved.get('results', [])
                                        if row.get('observation_run_id') in observation_ids
                                        and row.get('recipe_reference') == entry['reference']
                                        and row['host_id'] in entry['hosts']
                                        and (host_id is None or row['host_id'] == host_id)]
                        items.append({'id': entry['id'], 'source': 'recipe',
                                      'time': entry['started_at'], 'title': entry['title'],
                                      'recipe_reference': entry['reference'], 'status': entry['status'],
                                      'stage': {k: stage.get(k) for k in ('id', 'executor', 'awaiting_human')} if stage else None,
                                      'river_url': river, 'result_links': result_links,
                                      'results_loaded': item_id is not None})
                except (ConfigError, OSError, ValueError):
                    errors.append('staged_recipe_history_unavailable')
                items = [item for item in items if item['id'] not in covered_observations]
                for item in items:
                    if not item.get('web_run_id'):
                        continue
                    for row in item['result_links']:
                        river = rivers_by_observation.get((item['id'], item['recipe_reference'], row['host_id']))
                        if river:
                            row['river_url'] = river
                from opsfeast.recipe_activity import group_web_activity
                items = group_web_activity(items, item_id)
                sessions = {}
                hosts = [] if item_id is not None and any(item['id'] == item_id for item in items) else selected.hosts.list()
                for host in hosts:
                    cursor = None
                    while True:
                        data = app.state.console_records.list_sessions(selected.name + ' / ' + host, limit=100, before=cursor)
                        for item in data['sessions']: sessions[item['session_id']] = item
                        cursor = data['next_cursor']
                        if cursor is None: break
                for item in sessions.values():
                    if item['session_id'] in staged_ids:
                        continue
                    items.append({'id': item['session_id'], 'source': 'console', 'time': item['created_at'],
                                  'title': item['title'], 'status': item.get('block_states', {}),
                                  'url': '/console/' + item['session_id'] + '/history', 'details': item})
                items.sort(key=lambda item: (item['time'], item['id']), reverse=True)
                if item_id is not None: items = [item for item in items if item['id'] == item_id]
                selected_items = selected_page(items)
                from opsfeast.recipe_activity import activity_summary
                from recipe_reports import show_result
                for entry in selected_items['items']:
                    if entry['source'] != 'recipe' or entry.get('river_url'):
                        continue
                    raw_results = []
                    if host_id is not None:
                        entry['details'] = {**entry['details'], 'targets': [row for row in entry['details'].get('targets', []) if row.get('host_id') == host_id]}
                        entry['result_links'] = [row for row in entry['result_links'] if row['host_id'] == host_id]
                    bad_hosts = {row.get('host_id') for row in entry['details'].get('targets', []) if row.get('status') != 'success' or row.get('retention_status') in ('failed', 'error')}
                    detail_candidates = [link for link in entry['result_links'] if link['host_id'] in bad_hosts or link['status'] != 'success']
                    if item_id is not None:
                        for link in detail_candidates[:6]:
                            try:
                                raw_results.append({'result_id': link['result_id'], 'host_id': link['host_id'],
                                                    'raw': show_result(selected.root, link['result_id'], kind='operation')})
                            except (ConfigError, OSError, ValueError):
                                errors.append('some_result_details_unavailable')
                    entry['summary'] = activity_summary(entry['details'], raw_results)
                    entry['summary']['omitted_result_details'] = max(0, len(detail_candidates) - 6) if item_id is not None else 0
                    entry['expanded'] = item_id is not None
                result.update(selected_items, errors=sorted(set(errors)), status='partial' if errors else 'success')
        except (OSError, sqlite3.Error):
            raise HTTPException(503, 'workspace_storage_unavailable') from None
        return result
