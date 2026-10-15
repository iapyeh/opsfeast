"""Check or stage the public SSHScript skill bundle; never activate or install it."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import urllib.request
import zipfile
from console_output import ConsoleDependencyError

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://iapyeh.github.io/sshscript/v3a/ai-agents/downloads/sshscript-skill.zip'
LIMIT = 10 * 1024 * 1024
REQUIRED = ('SKILL.md', 'references/agent-guide.md', 'references/api-guide.md', 'references/versioning.md')


class BundleError(ValueError):
    pass


def fetch_bundle():
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
        if not response.url.startswith('https://iapyeh.github.io/'):
            raise BundleError('bundle redirected outside the public source host')
        content = response.read(LIMIT + 1)
    if len(content) > LIMIT:
        raise BundleError('bundle exceeds download size limit')
    return content


def inspect_bundle(content):
    """Validate before writing: one skill root, regular files, bounded expansion."""
    files = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if len(archive.infolist()) > 500:
            raise BundleError('too many bundle entries')
        seen = set()
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if ('\\' in item.filename or path.is_absolute() or '..' in path.parts or
                    not path.parts or path.parts[0] != 'sshscript' or str(path) != item.filename.rstrip('/')):
                raise BundleError('unsupported bundle path')
            if path in seen:
                raise BundleError('duplicate bundle path')
            seen.add(path)
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise BundleError('bundle contains a link or special file')
            if item.is_dir():
                continue
            total += item.file_size
            if total > LIMIT:
                raise BundleError('expanded bundle exceeds size limit')
            relative = path.relative_to('sshscript').as_posix()
            if relative in ('.', 'SOURCE.json'):
                raise BundleError('bundle contains a reserved file')
            files[relative] = archive.read(item)
    if any(name not in files for name in REQUIRED):
        raise BundleError('bundle is missing the full skill or required references')
    skill = files['SKILL.md'].decode('utf-8')
    guide = files['references/agent-guide.md'].decode('utf-8')
    skill_contract = re.search(r'SSHScript (\d+\.\d+\.\d+) contract', skill)
    guide_contract = re.search(r'Documentation contract: SSHScript (\d+\.\d+\.\d+)', guide)
    if not skill_contract or not guide_contract or skill_contract[1] != guide_contract[1]:
        raise BundleError('cannot establish a consistent documentation contract')
    return files, skill_contract[1]


def check(content, installed=None):
    installed = installed or ROOT / 'skills/sshscript'
    source = json.loads((installed / 'SOURCE.json').read_text(encoding='utf-8'))
    files, contract = inspect_bundle(content)
    digest = hashlib.sha256(content).hexdigest()
    local = {p.relative_to(installed).as_posix(): p.read_bytes()
             for p in installed.rglob('*') if p.is_file() and p.name != 'SOURCE.json'}
    return {'source_url': SOURCE_URL, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            'installed_contract': source['documentation_contract'], 'candidate_contract': contract,
            'bundle_sha256': digest, 'bundle_changed': digest != source['bundle_sha256'],
            'local_matches_candidate': local == files,
            'contract_matches_runner': contract == '5.0.0',
            'status': 'unchanged' if digest == source['bundle_sha256'] and local == files else 'review_required'}


def stage(content, destination):
    files, contract = inspect_bundle(content)
    # Exclusive creation preserves previously downloaded candidates and snapshots.
    destination.mkdir(parents=True, exist_ok=False)
    try:
        (destination / 'sshscript-skill.zip').write_bytes(content)
        snapshot = destination / 'sshscript'
        for relative, data in files.items():
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        now = datetime.now(timezone.utc)
        source = {'source_url': SOURCE_URL, 'saved_date': now.date().isoformat(),
                  'saved_at_utc': now.isoformat(), 'documentation_contract': contract,
                  'bundle_sha256': hashlib.sha256(content).hexdigest(),
                  'update_policy': 'Check only when requested or on an authorized schedule; apply updates only with authorization.'}
        (snapshot / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n', encoding='utf-8')
    except Exception:
        shutil.rmtree(destination)
        raise
    return {'candidate_directory': str(snapshot.resolve()), 'documentation_contract': contract,
            'bundle_sha256': source['bundle_sha256'], 'activated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check_parser = commands.add_parser('check')
    check_parser.add_argument('--json', action='store_true')
    download = commands.add_parser('download')
    download.add_argument('--json', action='store_true')
    download.add_argument('destination', type=Path, help='new staging directory; existing paths are refused')
    args = parser.parse_args(argv)
    try:
        from console_output import prepare, print_report
        prepare(args.json)
        content = fetch_bundle()
        report = check(content) if args.command == 'check' else stage(content, args.destination)
        print_report(report, json_output=args.json)
        return 0
    except Exception as exc:
        message = str(exc) if isinstance(exc, (BundleError, ConsoleDependencyError)) else type(exc).__name__
        print(f'ERROR: {message}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
