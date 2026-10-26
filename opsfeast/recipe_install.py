"""Reviewed recipe installation plans, rollback copies and pinned execution trees."""
from contextlib import contextmanager
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from uuid import uuid4

from opsfeast import ConfigError, read_yaml
from .transfer import checked, relative, digest, canonical, atomic, locked


def exchange(left,right):
    """Atomic directory exchange on supported POSIX controllers; fail before mutation elsewhere."""
    import ctypes
    library=ctypes.CDLL(None,use_errno=True)
    name='renameatx_np' if sys.platform=='darwin' else 'renameat2' if sys.platform.startswith('linux') else None
    function=getattr(library,name,None) if name else None
    if function is None:raise ConfigError('atomic recipe replacement unavailable on this controller')
    function.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    function.restype=ctypes.c_int
    current=-2 if sys.platform=='darwin' else -100
    if function(current,os.fsencode(left),current,os.fsencode(right),2)!=0:
        code=ctypes.get_errno();raise OSError(code,os.strerror(code))


def tree(directory):
    directory=Path(directory)
    if not directory.exists():return {}
    if directory.is_symlink() or not directory.is_dir():raise ConfigError('recipe destination is not an ordinary directory')
    files={}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():raise ConfigError('recipe tree contains a symlink')
        if path.is_file() and '__pycache__' not in path.parts:
            name=path.relative_to(directory).as_posix()
            relative(name)
            files[name]=path.read_bytes()
    return files


def fingerprint(directory):
    return digest({name:{'sha256':digest(value),'executable':bool((Path(directory)/name).stat().st_mode & 0o111)} for name,value in tree(directory).items()})


def requirements(metadata):
    from recipe_dispatch import version_match
    declaration=metadata.get('portability',{})
    if not isinstance(declaration,dict) or set(declaration)-{'api','python','distributions','services','features'}:
        raise ConfigError('invalid recipe portability requirements')
    for key in ('distributions','services','features'):
        if not isinstance(declaration.get(key,{}),dict) or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in declaration.get(key,{}).items()):
            raise ConfigError('invalid recipe portability dependency mapping')
    statuses=[]
    if declaration.get('api','0.1.0')!='0.1.0':statuses.append({'dependency':'opsfeast-api','status':'missing'})
    if not version_match('.'.join(map(str,sys.version_info[:3])),declaration.get('python','>=3.11')):
        statuses.append({'dependency':'python','status':'missing'})
    for name,condition in declaration.get('distributions',{}).items():
        try:version=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:version=None
        statuses.append({'dependency':name,'required':condition,'installed':version,
                         'status':'available' if version_match(version,condition) else 'missing'})
    for name,version in declaration.get('services',{}).items():
        statuses.append({'dependency':'service:'+name,'required':version,
            'status':'available' if name in ('notifications','todos') and version=='0.1.0' else 'missing'})
    from opsfeast.recipe_assessment import VERSION as assessment_version
    from opsfeast.recipe_execution import VERSION as execution_version
    features = {'recipe-assessment': assessment_version, 'recipe-execution': execution_version, 'portable-retention': '0.1.0'}
    for name, version in declaration.get('features', {}).items():
        statuses.append({'dependency':'feature:'+name, 'required':version,
                         'status':'available' if features.get(name)==version else 'missing'})
    return statuses


@contextmanager
def candidate(package):
    from recipe_packages import unpack
    with tempfile.TemporaryDirectory(prefix='opsfeast-recipe-candidate-') as temp:
        result=unpack(Path(package),Path(temp)/'candidate')
        path=Path(result['recipe_directory'])
        from recipe_inspection import inspect_one
        inspection=inspect_one(path,[])
        if inspection['status']!='success':raise ConfigError('candidate failed static recipe validation: '+canonical(inspection['errors']))
        yield path,read_yaml(path/'recipe.yaml')


def plan(root,package,path,*,resolution='conflict'):
    if resolution not in ('conflict','replace','skip'):raise ConfigError('invalid recipe conflict resolution')
    relative(path)
    destination=checked(root,'recipes/'+path)
    with candidate(package) as (source,metadata):
        incoming=fingerprint(source);previous=fingerprint(destination) if destination.exists() else None
        action='add' if previous is None else 'skip' if previous==incoming else resolution
        existing=read_yaml(destination/'recipe.yaml') if destination.exists() else None
        result={'version':'0.1.0','operation':'recipe-install','path':path,'destination':str(destination),
                'package_sha256':digest(Path(package).read_bytes()),'before':previous,'after':incoming,
                'action':action,'different_recipe':bool(existing and existing.get('id')!=metadata['id']),
                'requirements':requirements(metadata),'recipe_id':metadata['id'],'recipe_version':metadata['version'],
                'effects':['Install reviewed code only; no execution or consumer activation.',
                          'Existing exact-reference configuration is preserved; review changed inputs/contracts.',
                          'A new path does not rewrite jobs, subscriptions or historical references.']}
        if existing:
            result['descriptor_before']=existing
        result['descriptor_after']=metadata
        result['sha256']=digest(result)
        return result


