"""Dependency-free PEP 517 backend for the bundled checkout and public package.

Only explicit public directories/extensions are included; private instance data,
registries, local agent guidance, caches and generated artifacts are excluded.
"""
import base64
import csv
import hashlib
import io
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent
NAME = 'opsfeast'
VERSION = (ROOT / 'VERSION').read_text().strip()
DIST = f'{NAME}-{VERSION}.dist-info'


def source_files():
    for name in ('VERSION', 'README.md', 'AGENTS.md', 'pyproject.toml', 'build_backend.py',
                 'requirements.txt', 'requirements-init.txt', 'requirements-tui.txt'):
        yield Path(name)
    allowed = {'.py', '.md', '.yaml', '.json', '.txt', '.sh', '.html', '.css', '.js', '.svg', '.yang'}
    for directory in ('opsfeast', 'tools', 'recipes', 'consumers', 'skills', 'docs', 'schemas', 'templates', 'tests'):
        for path in sorted((ROOT / directory).rglob('*')):
            if path.is_file() and not path.is_symlink() and (path.suffix in allowed or path.name == 'LICENSE') and '__pycache__' not in path.parts:
                yield path.relative_to(ROOT)


def _metadata():
    return (f'Metadata-Version: 2.3\nName: {NAME}\nVersion: {VERSION}\n'
            'Summary: OpsFeast bundled Core Python API\nRequires-Python: >=3.11\n'
            'Requires-Dist: PyYAML==6.0.3\nRequires-Dist: tabulate[widechars]==0.10.0\nProvides-Extra: execution\n'
            'Requires-Dist: sshscript==5.0.0; extra == "execution"\nProvides-Extra: tui\n'
            'Requires-Dist: textual==8.2.8; extra == "tui"\n')


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    directory = Path(metadata_directory) / DIST
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'METADATA').write_text(_metadata())
    (directory / 'WHEEL').write_text('Wheel-Version: 1.0\nGenerator: opsfeast\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
    return DIST


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    name = f'{NAME}-{VERSION}-py3-none-any.whl'
    path = Path(wheel_directory) / name
    entries = {}
    for relative in source_files():
        if relative.parts[0] == 'opsfeast':
            target = relative.as_posix()
        elif relative.name in ('build_backend.py', 'pyproject.toml'):
            continue
        else:
            target = '_opsfeast_data/' + relative.as_posix()
        entries[target] = (ROOT / relative).read_bytes()
    entries['_opsfeast_data/__init__.py'] = b'"""Bundled public OpsFeast resources."""\n'
    entries[DIST + '/METADATA'] = _metadata().encode()
    entries[DIST + '/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: opsfeast\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    record = io.StringIO(newline='')
    writer = csv.writer(record)
    for key, data in sorted(entries.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        writer.writerow([key, 'sha256=' + digest, len(data)])
    writer.writerow([DIST + '/RECORD', '', ''])
    entries[DIST + '/RECORD'] = record.getvalue().encode()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for key, data in sorted(entries.items()):
            item = zipfile.ZipInfo(key, date_time=(2026, 1, 1, 0, 0, 0))
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)
    return name


def build_sdist(sdist_directory, config_settings=None):
    name = f'{NAME}-{VERSION}.tar.gz'
    with tarfile.open(Path(sdist_directory) / name, 'w:gz') as archive:
        for relative in source_files():
            archive.add(ROOT / relative, arcname=f'{NAME}-{VERSION}/{relative.as_posix()}', recursive=False)
    return name
