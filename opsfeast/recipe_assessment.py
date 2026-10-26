"""Recipe-owned human findings, independent from fixed execution/storage states."""
import copy
from opsfeast import ConfigError

VERSION = '0.1.0'
SEVERITIES = ('info', 'warning', 'error', 'critical')


def validate(value):
    if not isinstance(value, dict) or set(value) != {'label', 'severity', 'summary'}:
        raise ConfigError('assessment requires label, severity and summary')
    for name, limit in (('label', 80), ('summary', 1024)):
        text = value[name]
        if (not isinstance(text, str) or not text.strip() or text != text.strip() or len(text) > limit
                or any(ord(c) < 32 or 127 <= ord(c) < 160 or c in '\u2028\u2029' for c in text)):
            raise ConfigError('assessment text must be bounded single-line text without controls')
    if value['severity'] not in SEVERITIES:
        raise ConfigError('invalid assessment severity')
    return copy.deepcopy(value)


def text(value):
    assessment = validate(value)
    prefix = '' if assessment['severity'] == 'info' else assessment['severity'].upper() + ' · '
    return prefix + assessment['label']
