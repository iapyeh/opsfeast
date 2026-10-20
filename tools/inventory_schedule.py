"""Deterministic inventory schedules. No retries, no background model calls."""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re

from opsfeast import ConfigError, read_yaml
from retention_store import checked, atomic, canonical

VERSION = '0.1.0'


def interval(value):
    if isinstance(value, str):
        match = re.fullmatch(r'([1-9][0-9]*)([smhdw])', value)
        if not match:
            raise ConfigError('interval must be seconds or a duration such as 5m, 1h, 1d, 7w')
        value = int(match[1]) * {'s':1,'m':60,'h':3600,'d':86400,'w':604800}[match[2]]
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 60:
        raise ConfigError('interval must be finite and at least 60 seconds')
    return value


def overrides(value, catalog):
    if not isinstance(value, dict) or set(value)-set(catalog['jobs']):
        raise ConfigError('inventory job overrides contain unknown IDs')
    for key, options in value.items():
        if not isinstance(options,dict) or set(options)-{'enabled','interval'}:
            raise ConfigError('job override accepts enabled and interval only')
        if 'enabled' in options and type(options['enabled']) is not bool:
            raise ConfigError('job enabled must be boolean')
        if 'interval' in options:
            interval(options['interval'])
    return value


def settings(root, catalog, hosts):
    path = checked(root, 'inventory.yaml')
    value = read_yaml(path) if path.exists() else {'schema_version':VERSION,'defaults':{},'hosts':{}}
    if not isinstance(value,dict) or set(value)-{'schema_version','defaults','hosts'} or value.get('schema_version') != VERSION:
        raise ConfigError('inventory.yaml requires schema_version 0.1.0, defaults and hosts')
    overrides(value.get('defaults',{}), catalog)
    selected = value.get('hosts',{})
    if not isinstance(selected,dict) or set(selected)-set(hosts):
        raise ConfigError('inventory.yaml hosts must be configured host IDs')
    for host, entry in selected.items():
        if not isinstance(entry,dict) or set(entry)-{'enabled','recipe','jobs'} or type(entry.get('enabled',False)) is not bool:
            raise ConfigError('inventory host accepts boolean enabled, recipe and jobs')
        if not isinstance(entry.get('recipe','system/inventory/overview'),str) or not entry.get('recipe','system/inventory/overview'):
            raise ConfigError('inventory recipe reference must be nonempty')
        overrides(entry.get('jobs',{}), catalog)
    return value


def effective(catalog, settings, host):
    result = {}
    entry = settings.get('hosts',{}).get(host,{})
    for key, spec in catalog['jobs'].items():
        result[key] = dict(spec, **settings.get('defaults',{}).get(key,{}))
        result[key].update(entry.get('jobs',{}).get(key,{}))
        result[key]['interval'] = interval(result[key]['interval'])
    return result


def state_key(host, reference, definition):
    return hashlib.sha256(canonical([host,reference,definition]).encode()).hexdigest()


def read_state(root):
    path = checked(root, '.inventory-state.json')
    if not path.exists():
        return {'schema_version':VERSION,'targets':{}}
    try:
        value = json.loads(path.read_text())
    except (ValueError,OSError):
        raise ConfigError('invalid inventory scheduler state') from None
    if not isinstance(value,dict) or set(value) != {'schema_version','targets'} or value['schema_version'] != VERSION or not isinstance(value['targets'],dict):
        raise ConfigError('invalid inventory scheduler state')
    for target, jobs in value['targets'].items():
        if not re.fullmatch('[a-f0-9]{64}', target) or not isinstance(jobs,dict):
            raise ConfigError('invalid inventory scheduler target')
        for job, item in jobs.items():
            if not isinstance(job,str) or not isinstance(item,dict) or set(item) != {'attempted_at','status','source_observation_id'}:
                raise ConfigError('invalid inventory scheduler attempt')
            parse_time(item['attempted_at'])
    return value


def parse_time(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError()
        return result
    except (ValueError,TypeError):
        raise ConfigError('scheduler time must have a timezone') from None


def due(jobs, previous, at):
    current = parse_time(at)
    return [key for key,item in jobs.items() if item['enabled'] and
            (key not in previous or (current-parse_time(previous[key]['attempted_at'])).total_seconds() >= item['interval'])]


@contextmanager
def lock(root):
    path = checked(root, '.inventory-dispatch.lock')
    with path.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def write_state(root, state):
    atomic(checked(root, '.inventory-state.json'), canonical(state)+'\n')
