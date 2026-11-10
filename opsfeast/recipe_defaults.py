"""Edit Profile default recipe input variables in the existing hosts.yaml layer."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4

from . import ConfigError, read_yaml
from .core import Instance
from .host_settings import _Candidate, _TextDocument, _load, _revision
from .identity import _locked
from .site import SiteConflict, _atomic
from .menu_preferences import MenuError


def item_for(profile,reference):
    from recipe_catalog import choose
    from recipe_settings import reference as normalized
    if normalized(reference)!=reference:raise MenuError('exact_recipe_reference_required')
    item=choose(profile.root,reference)
    if item['reference']!=reference or not item.get('directory'):raise MenuError('recipe_not_available')
    return item


def _state(product,profile,reference):
    selected,config,files=_load(product,profile)
    item=item_for(selected,reference)
    info=config.recipe_location(reference,selected.root/'hosts.yaml',cli=True)
    return selected,config,files,item,info


def _options_revision(selected,files,item):
    from .recipe_install import fingerprint
    value={'configuration':_revision(selected,files),'descriptor':item['descriptor'],
           'code':fingerprint(Path(item['directory']))}
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def inspect(product,*,profile,reference):
    selected,config,files,item,info=_state(product,profile,reference)
    from recipe_settings import merge
    from management_view import masked
    inputs=item.get('inputs') or {}
    specs=inputs.get('variables',{}) if isinstance(inputs,dict) else {}
    if not isinstance(specs,dict):specs={}
    specs={name:spec for name,spec in specs.items() if isinstance(spec,dict)}
    overrides=config.default_recipes.get(reference,{}).get('vars',{})
    variables=[]
    for name,spec in specs.items():
        base=merge({name:spec['default']} if 'default' in spec else {},{name:info['vars'][name]} if name in info['vars'] else {})
        value=merge(base,{name:overrides[name]} if name in overrides else {})
        editable=(item['runnable'] and masked({name:'probe'})=={name:'probe'} and masked(value)==value and masked(base)==base)
        variables.append({'name':name,'definition':{k:v for k,v in spec.items() if k!='default'},'configured':name in overrides,
                          'base_present':name in base,'base_value':masked(base).get(name),
                          'value_present':name in value,'value':masked(value).get(name),'editable':editable})
    return {'schema_version':'0.1.0','profile':selected.name,'reference':reference,'revision':_options_revision(selected,files,item),
            'scope':'hosts.yaml default.recipes.REFERENCE.vars','variables':variables,'runnable':item['runnable'],
            'precedence':'recipe -> source -> Profile defaults -> groups -> host -> invocation',
            'remote_effects':False}


def update(product,*,profile,reference,expected_revision,changes,remove):
    if not isinstance(changes,dict) or not isinstance(remove,list) or any(not isinstance(n,str) for n in remove) or len(set(remove))!=len(remove) or set(changes)&set(remove):
        raise MenuError('invalid_default_option_changes')
    product=Path(product).resolve(strict=True)
    with _locked(product/'.opsfeast-profiles.json'):
        selected=Instance.open(product).profile(profile)
        with _locked(selected.root/'.opsfeast-host-settings.json'):
            state=inspect(product,profile=profile,reference=reference)
            if expected_revision!=state['revision']:raise SiteConflict('recipe options changed; reload')
            definitions={v['name']:v for v in state['variables']}
            if any(name not in definitions or not definitions[name]['editable'] for name in [*changes,*remove]):
                raise MenuError('default_option_is_unknown_or_sensitive')
            from recipe_inputs import validate_value
            from management_view import masked
            for name,value in changes.items():
                if masked({name:value})!={name:value}:raise MenuError('default_option_is_unknown_or_sensitive')
                validate_value(name,definitions[name]['definition'],value)
            selected,config,files,item,info=_state(product,profile,reference)
            if _options_revision(selected,files,item)!=expected_revision:raise SiteConflict('recipe options changed while preparing save')
            source=selected.root/'hosts.yaml';raw=files[source]
            import yaml
            if any(isinstance(t,(yaml.tokens.AnchorToken,yaml.tokens.AliasToken)) for t in yaml.scan(raw.decode())):
                raise MenuError('yaml_alias_edit_unsupported')
            try:from ruamel.yaml import YAML
            except ImportError:raise MenuError('recipe_default_editor_dependency_unavailable') from None
            editor=YAML(typ='rt');editor.preserve_quotes=True;editor.version=(1,1)
            document=editor.load(raw.decode())
            def patch(doc):
                recipes=doc.setdefault('default',{}).setdefault('recipes',{})
                # Bare/bundle: are one policy key; preserve whichever spelling the
                # owner already used, while rejecting duplicate normalized aliases.
                from recipe_settings import reference as canonical
                keys=[key for key in recipes if canonical(key)==reference]
                key=keys[0] if keys else reference
                options=recipes.setdefault(key,{})
                values=options.setdefault('vars',{})
                for name in remove:values.pop(name,None)
                for name,value in changes.items():values[name]=deepcopy(value)
            expected=deepcopy(config.documents[source]);patch(expected);patch(document)
            output=io.StringIO();editor.dump(document,output);candidate=output.getvalue()
            if read_yaml(_TextDocument(source,candidate))!=expected:raise MenuError('yaml_semantics_changed')
            try:_Candidate(selected.root,source,candidate).check()
            except ConfigError:raise MenuError('candidate_recipe_configuration_invalid') from None
            if any(path.read_bytes()!=value for path,value in files.items()):raise SiteConflict('configuration changed during save')
            backups=selected.root/'.recipe-default-backups'
            if backups.is_symlink() or (backups.exists() and not backups.is_dir()):raise MenuError('invalid_default_backup_directory')
            backups.mkdir(mode=0o700,exist_ok=True)
            _atomic(backups/(str(uuid4())+'.yaml'),raw)
            _atomic(source,candidate.encode())
            return inspect(product,profile=profile,reference=reference)
