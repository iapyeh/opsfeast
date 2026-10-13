"""Report this interpreter's Ops prerequisites without installing or connecting."""
import argparse
from importlib import import_module, metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def inspect_package(name, expected=None, distribution=None):
    report = {'required_version': expected}
    try:
        module = import_module(name)
        report.update(import_version=module.__version__, distribution_version=metadata.version(distribution or name),
                      module_path=module.__file__)
        report['ready'] = report['import_version'] == report['distribution_version']
        if expected:
            report['ready'] = report['ready'] and report['import_version'] == expected
    except Exception as exc:
        report.update(ready=False, error=type(exc).__name__)
    return report


def inspect_environment(scope='full'):
    python_ok = sys.version_info >= (3, 11)
    packages = {'PyYAML': inspect_package('yaml', '6.0.3', 'PyYAML')}
    if scope == 'full':
        packages['sshscript'] = inspect_package('sshscript', '5.0.0')
    try:
        source = json.loads((ROOT / 'skills/sshscript/SOURCE.json').read_text(encoding='utf-8'))
        skill = {'documentation_contract': source['documentation_contract'],
                 'ready': source['documentation_contract'] == '5.0.0'}
        for relative in ('SKILL.md', 'references/agent-guide.md', 'references/api-guide.md', 'references/versioning.md'):
            if not (ROOT / 'skills/sshscript' / relative).is_file():
                skill['ready'] = False
    except (OSError, ValueError, KeyError, TypeError) as exc:
        skill = {'ready': False, 'error': type(exc).__name__}
    return {'scope': scope, 'interpreter': sys.executable, 'python': sys.version.split()[0],
            'python_ready': python_ok, 'packages': packages, 'skill': skill,
            'ready': python_ok and all(p['ready'] for p in packages.values()) and skill['ready']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=('init', 'full'), default='full')
    args = parser.parse_args(argv)
    report = inspect_environment(args.scope)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report['ready'] else 1


if __name__ == '__main__':
    sys.exit(main())
