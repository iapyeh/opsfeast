"""Run the public shell example locally with a synthetic Core boundary."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FAKE_CORE = '''
from contextlib import contextmanager
import json
import os
import shlex
import subprocess
from types import SimpleNamespace

class Instance:
    @classmethod
    def open(cls):
        return cls()
    def profile(self, name):
        assert name == "main"
        return self
    @contextmanager
    def recipe(self, host, timeout):
        assert host == "web-01" and timeout == 60
        yield self
    @contextmanager
    def root(self):
        yield self.run
    def run(self, command, **kwargs):
        assert kwargs == {"check": False, "command_timeout": 10}
        with open(os.environ["COMMAND_RECEIPT"], "w") as stream:
            json.dump(command, stream)
        if os.environ.get("SIMULATE_FAILURE"):
            return SimpleNamespace(stdout="", stderr="", exitcode=7)
        # Reject future guide changes that would execute anything but the
        # reviewed read-only printf command in this synthetic boundary.
        argv = shlex.split(command)
        assert len(argv) == 3 and argv[:2] == ["printf", "%s"]
        assert command == shlex.join(argv)
        # The guide's only command is a read-only printf, executed locally.
        result = subprocess.run(["/bin/sh", "-c", command], capture_output=True,
                                text=True, timeout=5, check=False)
        return SimpleNamespace(stdout=result.stdout, stderr=result.stderr,
                               exitcode=result.returncode)
'''


class AgentOperationGuideTests(unittest.TestCase):
    def test_quoted_example_preserves_remote_literals_and_reports_failure(self):
        guide = (ROOT / 'docs/core-agent-operations.md').read_text()
        shell, = re.findall(r'```sh\n(.*?)\n```', guide, re.S)
        # Substitute only the selected interpreter path, not the example body.
        shell = shell.replace('./.venv/bin/python', '"$GUIDE_PYTHON"', 1)
        expected = 'limit_req_zone $binary_remote_addr zone=example:10m rate=10r/s;\n'
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                package = base / 'opsfeast'
                package.mkdir()
                (package / '__init__.py').write_text(FAKE_CORE)
                receipt = base / 'command.json'
                env = dict(os.environ, GUIDE_PYTHON=sys.executable,
                           PYTHONPATH=str(base), PYTHONDONTWRITEBYTECODE='1',
                           COMMAND_RECEIPT=str(receipt), binary_remote_addr='WRONG_LOCAL_VALUE')
                if failed:
                    env['SIMULATE_FAILURE'] = '1'
                else:
                    env.pop('SIMULATE_FAILURE', None)
                result = subprocess.run(['/bin/sh'], input=shell, cwd=base,
                                        env=env, capture_output=True, text=True,
                                        timeout=10, check=False)
                command = json.loads(receipt.read_text())
                self.assertIn('$binary_remote_addr', command)
                self.assertNotIn('WRONG_LOCAL_VALUE', command)
                if failed:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('command exited 7', result.stderr)
                    self.assertIn('Operation step: preview literal configuration', result.stderr)
                    self.assertNotIn('Operation and scope cleanup completed.', result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(expected, result.stdout)
                    self.assertIn('Operation and scope cleanup completed.', result.stdout)


if __name__ == '__main__':
    unittest.main()
