"""Internal primitive checks for schema-bound projected inventory values."""
import ipaddress
import math
import re


def matches(spec, value):
    kind = spec['type']
    if kind=='integer':
        valid = type(value) is int and 0 <= value <= 2**64-1
    elif kind=='number':
        valid = type(value) in (int,float) and math.isfinite(value) and value >= 0 and value==round(value,spec.get('fraction_digits') or 6)
    elif kind=='string':
        valid = isinstance(value,str) and '\x00' not in value
    else:
        valid = kind=='array' and isinstance(value,list)
    if not valid:
        return False
    if 'maximum' in spec and value>spec['maximum']:
        return False
    if spec['unit']=='percent' and not 0<=value<=100:
        return False
    if 'max_length' in spec and len(value)>spec['max_length']:
        return False
    if 'pattern' in spec and re.fullmatch(spec['pattern'],value) is None:
        return False
    if 'enum' in spec and value not in spec['enum']:
        return False
    if 'ip_version' in spec:
        try:
            if '%' in value or ipaddress.ip_address(value).version!=spec['ip_version']:
                return False
        except ValueError:
            return False
    return True
