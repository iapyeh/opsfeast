"""Inventory-owned attention policy validation and deterministic retained-data evaluation."""
import math
from opsfeast import ConfigError

DEFAULTS = {'enabled': True, 'thresholds': {
    'filesystem_used_percent': {'warning': 90, 'critical': 95},
    'cpu_utilization_percent': {'warning': 90, 'critical': 95},
    'memory_available_percent': {'warning': 10, 'critical': 5},
    'load_5m_per_cpu': {'warning': 1, 'critical': 2}}}


def resolve(value):
    from recipe_settings import merge
    if not isinstance(value, dict) or set(value) - {'enabled', 'thresholds'}:
        raise ConfigError('attention accepts enabled and thresholds only')
    result = merge(DEFAULTS, value)
    if type(result['enabled']) is not bool or not isinstance(result['thresholds'], dict):
        raise ConfigError('attention requires Boolean enabled and a thresholds mapping')
    if set(result['thresholds']) != set(DEFAULTS['thresholds']):
        raise ConfigError('unknown inventory attention threshold')
    for name, rule in result['thresholds'].items():
        if not isinstance(rule, dict) or set(rule) != {'warning', 'critical'}:
            raise ConfigError('threshold requires warning and critical')
        for limit in rule.values():
            if type(limit) not in (int, float) or not math.isfinite(limit) or limit < 0 or (name != 'load_5m_per_cpu' and limit > 100):
                raise ConfigError('invalid inventory attention threshold range')
        if name == 'load_5m_per_cpu' and min(rule.values()) <= 0:
            raise ConfigError('load-per-CPU limits must be positive')
        if (rule['critical'] > rule['warning'] if name == 'memory_available_percent' else rule['critical'] < rule['warning']):
            raise ConfigError('inventory attention warning/critical order is invalid')
    return result


def evaluate(record, policy=None):
    """Preview thresholds over latest available observations; no live health claim.

    Baselines may have different ages. Each comparison names both source times.
    Failed/null latest samples never use an earlier value.
    """
    policy = resolve(policy or {})
    if not policy['enabled']:
        return {'policy': policy, 'findings': [], 'assessed': [], 'disabled': True}
    limits = policy['thresholds']
    data, samples = record['data'], []
    if 'groups' in data:
        samples = [sample for group in data['groups'] for sample in group['samples'] if sample['status'] == 'success']
    elif data.get('inventory'):
        inventory = data['inventory']
        for section, field in (('hardware', 'logical_cpus'), ('hardware', 'memory_total_bytes')):
            value = inventory.get(section, {}).get(field)
            samples.append({'property': section + '.' + field, 'value': value, 'observed_at': record['observed_at'], 'keys': {}})
        for row in inventory.get('storage', {}).get('filesystems') or []:
            value = row.get('used_percent')
            if isinstance(value, str):
                try:
                    value = float(value.rstrip('%'))
                except ValueError:
                    value = None
            samples.append({'property': 'storage.filesystems.used_percent', 'value': value,
                            'observed_at': record['observed_at'], 'keys': row})
    numeric = [sample for sample in samples if type(sample['value']) in (int, float) and math.isfinite(sample['value'])]
    latest = {}
    for sample in numeric:
        name = sample['property']
        if name not in latest or sample['observed_at'] > latest[name]['observed_at']:
            latest[name] = sample
    flags, assessed = [], []
    def thresholds(name, suffix=''):
        rule = limits[name]
        return 'warning ' + str(rule['warning']) + suffix + ', critical ' + str(rule['critical']) + suffix
    def flag(message, sample, critical=False, baseline=None):
        flags.append({'message': message, 'severity': 'critical' if critical else 'warning',
                      'observed_at': sample['observed_at'],
                      'baseline_at': baseline['observed_at'] if baseline else None})
    filesystems = [sample for sample in numeric if sample['property'] == 'storage.filesystems.used_percent' and 0 <= sample['value'] <= 100]
    if filesystems:
        assessed.append('filesystem capacity')
    for sample in filesystems:
        if sample['value'] >= limits['filesystem_used_percent']['warning']:
            flag('Filesystem ' + str(sample['keys'].get('mountpoint') or sample['keys'].get('name') or '(unnamed)') +
                 ' reported ' + format(sample['value'], '.6g') + '% used (thresholds: ' + thresholds('filesystem_used_percent', '%') + ').' , sample, sample['value'] >= limits['filesystem_used_percent']['critical'])
    cpu = latest.get('metrics.cpu_utilization_percent')
    if cpu and 0 <= cpu['value'] <= 100:
        assessed.append('CPU utilization')
        if cpu['value'] >= limits['cpu_utilization_percent']['warning']:
            flag('CPU utilization reported ' + format(cpu['value'], '.6g') + '% (thresholds: ' + thresholds('cpu_utilization_percent', '%') + ').' , cpu, cpu['value'] >= limits['cpu_utilization_percent']['critical'])
    load, cores = latest.get('metrics.load_5m'), latest.get('hardware.logical_cpus')
    if load and cores and load['value'] >= 0 and cores['value'] > 0:
        assessed.append('5-minute load')
        if load['value'] / cores['value'] >= limits['load_5m_per_cpu']['warning']:
            flag('5-minute load ' + format(load['value'], '.6g') + ' compared with the reported ' + format(cores['value'], '.6g') +
                 ' logical CPUs (load per CPU ' + format(load['value'] / cores['value'], '.6g') + '; thresholds: ' + thresholds('load_5m_per_cpu') + '). This does not identify CPU versus I/O pressure.', load, load['value'] / cores['value'] >= limits['load_5m_per_cpu']['critical'], baseline=cores)
    available, total = latest.get('metrics.memory_available_bytes'), latest.get('hardware.memory_total_bytes')
    if available and total and total['value'] > 0 and 0 <= available['value'] <= total['value']:
        assessed.append('memory headroom')
        ratio = available['value'] / total['value'] * 100
        if ratio <= limits['memory_available_percent']['warning']:
            flag('Available memory reported ' + format(ratio, '.3g') + '% of the reported total (thresholds: ' + thresholds('memory_available_percent', '%') + ').' ,
                 available, ratio <= limits['memory_available_percent']['critical'], baseline=total)
    return {'policy': policy, 'findings': flags, 'assessed': assessed, 'disabled': False}
