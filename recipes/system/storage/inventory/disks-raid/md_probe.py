"""Fixed read-only Linux sysfs reader, sent through python3 -c. No mdadm required."""
import json
from pathlib import Path


def collect(base=Path('/sys/block')):
    arrays, errors = [], []

    def read(path, optional=False):
        try:
            with path.open() as stream:
                value = stream.read(4097)
            if len(value) > 4096:
                raise ValueError('oversized sysfs attribute')
            return value.strip()
        except FileNotFoundError:
            if not optional:
                errors.append(str(path))
        except (OSError, ValueError):
            errors.append(str(path))
        return None

    try:
        devices = sorted(base.iterdir())
        for device in devices:
            directory = device / 'md'
            if not directory.is_dir():
                continue
            values = {name: read(directory / name, optional=name in ('degraded', 'sync_action', 'sync_completed'))
                      for name in ('level', 'array_state', 'raid_disks', 'degraded', 'sync_action', 'sync_completed')}
            members = []
            for member in sorted(directory.iterdir()):
                if member.name.startswith('dev-') and member.is_dir():
                    members.append({'sysfs_name': member.name, 'state': read(member / 'state'),
                                    'slot': read(member / 'slot', optional=True),
                                    'block_device': str((member / 'block').resolve()) if (member / 'block').exists() else None})
            arrays.append({'name': device.name, 'path': '/dev/' + device.name, **values, 'members': members})
    except OSError:
        errors.append(str(base))
    return {'arrays': arrays, 'errors': errors}


if __name__ == '__main__':
    print(json.dumps(collect(), allow_nan=False))
