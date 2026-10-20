"""Manage only the current user's marked OpsFeast cron entry; preserve other entries."""
import hashlib
from pathlib import Path
import shlex
import subprocess
import sys

from opsfeast import ConfigError, REPOSITORY_ROOT


def marker(root):
    key = hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:16]
    return '# opsfeast-inventory:' + key


def command(root, python=None):
    python = Path(python or sys.executable).absolute()
    script = REPOSITORY_ROOT/'tools/opsfeast.py'
    args = [str(python),'-B',str(script),'inventory','dispatch','--root',str(Path(root).resolve()),'--quiet']
    if any('\n' in arg or '\r' in arg for arg in args):
        raise ConfigError('cron paths must not contain line breaks')
    # cron interprets percent signs even inside shell quotes.
    error_log = shlex.quote(str(Path(root).resolve()/'inventory-cron-errors.log')).replace('%',r'\%')
    return '* * * * * ' + shlex.join(args).replace('%',r'\%') + ' >/dev/null 2>>' + error_log + ' ' + marker(root)


def read(run=subprocess.run):
    result = run(['crontab','-l'],capture_output=True,text=True,check=False)
    if result.returncode:
        if result.returncode == 1 and 'no crontab' in result.stderr.lower():
            return ''
        raise ConfigError('cannot read current user crontab')
    return result.stdout


def update(root, mode, *, run=subprocess.run):
    old = read(run)
    tag = marker(root)
    lines = old.splitlines()
    matching = [line for line in lines if line.rstrip().endswith(tag)]
    entry = command(root)
    if mode == 'show':
        return {'status':'success','installed':matching,'proposed':entry,'scope':'current-user crontab'}
    if mode not in ('install','remove'):
        raise ConfigError('unknown cron operation')
    kept = [line for line in lines if not line.rstrip().endswith(tag)]
    if mode == 'install':
        kept.append(entry)
    new = '\n'.join(kept) + ('\n' if kept else '')
    if new != old:
        result = run(['crontab','-'],input=new,capture_output=True,text=True,check=False)
        if result.returncode:
            raise ConfigError('cannot update current user crontab')
        if read(run) != new:
            raise ConfigError('crontab update could not be verified')
    return {'status':'success','mode':mode,'entry':entry if mode=='install' else None,'changed':new!=old,
            'scope':'current-user crontab','verification':'entry read-back, not proof of a future cron execution'}
