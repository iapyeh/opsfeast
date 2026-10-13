"""Public onboarding checks with temporary settings and a synthetic activation file."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FirstHostExamplesTests(unittest.TestCase):
    def test_all_complete_yaml_examples_pass_configuration_check(self):
        examples = re.findall(r'```yaml\n(.*?)\n```', (ROOT / 'docs/first-host.md').read_text(), re.S)
        self.assertEqual(len(examples), 7)
        with tempfile.TemporaryDirectory() as directory:
            for example in examples:
                with self.subTest(example=example.splitlines()[1]):
                    Path(directory, 'hosts.yaml').write_text(example + '\n')
                    result = subprocess.run(
                        [sys.executable, '-B', str(ROOT / 'tools/opsfeast.py'), 'check', directory],
                        capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_init_marks_remote_example_as_unconfigured(self):
        with tempfile.TemporaryDirectory() as directory:
            # Copy tools to keep the generated registry out of the real checkout.
            shutil.copytree(ROOT / 'tools', Path(directory, 'tools'), ignore=shutil.ignore_patterns('__pycache__'))
            result = subprocess.run([sys.executable, '-B', str(Path(directory, 'tools/opsfeast.py')), 'init'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = Path(directory, 'feasts/main/hosts.yaml').read_text()
            self.assertIn('NOT ready to connect', text)
            self.assertIn('docs/first-host.md', text)


class ActivationTests(unittest.TestCase):
    def test_activation_from_other_directory_and_failures(self):
        for shell in ('bash', 'zsh'):
            executable = shutil.which(shell)
            if not executable:
                continue
            with self.subTest(shell=shell), tempfile.TemporaryDirectory(prefix='ops onboarding ') as directory:
                checkout = Path(directory, 'clone with spaces')
                tools = checkout / 'tools'
                tools.mkdir(parents=True)
                helper = tools / 'activate.sh'
                shutil.copyfile(ROOT / 'tools/activate.sh', helper)
                env = dict(os.environ)
                env.pop('PYTHONDONTWRITEBYTECODE', None)
                env.pop('VIRTUAL_ENV', None)
                # Missing environment must not activate anything or set the export.
                missing = subprocess.run([executable, '-c',
                    'source "$1"; result=$?; test "$result" -ne 0 && '
                    'test -z "${PYTHONDONTWRITEBYTECODE:-}" && test -z "${VIRTUAL_ENV:-}"',
                    'test', str(helper)], cwd=directory, env=env, capture_output=True, text=True)
                self.assertEqual(missing.returncode, 0, missing.stderr)
                activation = checkout / '.venv/bin/activate'
                activation.parent.mkdir(parents=True)
                activation.write_text('export VIRTUAL_ENV="synthetic-activated"\n')
                result = subprocess.run([executable, '-c',
                    'before=$PWD; source "$1" || exit 10; '
                    'test "$PWD" = "$before" && test "$VIRTUAL_ENV" = synthetic-activated && '
                    'test "$PYTHONDONTWRITEBYTECODE" = 1', 'test', str(helper)],
                    cwd=directory, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                executed = subprocess.run([executable, str(helper)], cwd=directory, env=env,
                                          capture_output=True, text=True)
                self.assertNotEqual(executed.returncode, 0)
                self.assertIn('Use source', executed.stderr)
                activation.write_text('return 7\n')
                failed = subprocess.run([executable, '-c',
                    'source "$1"; result=$?; test "$result" -ne 0 && '
                    'test -z "${PYTHONDONTWRITEBYTECODE:-}"', 'test', str(helper)],
                    cwd=directory, env=env, capture_output=True, text=True)
                self.assertEqual(failed.returncode, 0, failed.stderr)


if __name__ == '__main__':
    unittest.main()