def install(root,package,path,*,resolution='conflict',expected_plan=None):
    with locked(root):
        selected=plan(root,package,path,resolution=resolution)
        if expected_plan is None or selected['sha256']!=expected_plan:raise ConfigError('recipe install requires the current reviewed plan digest')
        if selected['action']=='conflict':raise ConfigError('recipe path conflict requires replace, skip, or a different path')
        if any(r['status']=='missing' for r in selected['requirements']):raise ConfigError('recipe dependencies unavailable; no automatic installation')
        if selected['action']=='skip':return {'status':'success','action':'skip','plan':selected}
        destination=Path(selected['destination']);destination.parent.mkdir(parents=True,exist_ok=True)
        with candidate(package) as (source,metadata):
            if fingerprint(source)!=selected['after'] or digest(Path(package).read_bytes())!=selected['package_sha256']:
                raise ConfigError('recipe package changed during installation')
            staging=destination.parent/('.recipe-stage-'+str(uuid4()))
            shutil.copytree(source,staging)
            backup=checked(root,'transfer/recipes/'+str(uuid4()))
            journal={'status':'prepared','plan':selected,'backup':str(backup),'staging':str(staging),'id':backup.name}
            receipt=checked(root,'transfer/recipe-installs/'+backup.name+'.json');atomic(receipt,journal)
            try:
                if selected['before'] is not None:
                    backup.parent.mkdir(parents=True,exist_ok=True)
                    exchange(staging,destination)
                    # After exchange staging contains the old generation, even after a crash.
                    os.rename(staging,backup)
                else:
                    os.rename(staging,destination)
                journal['status']='completed';atomic(receipt,journal)
            except BaseException:
                journal['status']='recoverable';atomic(receipt,journal)
                raise
        return {'status':'success','action':selected['action'],'plan':selected,'receipt':str(receipt),
                'rollback_copy':str(backup) if backup.exists() else None}


@contextmanager
def execution_snapshot(root,directory):
    """Copy every reviewed byte while installation is excluded, then release the lock."""
    with tempfile.TemporaryDirectory(prefix='opsfeast-recipe-execution-') as temp:
        with locked(root):
            files=tree(directory)
            if 'recipe.yaml' not in files:raise ConfigError('execution recipe is missing')
            for name,data in files.items():
                path=Path(temp)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                path.chmod(0o755 if (Path(directory)/name).stat().st_mode & 0o111 else 0o644)
        yield Path(temp)


def rollback_plan(root,receipt_id):
    from uuid import UUID
    from .transfer import document
    UUID(receipt_id)
    receipt_path=checked(root,'transfer/recipe-installs/'+receipt_id+'.json')
    receipt=document(receipt_path.read_bytes());selected=receipt['plan']
    destination=checked(root,'recipes/'+selected['path'])
    backup=checked(root,'transfer/recipes/'+receipt_id)
    staging=checked(root,Path(receipt['staging']).relative_to(Path(root).resolve()).as_posix())
    if not backup.exists() and staging.exists() and fingerprint(staging)==selected['before']:
        backup=staging
    actual=fingerprint(destination) if destination.exists() else None
    saved=fingerprint(backup) if backup.exists() else None
    allowed=(actual in (None,selected['after'],selected['before']) and saved in (None,selected['before'])
             and (selected['before'] is None or saved==selected['before'] or actual==selected['before']))
    result={'operation':'recipe-rollback','id':receipt_id,'destination':str(destination),'backup':str(backup),
            'before':actual,'saved':saved,'target':selected['before'],'allowed':allowed,'receipt_status':receipt['status']}
    result['sha256']=digest(result)
    return result


def rollback(root,receipt_id,*,expected_plan=None):
    from .transfer import document
    with locked(root):
        selected=rollback_plan(root,receipt_id)
        if expected_plan is None or expected_plan!=selected['sha256'] or not selected['allowed']:
            raise ConfigError('rollback requires current reviewed plan and unchanged installed/backup trees')
        receipt_path=checked(root,'transfer/recipe-installs/'+receipt_id+'.json');receipt=document(receipt_path.read_bytes())
        destination=Path(selected['destination']);backup=Path(selected['backup'])
        if selected['before']!=selected['target']:
            if destination.exists():
                displaced=checked(root,'transfer/recipes/'+str(uuid4()))
                displaced.parent.mkdir(parents=True,exist_ok=True)
                if backup.exists():
                    exchange(backup,destination)
                    os.rename(backup,displaced)
                else:os.rename(destination,displaced)
                receipt['displaced']=str(displaced)
            elif backup.exists():os.rename(backup,destination)
        receipt['status']='rolled_back';atomic(receipt_path,receipt)
        return {'status':'success','receipt':receipt}
