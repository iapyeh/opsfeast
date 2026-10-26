"""Data-only portable contracts. Restricted JSON Schema, no imports or remote refs."""
import json
import math
import re
from functools import lru_cache
import subprocess
import sys
from opsfeast import ConfigError

DIALECT = 'opsfeast-json-schema/0.1.0'
KEYS = {'$schema', '$id', '$comment', 'title', 'description', 'default', 'examples',
        '$ref', '$defs', 'definitions', 'type', 'enum', 'const', 'properties', 'required',
        'additionalProperties', 'items', 'minItems', 'maxItems', 'uniqueItems',
        'minLength', 'maxLength', 'pattern', 'minimum', 'maximum', 'exclusiveMinimum',
        'exclusiveMaximum', 'multipleOf', 'allOf', 'anyOf', 'oneOf', 'not', 'if', 'then', 'else',
        'minProperties', 'maxProperties', 'format', 'dependentRequired', 'propertyNames', 'unit', 'property_catalog'}


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        raise ConfigError('invalid portable JSON') from None


def definition(schema, depth=0):
    if depth > 64 or not isinstance(schema, (dict, bool)):
        raise ConfigError('invalid or excessively nested portable schema')
    if isinstance(schema, bool):
        return
    if set(schema) - KEYS:
        raise ConfigError('unsupported portable schema keywords: ' + ', '.join(sorted(set(schema) - KEYS)))
    if '$ref' in schema and (not isinstance(schema['$ref'], str) or not schema['$ref'].startswith('#/')):
        raise ConfigError('portable schemas require bundled local JSON-pointer references')
    for key in ('properties', '$defs', 'definitions'):
        if key in schema:
            if not isinstance(schema[key], dict):
                raise ConfigError('invalid schema mapping')
            for child in schema[key].values():
                definition(child, depth+1)
    for key in ('items', 'additionalProperties', 'propertyNames', 'not', 'if', 'then', 'else'):
        if key in schema:
            definition(schema[key], depth+1)
    for key in ('allOf', 'anyOf', 'oneOf'):
        if key in schema:
            if not isinstance(schema[key], list) or not schema[key]:
                raise ConfigError('invalid schema alternatives')
            for child in schema[key]:
                definition(child, depth+1)
    kinds = schema.get('type', [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not isinstance(kinds, list) or any(k not in ('object','array','string','number','integer','boolean','null') for k in kinds):
        raise ConfigError('invalid schema type')
    if 'pattern' in schema:
        # Restrict expensive expressions from untrusted data-only contracts.
        pattern = schema['pattern']
        if not isinstance(pattern, str) or len(pattern) > 256 or re.search(r'\\[1-9]|\(\?(?!:)', pattern):
            raise ConfigError('unsupported portable schema pattern')
        try:
            re.compile(pattern)
        except re.error:
            raise ConfigError('invalid schema pattern') from None
    for key in ('required',):
        if key in schema and (not isinstance(schema[key],list) or any(not isinstance(v,str) for v in schema[key]) or len(set(schema[key]))!=len(schema[key])):
            raise ConfigError('invalid schema field names')
    for key in ('minItems','maxItems','minLength','maxLength','minProperties','maxProperties'):
        if key in schema and (type(schema[key]) is not int or schema[key]<0):raise ConfigError('invalid schema size constraint')
    for key in ('minimum','maximum','exclusiveMinimum','exclusiveMaximum','multipleOf'):
        if key in schema and (type(schema[key]) not in (int,float) or not math.isfinite(schema[key]) or key=='multipleOf' and schema[key]<=0):raise ConfigError('invalid schema numeric constraint')
    if 'dependentRequired' in schema and (not isinstance(schema['dependentRequired'],dict) or any(not isinstance(v,list) or any(not isinstance(k,str) for k in v) for v in schema['dependentRequired'].values())):
        raise ConfigError('invalid schema dependentRequired')
    if 'enum' in schema and (not isinstance(schema['enum'],list) or not schema['enum']):raise ConfigError('invalid schema enum')
    if schema.get('format') not in (None, 'date-time', 'date', 'uuid', 'uri', 'email'):
        raise ConfigError('unsupported portable schema format')
    canonical(schema)


def validate(value, schema, root=None, depth=0):
    if root is None:
        definition(schema)
        root = schema
        canonical(value)
    if depth > 128:
        raise ConfigError('portable data/schema recursion limit')
    if schema is True:
        return
    if schema is False:
        raise ConfigError('data rejected by schema')
    if '$ref' in schema:
        target = root
        try:
            for part in schema['$ref'][2:].split('/'):
                target = target[part.replace('~1','/').replace('~0','~')]
        except (KeyError, TypeError):
            raise ConfigError('unresolved portable schema reference') from None
        validate(value, target, root, depth+1)
    check = lambda child: validate(value, child, root, depth+1)
    for child in schema.get('allOf', []):
        check(child)
    def matches(child):
        try:
            check(child)
            return True
        except ConfigError:
            return False
    for key in ('anyOf', 'oneOf'):
        if key in schema:
            count = sum(matches(child) for child in schema[key])
            if not count or key == 'oneOf' and count != 1:
                raise ConfigError('data does not match schema alternatives')
    if 'not' in schema and matches(schema['not']):
        raise ConfigError('data matches prohibited schema')
    if 'if' in schema:
        check(schema.get('then' if matches(schema['if']) else 'else', True))
    types = {'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),
             'number':type(value) in (int,float),'integer':type(value) is int or type(value) is float and value.is_integer(),
             'boolean':type(value) is bool,'null':value is None}
    kinds = schema.get('type', list(types))
    if not any(types[k] for k in ([kinds] if isinstance(kinds,str) else kinds)):
        raise ConfigError('portable data type mismatch')
    if 'const' in schema and canonical(value) != canonical(schema['const']):
        raise ConfigError('portable data const mismatch')
    if 'enum' in schema and not any(canonical(value) == canonical(v) for v in schema['enum']):
        raise ConfigError('portable data enum mismatch')
    if isinstance(value,dict):
        if set(schema.get('required',[])) - set(value):
            raise ConfigError('portable data missing required fields')
        if not schema.get('minProperties',0) <= len(value) <= schema.get('maxProperties',len(value)):
            raise ConfigError('portable property count mismatch')
        for key,requirements in schema.get('dependentRequired',{}).items():
            if key in value and set(requirements)-set(value):raise ConfigError('portable dependent fields missing')
        for key,item in value.items():
            if 'propertyNames' in schema:validate(key,schema['propertyNames'],root,depth+1)
            validate(item, schema.get('properties',{}).get(key,schema.get('additionalProperties',True)),root,depth+1)
    if isinstance(value,list):
        if not schema.get('minItems',0) <= len(value) <= schema.get('maxItems',len(value)):
            raise ConfigError('portable array size mismatch')
        if schema.get('uniqueItems') and len({canonical(v) for v in value}) != len(value):
            raise ConfigError('portable array has duplicates')
        for item in value:
            validate(item,schema.get('items',True),root,depth+1)
    if isinstance(value,str):
        if not schema.get('minLength',0) <= len(value) <= schema.get('maxLength',len(value)):
            raise ConfigError('portable string size mismatch')
        if 'pattern' in schema and (len(value)>65536 or not search(schema['pattern'],value)):
            raise ConfigError('portable pattern mismatch')
        form=schema.get('format')
        try:
            if form=='date-time':
                from datetime import datetime
                if datetime.fromisoformat(value.replace('Z','+00:00')).tzinfo is None:
                    raise ValueError()
            if form=='date':
                from datetime import date
                date.fromisoformat(value)
            if form=='uuid':
                from uuid import UUID
                UUID(value)
            if form=='uri' and not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',value):
                raise ValueError()
            if form=='email' and not re.fullmatch(r'[^\s@]+@[^\s@]+',value):
                raise ValueError()
        except ValueError:
            raise ConfigError('portable format mismatch') from None
    if type(value) in (int,float):
        if not math.isfinite(value) or value < schema.get('minimum',value) or value > schema.get('maximum',value):
            raise ConfigError('portable numeric bound mismatch')
        if 'exclusiveMinimum' in schema and value <= schema['exclusiveMinimum'] or 'exclusiveMaximum' in schema and value >= schema['exclusiveMaximum']:
            raise ConfigError('portable exclusive bound mismatch')
        if 'multipleOf' in schema and (schema['multipleOf']<=0 or not math.isclose(value/schema['multipleOf'],round(value/schema['multipleOf']))):
            raise ConfigError('portable multiple mismatch')


@lru_cache(maxsize=512)
def search(pattern,value):
    # Bounded subprocess for quantified groups: hostile backtracking cannot hang import.
    if re.search(r'\)[+*{]',pattern):
        if len(value)>4096:raise ConfigError('complex schema pattern input too long')
        try:
            result=subprocess.run([sys.executable,'-I','-c',
                'import json,re,sys; p,v=json.load(sys.stdin); print(int(re.search(p,v) is not None))'],
                input=json.dumps([pattern,value]),capture_output=True,text=True,timeout=1)
        except subprocess.TimeoutExpired:
            raise ConfigError('portable schema pattern evaluation timed out') from None
        if result.returncode:raise ConfigError('portable schema pattern evaluation failed')
        return result.stdout.strip()=='1'
    return re.search(pattern,value) is not None


def timestamp(value):
    """Canonical UTC source timestamp for portable recipe producers."""
    from datetime import datetime,timezone
    try:
        instant=datetime.fromisoformat(value.replace('Z','+00:00'))
        if instant.tzinfo is None:raise ValueError()
        return instant.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (ValueError,TypeError,AttributeError):
        raise ConfigError('timestamp requires a timezone-aware ISO value') from None


def uuid_text(value):
    from uuid import UUID
    try:
        if not isinstance(value,str) or str(UUID(value))!=value:raise ValueError()
        return value
    except (ValueError,TypeError,AttributeError):raise ConfigError('canonical UUID required') from None


def validate_collection_evidence(value):
    """Public data-only validation of the platform collection-evidence 0.1.0 envelope."""
    from collection_evidence import validate
    return validate(value)
