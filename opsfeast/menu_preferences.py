"""Profile-local recipe categorization and reusable plate definitions 0.1.0.

Presentation/selection metadata only; never recipe options or execution authority.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from . import ConfigError
from .core import Instance
from .identity import _locked
from .site import SiteConflict, _atomic

VERSION='0.1.0'
FILENAME='recipe-menu.json'
BUILTIN={'hardware','storage','software','network','workloads','identity','observability','analysis','reports','custom'}
BUILTIN_TITLES={'硬體與環境','儲存與檔案系統','作業系統與軟體','網路與通訊','服務與工作負載','身分與存取','日誌與監控','基準與異常分析','報告與成果','其他／未分類'}


class MenuError(ConfigError):
    """Fixed safe reason; no private source/credential exception strings."""


def text(value,limit=120):
    if not isinstance(value,str) or not value.strip() or value!=value.strip() or len(value)>limit or any(ord(c)<32 for c in value):
        raise MenuError('invalid_menu_text')
    try:value.encode('utf-8')
    except UnicodeError:raise MenuError('invalid_menu_text') from None
    return value


def references(values):
    from recipe_settings import reference
    if not isinstance(values,list) or len(values)>100 or len(set(v for v in values if isinstance(v,str)))!=len(values):
        raise MenuError('invalid_recipe_references')
    try:
        if any(not isinstance(v,str) or reference(v)!=v for v in values):raise ValueError()
    except (ConfigError,ValueError):raise MenuError('exact_recipe_references_required') from None
    return values


def _validate(data):
    if not isinstance(data,dict) or set(data)!={'schema_version','categories','assignments','sets'} or data['schema_version']!=VERSION:
        raise MenuError('invalid_menu_preferences')
    if not isinstance(data['categories'],list) or len(data['categories'])>64 or not isinstance(data['assignments'],dict) or len(data['assignments'])>1000 or not isinstance(data['sets'],list) or len(data['sets'])>100:
        raise MenuError('menu_preferences_limit')
    ids=set(BUILTIN);titles=set()
    for category in data['categories']:
        if not isinstance(category,dict) or set(category)!={'id','title','description'}:raise MenuError('invalid_category')
        identifier=text(category['id']);title=text(category['title'])
        if not identifier.startswith('user-') or identifier in ids or title.casefold() in titles:raise MenuError('duplicate_category')
        ids.add(identifier);titles.add(title.casefold())
        if not isinstance(category['description'],str) or len(category['description'])>2000:raise MenuError('invalid_category_description')
    for ref,assigned in data['assignments'].items():
        references([ref])
        if ':' not in ref or ref.startswith('bundle:') or not isinstance(assigned,list) or len(assigned)>len(ids) or any(not isinstance(i,str) or i not in ids for i in assigned) or len(set(assigned))!=len(assigned):
            raise MenuError('invalid_category_assignment')
    seen=set()
    for saved in data['sets']:
        if not isinstance(saved,dict) or set(saved)-{'selections'}!={'id','title','description','recipes','hosts'}:raise MenuError('invalid_user_set')
        if text(saved['id']) in seen:raise MenuError('duplicate_user_set')
        seen.add(saved['id']);text(saved['title'])
        if not isinstance(saved['description'],str) or len(saved['description'])>2000:raise MenuError('invalid_set_description')
        references(saved['recipes'])
        if not saved['recipes']:raise MenuError('user_set_requires_recipes')
        selections=saved.get('selections',{})
        if not isinstance(selections,dict) or set(selections)-set(saved['recipes']):raise MenuError('invalid_set_selections')
        for selection in selections.values():
            if not isinstance(selection,dict) or len(selection)!=1 or set(selection)-{'jobs','properties'}:raise MenuError('invalid_set_selections')
            values=next(iter(selection.values()))
            if not isinstance(values,list) or not values or len(values)>500 or any(not isinstance(v,str) or not v for v in values) or len(set(values))!=len(values):raise MenuError('invalid_set_selections')
        hosts=saved['hosts']
        if not isinstance(hosts,list) or len(hosts)>1000 or any(not isinstance(h,str) or not h for h in hosts) or len(set(hosts))!=len(hosts):raise MenuError('invalid_set_hosts')
    try:json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,UnicodeError):raise MenuError('invalid_menu_text') from None
    return data


def _read(profile):
    path=profile.root/FILENAME
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_size>1024*1024)):
        raise MenuError('invalid_menu_preferences_file')
    raw=path.read_bytes() if path.exists() else b''
    try:data=json.loads(raw) if raw else {'schema_version':VERSION,'categories':[],'assignments':{},'sets':[]}
    except (ValueError,UnicodeError):raise MenuError('invalid_menu_preferences_file') from None
    revision=hashlib.sha256(str(profile.root).encode()+b'\0'+raw).hexdigest()
    return _validate(data),revision,raw


def inspect(profile):
    data,revision,_=_read(profile)
    return {**deepcopy(data),'revision':revision,'profile':profile.name,
            'scope_id':hashlib.sha256(str(profile.root).encode()).hexdigest()}


def mutate(product,*,profile,expected_revision,action,changes):
    if not isinstance(changes,dict):raise MenuError('menu_changes_object_required')
    with _locked(Path(product)/'.opsfeast-profiles.json'):
        selected=Instance.open(product).profile(profile)
        with _locked(selected.root/FILENAME):
            data,revision,raw=_read(selected)
            if revision!=expected_revision:raise SiteConflict('menu preferences changed; reload')
            if action in ('category.create','category.update'):
                allowed={'title','description'}|({'id'} if action.endswith('update') else set())
                if set(changes)!=allowed:raise MenuError('invalid_category_fields')
                title=text(changes['title']);identifier=changes.get('id')
                if title in BUILTIN_TITLES:raise MenuError('category_title_reserved_for_bundle')
                if any(c['title'].casefold()==title.casefold() and c['id']!=identifier for c in data['categories']):raise MenuError('duplicate_category')
                if action.endswith('create'):
                    identifier='user-'+str(uuid4());data['categories'].append({'id':identifier,'title':title,'description':changes['description']})
                else:
                    target=next((c for c in data['categories'] if c['id']==identifier),None)
                    if target is None:raise MenuError('user_category_not_found')
                    target.update(title=title,description=changes['description'])
            elif action=='recipe.categories':
                if set(changes)!={'reference','categories'}:raise MenuError('invalid_assignment_fields')
                references([changes['reference']])
                from recipe_catalog import choose
                item=choose(selected.root,changes['reference'])
                if item['reference']!=changes['reference'] or not item.get('source') or item.get('source')=='repository' or ':' not in changes['reference']:raise MenuError('only_user_recipe_categories_are_editable')
                if changes['categories'] is None:data['assignments'].pop(item['reference'],None)
                else:data['assignments'][item['reference']]=changes['categories']
            elif action in ('set.create','set.update'):
                allowed={'title','description','recipes','hosts'}|({'id'} if action.endswith('update') else set())
                if set(changes)-{'selections'}!=allowed:raise MenuError('invalid_set_fields')
                references(changes['recipes'])
                from recipe_catalog import catalog
                available={r['reference']:r for r in catalog(selected.root)['recipes'] if r['runnable']}
                if any(ref not in available for ref in changes['recipes']):raise MenuError('set_contains_unavailable_recipes')
                from .recipe_runs import inventory_selection
                if not isinstance(changes.get('selections',{}),dict) or set(changes.get('selections',{}))-set(changes['recipes']):raise MenuError('invalid_set_selections')
                for ref,selection in changes.get('selections',{}).items():
                    if selection is None:raise MenuError('invalid_set_selections')
                    item=available[ref];inventory_selection(item['descriptor'],Path(item['directory']),selection)
                known_hosts=set(selected.hosts.list())
                if not isinstance(changes['hosts'],list) or any(not isinstance(h,str) or h not in known_hosts for h in changes['hosts']):raise MenuError('set_contains_unknown_hosts')
                if action.endswith('create'):data['sets'].append({'id':str(uuid4()),**changes})
                else:
                    target=next((s for s in data['sets'] if s['id']==changes['id']),None)
                    if target is None:raise MenuError('user_set_not_found')
                    target.update(changes)
            elif action=='set.delete':
                if set(changes)!={'id'} or not any(s['id']==changes['id'] for s in data['sets']):raise MenuError('user_set_not_found')
                data['sets']=[s for s in data['sets'] if s['id']!=changes['id']]
            else:raise MenuError('invalid_menu_action')
            _validate(data)
            encoded=(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            if len(encoded)>1024*1024:raise MenuError('menu_preferences_limit')
            backups=selected.root/'.recipe-menu-backups'
            if backups.is_symlink() or (backups.exists() and not backups.is_dir()):raise MenuError('invalid_menu_backup_directory')
            if raw:
                backups.mkdir(mode=0o700,exist_ok=True)
                _atomic(backups/(str(uuid4())+'.json'),raw)
            # Preserve non-cooperating edits observed during validation.
            if _read(selected)[1]!=revision:raise SiteConflict('menu preferences changed while saving')
            _atomic(selected.root/FILENAME,encoded)
            return inspect(selected)
