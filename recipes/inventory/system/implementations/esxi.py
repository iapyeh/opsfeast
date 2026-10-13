"""ESXi system inventory via read-only shell commands; synthetic verification only."""
from pathlib import Path
import runpy

VERSION = '0.1.0'
common = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'))


def collect(session, report, timeout, facts, *, context=None):
    if context is not None:
        timeout = context.vars.get('command_timeout_seconds', timeout)
    common['observe'](report, 'platform', 'esxi', 'success', ['host-init'])
    common['observe'](report, 'system_name', 'VMware ESXi', 'success', ['host-init'])
    for field, argv in (('hostname', ['uname', '-n']), ('kernel_name', ['uname', '-s']),
                        ('kernel_release', ['uname', '-r']), ('architecture', ['uname', '-m']),
                        ('system_version', ['vmware', '-v'])):
        source, state = common['probe'](session, report, field, argv, timeout)
        value = None
        if state == 'success':
            try:
                value = common['one_line'](source['stdout'])
            except ValueError:
                state = 'parsing_failed'
        common['observe'](report, field, value, state, [source['id']])
    return report
