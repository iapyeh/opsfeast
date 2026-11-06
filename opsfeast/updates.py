"""Read-only official version checks and review evidence; never applies updates."""
import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import ConfigError

SOURCES = {'opsfeast': 'https://github.com/iapyeh/opsfeast',
           'sshscript': 'https://pypi.org/project/sshscript/'}


class CheckError(ConfigError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CheckError('source_redirect_rejected')


def fetch(url, *, as_json=True):
    request = Request(url, headers={'User-Agent': 'OpsFeast-version-check/0.1.0', 'Accept': 'application/json' if as_json else 'text/plain'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024: raise CheckError('source_response_too_large')
        return json.loads(raw) if as_json else raw.decode('utf-8').strip()
    except HTTPError as exc:
        raise CheckError('source_not_found' if exc.code == 404 else 'source_http_error') from None
    except (URLError, OSError, ValueError, UnicodeError):
        raise CheckError('source_unavailable') from None


def git(root, *args):
    try:
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None


def current(installation):
    root = Path(installation).resolve(strict=True)
    try: version = (root / 'VERSION').read_text().strip()
    except OSError: version = None
    try: sshscript = metadata.version('sshscript')
    except metadata.PackageNotFoundError: sshscript = None
    head = git(root, 'rev-parse', 'HEAD')
    branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    dirty = git(root, 'status', '--porcelain', '--untracked-files=normal')
    contract = root / 'schemas' / 'sshscript-runtime.json'
    try: supported = json.loads(contract.read_text())['version']
    except (OSError, ValueError, KeyError, TypeError): supported = None
    return {'opsfeast': {'version': version, 'commit': head.stdout.strip() if head and head.returncode == 0 else None,
                         'branch': branch.stdout.strip() if branch and branch.returncode == 0 else None,
                         'local_changes': bool(dirty.stdout) if dirty and dirty.returncode == 0 else None},
            'sshscript': {'version': sshscript, 'supported_version': supported}}


def release_version(value, *, stable=True):
    try:
        from packaging.version import Version, InvalidVersion
    except ImportError:
        raise CheckError('version_dependency_missing') from None
    if not isinstance(value, str): return None
    try: parsed = Version(value)
    except InvalidVersion: return None
    return None if stable and (parsed.is_prerelease or parsed.is_devrelease) else parsed


def check(installation, product):
    if product not in SOURCES: raise ConfigError('unknown_update_product')
    installed = current(installation)[product]
    result = {'schema_version': '0.1.0', 'product': product, 'current': installed,
              'checked_at': datetime.now(timezone.utc).isoformat(), 'source': SOURCES[product],
              'status': 'success', 'update_available': None, 'update_method': 'agent_review'}
    try:
        if product == 'sshscript':
            data = fetch('https://pypi.org/pypi/sshscript/json')
            candidates = [(release_version(version), version) for version, files in data['releases'].items()
                          if release_version(version) is not None and any(not item.get('yanked', False) for item in files)]
            if not candidates: raise CheckError('stable_release_unavailable')
            newest, version = max(candidates)
            before = release_version(installed['version'], stable=False)
            result.update(latest={'version': version}, update_available=newest > before if before else None,
                          comparison=('update_available' if newest > before else 'local_newer' if newest < before else 'up_to_date') if before else 'comparison_unknown',
                          compatible=version == installed['supported_version'] if installed['supported_version'] is not None else None)
        else:
            base = 'https://api.github.com/repos/iapyeh/opsfeast'
            remote = fetch(base + '/commits/main')['sha']
            if not isinstance(remote, str) or not re.fullmatch(r'[0-9a-f]{40}', remote): raise CheckError('invalid_source_metadata')
            version = fetch('https://raw.githubusercontent.com/iapyeh/opsfeast/' + remote + '/VERSION', as_json=False)
            if not re.fullmatch(r'[0-9][0-9A-Za-z.+!-]{0,63}', version): raise CheckError('invalid_source_metadata')
            result['latest'] = {'version': version, 'commit': remote, 'branch': 'main'}
            local = installed['commit']
            comparison = 'comparison_unknown'
            if local == remote: comparison = 'up_to_date'
            elif local:
                ahead = git(installation, 'merge-base', '--is-ancestor', remote, local)
                behind = git(installation, 'merge-base', '--is-ancestor', local, remote)
                if ahead and ahead.returncode == 0: comparison = 'local_newer'
                elif behind and behind.returncode == 0: comparison = 'update_available'
                else:
                    try:
                        relation = fetch(base + '/compare/' + local + '...' + remote)['status']
                        comparison = {'ahead':'update_available', 'behind':'local_newer', 'identical':'up_to_date', 'diverged':'diverged'}.get(relation, 'comparison_unknown')
                    except CheckError: pass
            result.update(comparison=comparison, update_available=True if comparison == 'update_available' else False if comparison in ('up_to_date','local_newer') else None)
    except CheckError as exc:
        result.update(status='failed', reason_code=str(exc))
    except (KeyError, TypeError, ValueError, AttributeError):
        result.update(status='failed', reason_code='invalid_source_metadata')
    return result


def main():
    parser = argparse.ArgumentParser(description='Read installed versions or check official sources; never installs or replaces files. JSON output.')
    parser.add_argument('action', choices=('show', 'check'))
    parser.add_argument('--installation', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--product', choices=tuple(SOURCES))
    args = parser.parse_args()
    if args.action == 'check' and not args.product: parser.error('check requires --product')
    result = current(args.installation) if args.action == 'show' else check(args.installation, args.product)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get('status') == 'failed': parser.exit(1)


if __name__ == '__main__': main()
