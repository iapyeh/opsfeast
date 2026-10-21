"""Purpose-first CLI help must be useful without profiles, connections or writes."""
from recipe_test_support import recipe_main
import argparse
from contextlib import ExitStack, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import opsfeast
from cli_help import TaskHelpFormatter
import observation_store
import recipe_runner as run_recipe


class CommandHelpTests(unittest.TestCase):
    def help(self, arguments, entry=opsfeast.main):
        output = io.StringIO()
        with ExitStack() as stack:
            for name in ('opsfeast.resolve_root', 'opsfeast.load_session_class', 'recipe_cli.resolve_root',
                         'recipe_cli.execute', 'retention_store.resolve_root', 'retention_store.refresh_content',
                         'retention_consumers.resolve_root', 'retention_consumers.dispatch',
                         'host_vault.resolve_root', 'host_vault.rebuild', 'observation_store.resolve_root',
                         'recipe_cli.resolve_root', 'recipe_runner.load_runtime', 'terminal_ui.launch'):
                stack.enter_context(patch(name, side_effect=AssertionError('help must not perform work')))
            stack.enter_context(redirect_stdout(output))
            with self.assertRaises(SystemExit) as exit:
                entry([*arguments, '--help'])
        self.assertEqual(exit.exception.code, 0, output.getvalue())
        return output.getvalue()

    def description(self, help_text):
        # Restrict assertions to the prose after usage and before argument listings.
        prose = help_text.split('\n\n', 1)[1]
        for heading in ('\npositional arguments:', '\noptions:'):
            prose = prose.split(heading, 1)[0]
        return ' '.join(prose.split())

    def test_root_help_groups_all_commands_once_in_task_order(self):
        text = self.help([])
        groups = (
            ('Profiles and setup', ('init', 'profiles', 'use', 'attach', 'detach', 'instance')),
            ('Hosts and access (hosts.yaml)',
             ('check', 'dump', 'test-connection', 'host-init', 'test-host', 'test-su', 'test-sudo', 'check-access')),
            ('Recipes and reports', ('inspect-recipe', 'recipes')),
            ('Retained data and consumers', ('observation', 'retention', 'consumers')),
            ('Vault content', ('vault',)),
        )
        self.assertTrue(text.startswith('usage: opsfeast.py [-h] COMMAND ...'))
        self.assertIn('Commands by task:', text)
        self.assertNotIn('positional arguments:', text)
        positions = [text.index(title + ':') for title, _ in groups]
        self.assertEqual(positions, sorted(positions))
        for index, (_, names) in enumerate(groups):
            end = positions[index + 1] if index + 1 < len(groups) else len(text)
            for name in names:
                marker = '\n    ' + name + ' '
                self.assertEqual(text.count(marker), 1, name)
                self.assertIn(marker, text[positions[index]:end], name)
        prose = ' '.join(text.split())
        self.assertIn('commands can be reused at any stage', prose)
        self.assertIn('saved data without a new collection', prose)

    def test_task_groups_do_not_change_leaf_help(self):
        for arguments in (['recipes', 'run'], ['check-access']):
            with self.subTest(arguments=arguments):
                text = self.help(arguments)
                self.assertNotIn('Commands by task:', text)
                self.assertNotIn('Profiles and setup:', text)
                self.assertTrue(text.startswith('usage: opsfeast.py ' + ' '.join(arguments)))
                self.assertIn('--host', text)

    def test_formatter_keeps_unassigned_commands_visible_and_parsing_unchanged(self):
        parser = argparse.ArgumentParser(prog='example', formatter_class=TaskHelpFormatter)
        commands = parser.add_subparsers(dest='command', metavar='COMMAND', title='Tasks')
        commands.help_groups = (('Setup', ('known', 'missing')), ('Later', ('known',)))
        commands.add_parser('known', aliases=['k'], help='create a local setup')
        commands.add_parser('extra', help='inspect saved data')
        text = parser.format_help()
        self.assertEqual(text.count('known (k)'), 1)
        self.assertNotIn('Later:', text)
        self.assertIn('Other commands:', text)
        self.assertGreater(text.index('extra '), text.index('Other commands:'))
        self.assertIn('-h, --help', text)
        self.assertEqual(parser.parse_args(['known']).command, 'known')
        self.assertEqual(parser.parse_args(['k']).command, 'k')
        self.assertEqual(parser.parse_args(['extra']).command, 'extra')

    def test_recipes_run_explains_operations_reports_storage_and_examples(self):
        help_text = self.help(['recipes', 'run'])
        prose = self.description(help_text)
        self.assertIn('Run one selected recipe', prose)
        for meaning in ('selected hosts', 'configured sessions', 'Raw results', 'declared data',
                        'enabled consumers', 'Offline report recipes', 'without host collection'):
            self.assertIn(meaning, prose)
        self.assertIn('Examples:', help_text)
        self.assertIn('system/network/check/port', help_text)
        self.assertIn('feast/report/retention-summary', help_text)
        self.assertIn('check-access for connection and privilege diagnostics', help_text)
        self.assertIn('--vars-file', help_text)

    def test_parent_help_summarizes_recipe_and_job_commands(self):
        recipes = self.help(['recipes'])
        self.assertIn('host operations or offline reports', self.description(recipes))
        for meaning in ('discover available recipes', 'inspect one recipe', 'execute one host-operation',
                        'browse saved execution', 'package explicitly', 'save and reuse'):
            self.assertIn(meaning, recipes)
        jobs = self.help(['recipes', 'jobs'])
        self.assertIn('does not execute it or create a schedule', self.description(jobs))
        self.assertIn('verify and execute', jobs)

    def test_recipe_subcommands_describe_their_actual_effects(self):
        cases = {
            ('list',): ('metadata', 'no recipe is executed'),
            ('show',): ('purpose', 'static inspection'),
            ('results',): ('previously saved', 'No recipe is rerun'),
            ('artifact',): ('JSON metadata', 'absolute file path'),
            ('pack',): ('file allowlist', 'does not execute'),
            ('unpack',): ('candidate directory', 'does not register'),
            ('jobs', 'save'): ('fingerprint', 'does not connect'),
            ('jobs', 'list'): ('named jobs', 'without running'),
            ('jobs', 'show'): ('saved job definition', 'does not run'),
            ('jobs', 'run'): ('Verify', 'then execute'),
        }
        for arguments, meanings in cases.items():
            with self.subTest(arguments=arguments):
                prose = self.description(self.help(['recipes', *arguments]))
                for meaning in meanings:
                    self.assertIn(meaning, prose)

    def test_main_commands_explain_configuration_and_connection_scope(self):
        cases = {
            'profiles': ('registered', 'without connecting'),
            'instance': ('UUID', 'without moving files'),
            'inspect-recipe': ('declared platform', 'without executing recipe code'),
            'use': ('default', 'profile registry'),
            'attach': ('register', 'preserves'),
            'detach': ('preserving all files', 'main is protected'),
            'init': ('local setup', 'without connecting'),
            'check': ('Validate hosts.yaml', 'without testing connectivity'),
            'dump': ('not masked', 'credentials'),
            'test-connection': ('Connect', 'hostname/date'),
            'host-init': ('platform facts', 'local cache'),
            'test-su': ('su to declared accounts', 'cleanup evidence'),
            'test-sudo': ('Other actors require su first', '--run-as'),
            'test-host': ('reuse valid platform facts', 'independent su'),
            'check-access': ('per-account identity', 'without collecting inventory'),
        }
        for command, meanings in cases.items():
            with self.subTest(command=command):
                prose = self.description(self.help([command]))
                for meaning in meanings:
                    self.assertIn(meaning, prose)
        self.assertIn('retained data', self.description(self.help([])))

    def test_data_command_help_distinguishes_reading_writing_and_dispatch(self):
        for arguments, meanings in (
            (['retention', 'ingest'], ('saved raw results', 'enabled retention consumers', 'Actions:', 'delete-observation')),
            (['vault', 'rebuild'], ('manifest-owned', 'unmanaged human notes', 'group membership')),
            (['consumers', 'dispatch'], ('reviewed local programs', 'individual failed attempts', 'at least once')),
        ):
            with self.subTest(arguments=arguments):
                help_text = ' '.join(self.help(arguments).split())
                for meaning in meanings:
                    self.assertIn(meaning, help_text)

    def test_standalone_runner_and_exchange_tools_have_purpose_descriptions(self):
        prose = self.description(self.help(['recipes','run']))
        self.assertIn('selected hosts', prose)
        self.assertIn('Offline report', prose)
        for command, meanings in (
            ('ingest', ('saved raw', 'does not reconnect')),
            ('export', ('stdout', 'no recipient')),
            ('validate', ('saved exchange file', 'does not import')),
            ('combine', ('deduplicate', 'does not merge into a Feast')),
        ):
            with self.subTest(command=command):
                prose = self.description(self.help([command], observation_store.main))
                for meaning in meanings:
                    self.assertIn(meaning, prose)

    def test_nested_usage_includes_the_complete_command_path(self):
        for arguments in (['recipes'], ['recipes', 'run'], ['recipes', 'jobs'], ['recipes', 'jobs', 'save'],
                          ['recipes', 'jobs', 'run'], ['retention'], ['vault'], ['consumers']):
            with self.subTest(arguments=arguments):
                self.assertTrue(self.help(arguments).startswith('usage: opsfeast.py ' + ' '.join(arguments)))

    def test_help_takes_priority_over_optional_ui_launch(self):
        for arguments in (['recipes', 'run', '--tui'], ['--tui', 'recipes', 'run']):
            with self.subTest(arguments=arguments):
                text = self.help(arguments)
                self.assertTrue(text.startswith('usage: opsfeast.py recipes run'))
                self.assertIn('Run one selected recipe', self.description(text))
        self.assertIn('selected hosts', self.description(self.help(['recipes','run','--tui'])))

    def test_real_help_from_an_empty_directory_needs_no_profile_or_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ)
            package_root = str(Path(opsfeast.__file__).resolve().parents[1])
            environment['PYTHONPATH'] = os.pathsep.join(filter(None, [package_root, environment.get('PYTHONPATH')]))
            result = subprocess.run([sys.executable, '-B', '-m', 'opsfeast', 'recipes', 'run', '-h'],
                                    cwd=directory, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Run one selected recipe', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
