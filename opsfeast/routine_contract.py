"""Static, explicit Python routine/meal contracts 0.1.0; no candidate imports."""
from dataclasses import dataclass
from pathlib import Path
import ast
import json
import re
from . import ConfigError, mapping, plain_values

VERSION='0.1.0'
ROUTINES='python-routines'
MEAL='recipe-meal'

@dataclass(frozen=True)
class RoutineSpec:
    id: str
    function: str
    required_permission: str
    depends_on: tuple
    properties: tuple
    platforms: tuple


def validate(directory,metadata):
    from .recipe_launch import describe as launch
    launch(metadata)
    try:return _validate(Path(directory),metadata)
    except ConfigError:raise
    except (ValueError,KeyError,TypeError,AttributeError,RecursionError):raise ConfigError('invalid routine or meal definition') from None


def _validate(directory,metadata):
    from recipe_identity import validate as identity
    from recipe_inputs import prepare_vars
    from recipe_dispatch import declared_version
    from retention_contracts import validate_declaration
    identity(metadata,directory);plain_values(metadata,'recipe definition')
    if metadata.get('descriptor_version')!='0.3.0' or metadata.get('access_mode')!='read':raise ConfigError('routine/meal requires descriptor 0.3.0 and read access')
    runner=metadata.get('runner',{})
    if runner.get('version')!=VERSION or runner.get('contract') not in (ROUTINES,MEAL):raise ConfigError('unsupported routine/meal contract')
    if not isinstance(metadata.get('id'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',metadata['id']):raise ConfigError('simple recipe ID required')
    output=mapping(metadata.get('output'),'recipe output',('schema_version',))
    if not isinstance(output.get('schema_version'),str) or not output['schema_version']:raise ConfigError('output schema version required')
    if not isinstance(metadata.get('version'),str) or not metadata['version']:raise ConfigError('recipe version required')
    definitions=metadata.get('inputs',{}).get('variables',{})
    for spec in definitions.values():
        if not isinstance(spec,dict) or type(spec.get('required',False)) is not bool:raise ConfigError('invalid input required flag')
    prepare_vars(dict(metadata,inputs={'variables':{n:dict(spec,required=False) for n,spec in definitions.items()}}),{},{})
    for helper in directory.rglob('*.py'):
        if helper.is_symlink() or not helper.resolve().is_relative_to(directory.resolve()):raise ConfigError('recipe helper escapes directory')
    if runner['contract']==MEAL:
        if set(runner)!={'contract','version','entrypoint'} or runner['entrypoint']!='meal.json':raise ConfigError('meal requires meal.json')
        path=directory/'meal.json'
        if path.is_symlink() or not path.is_file():raise ConfigError('meal definition missing or symlink')
        data=json.loads(path.read_text())
        if set(data)!={'schema_version','members'} or data['schema_version']!=VERSION or not isinstance(data['members'],list) or not 1<=len(data['members'])<=32:raise ConfigError('invalid meal definition')
        from recipe_settings import reference
        seen=set()
        for member in data['members']:
            if not isinstance(member,dict) or set(member)!={'reference','enabled'} or type(member['enabled']) is not bool or not isinstance(member['reference'],str) or reference(member['reference'])!=member['reference'] or member['reference'] in seen:raise ConfigError('invalid or duplicate meal member')
            seen.add(member['reference'])
        return data
    if set(runner)!={'contract','version','entrypoint','routines','finalizer'}:raise ConfigError('routine runner fields invalid')
    entry=directory/runner['entrypoint']
    if entry.is_symlink() or not entry.resolve().is_relative_to(directory.resolve()) or not entry.is_file() or entry.suffix!='.py':raise ConfigError('routine entrypoint escapes recipe')
    if declared_version(entry)!=metadata['version']:raise ConfigError('routine code version differs')
    tree=ast.parse(entry.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    values=runner['routines']
    if not isinstance(values,list) or not 1<=len(values)<=64:raise ConfigError('routine list required')
    specs=[];ids=set()
    for value in values:
        if not isinstance(value,dict) or set(value)!={'id','function','required_permission','depends_on','properties','platforms'}:raise ConfigError('routine fields invalid')
        identifier=value['id'];function=value['function']
        if not isinstance(identifier,str) or not re.fullmatch(r'[a-z][a-z0-9-]*',identifier) or identifier in ids or not isinstance(function,str) or function not in functions:raise ConfigError('routine ID/function invalid')
        if value['required_permission'] not in ('login','root'):raise ConfigError('routine permission must be login or root')
        for key in ('depends_on','properties','platforms'):
            if not isinstance(value[key],list) or any(not isinstance(v,str) or not v for v in value[key]) or len(set(value[key]))!=len(value[key]):raise ConfigError('routine lists must be unique strings')
        for previous in specs:
            if set(previous.properties).intersection(value['properties']) and (not previous.platforms or not value['platforms'] or set(previous.platforms).intersection(value['platforms'])):raise ConfigError('routine outputs overlap')
        ids.add(identifier)
        fn=functions[function]
        if len(fn.args.args)!=1 or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:raise ConfigError('routine function accepts exactly one Recipe')
        specs.append(RoutineSpec(identifier,function,value['required_permission'],tuple(value['depends_on']),tuple(value['properties']),tuple(value['platforms'])))
    finalizer=functions.get(runner['finalizer'])
    if finalizer is None or len(finalizer.args.args)!=1 or finalizer.args.vararg or finalizer.args.kwarg or finalizer.args.kwonlyargs:raise ConfigError('finalizer accepts routine result list')
    order(specs)
    definitions=metadata.get('inputs',{}).get('variables',{})
    prepare_vars(dict(metadata,inputs={'variables':{n:dict(s,required=False) for n,s in definitions.items()}}),{},{})
    declaration=validate_declaration(metadata,directory)
    if metadata.get('inventory'):
        if not declaration or declaration.get('contract')!='inventory-routine-observations':raise ConfigError('inventory routines require their data contract')
        from .routine_execution import collection
        collection(metadata)
    return tuple(specs)


def order(specs):
    """Stable dependency sort with login before root; reject contradictory phases."""
    known={s.id:s for s in specs};done=set();ordered=[]
    if any(d not in known or s.required_permission=='login' and known[d].required_permission=='root' for s in specs for d in s.depends_on):raise ConfigError('unknown dependency or login depends on root')
    for permission in ('login','root'):
        pending=[s for s in specs if s.required_permission==permission]
        while pending:
            ready=next((s for s in pending if set(s.depends_on)<=done),None)
            if ready is None:raise ConfigError('routine dependency cycle')
            pending.remove(ready);ordered.append(ready);done.add(ready.id)
    return tuple(ordered)
