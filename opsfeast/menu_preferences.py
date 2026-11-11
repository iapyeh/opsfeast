"""Profile-local recipe categorization and reusable plate definitions 0.2.0.

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

VERSION='0.2.0'
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
        if not isinstance(saved,dict) or set(saved)!={'id','title','description','recipes','meals','selections'}:raise MenuError('invalid_user_set')
        identifier=text(saved['id'])
        if identifier.startswith('bundle:') or identifier in seen:raise MenuError('duplicate_user_set')
        seen.add(identifier);text(saved['title'])
        if not isinstance(saved['description'],str) or len(saved['description'])>2000:raise MenuError('invalid_set_description')
        references(saved['recipes'])
        meal_ids(saved['meals'])
        selections=saved['selections']
        if not isinstance(selections,dict) or set(selections)-set(saved['recipes']):raise MenuError('invalid_set_selections')
        for selection in selections.values():
            if not isinstance(selection,dict) or len(selection)!=1 or set(selection)-{'jobs','properties'}:raise MenuError('invalid_set_selections')
            values=next(iter(selection.values()))
            if not isinstance(values,list) or not values or len(values)>500 or any(not isinstance(v,str) or not v for v in values) or len(set(values))!=len(values):raise MenuError('invalid_set_selections')
    validate_graph(data['sets'])
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
            elif action=='set.create':
                if set(changes)!={'title','description','recipes','meals','selections'}:raise MenuError('invalid_set_fields')
                references(changes['recipes']);meal_ids(changes['meals'])
                if not changes['recipes'] and not changes['meals']:raise MenuError('user_set_requires_members')
                from recipe_catalog import catalog
                available={r['reference']:r for r in catalog(selected.root)['recipes'] if r['runnable']}
                if any(ref not in available for ref in changes['recipes']):raise MenuError('set_contains_unavailable_recipes')
                if not isinstance(changes['selections'],dict) or set(changes['selections'])-set(changes['recipes']):raise MenuError('invalid_set_selections')
                from .recipe_runs import inventory_selection
                for ref,selection in changes['selections'].items():
                    if selection is None:raise MenuError('invalid_set_selections')
                    item=available[ref];inventory_selection(item['descriptor'],Path(item['directory']),selection)
                data['sets'].append({'id':str(uuid4()),**changes})
            elif action=='set.delete':
                if set(changes)!={'id'} or not any(s['id']==changes['id'] for s in data['sets']):raise MenuError('user_set_not_found')
                data['sets']=[s for s in data['sets'] if s['id']!=changes['id']]
                for saved in data['sets']:
                    saved['meals']=[identifier for identifier in saved['meals'] if identifier!=changes['id']]
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


def meal_ids(values):
    if not isinstance(values,list) or len(values)>100 or any(not isinstance(v,str) or not v for v in values) or len(set(values))!=len(values):
        raise MenuError('invalid_meal_references')


def meal_catalog(user_sets):
    from .recipe_menu import bundle_sets
    return {s['id']:s for s in [*bundle_sets(),*user_sets]}


def validate_graph(user_sets):
    catalog=meal_catalog(user_sets)
    visiting=set();done=set()
    def visit(identifier):
        if identifier in visiting:raise MenuError('cyclic_meal_reference')
        if identifier not in catalog:raise MenuError('unknown_meal_reference')
        if identifier in done:return
        visiting.add(identifier)
        for child in catalog[identifier]['meals']:visit(child)
        visiting.remove(identifier);done.add(identifier)
    for identifier in catalog:visit(identifier)


def expand(profile, recipes, meals):
    """Resolve current meal references and union scopes; no execution or writes."""
    meal_ids(meals)
    saved=inspect(profile);validate_graph(saved['sets']);catalog=meal_catalog(saved['sets'])
    from recipe_catalog import choose
    from .recipe_runs import inventory_selection
    choices={};items={}
    def add(choice):
        ref=choice['reference']
        if ref not in choices and len(choices)>=32:raise MenuError('too_many_expanded_recipes')
        if ref not in items:items[ref]=choose(profile.root,ref)
        item=items[ref]
        if item['reference']!=ref or not item['runnable']:raise MenuError('exact_runnable_reference_required')
        scope=inventory_selection(item['descriptor'],Path(item['directory']),choice.get('inventory_selection'))
        incoming=deepcopy(choice)
        if scope is not None:incoming['inventory_selection']={'properties':scope['properties']}
        if ref in choices:
            old=choices[ref]
            if old['vars']!=incoming['vars'] or old['inputs']!=incoming['inputs']:raise MenuError('conflicting_recipe_options')
            if scope is not None:
                old['inventory_selection']['properties']=sorted(set(old['inventory_selection']['properties'])|set(scope['properties']))
        else:choices[ref]=incoming
    visited=set()
    def visit(identifier):
        if identifier not in catalog:raise MenuError('unknown_meal_reference')
        if identifier in visited:return
        visited.add(identifier);meal=catalog[identifier]
        for ref in meal['recipes']:
            add({'reference':ref,'vars':{},'inputs':[],**({'inventory_selection':meal['selections'][ref]} if ref in meal['selections'] else {})})
        for child in meal['meals']:visit(child)
    for choice in recipes:add(choice)
    for identifier in meals:visit(identifier)
    if not choices:raise MenuError('empty_meal_selection')
    if len(choices)>32:raise MenuError('too_many_expanded_recipes')
    binding=hashlib.sha256(json.dumps({'revision':saved['revision'],'meals':catalog},sort_keys=True).encode()).hexdigest()
    return list(choices.values()),binding
