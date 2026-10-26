"""Backup recipe: native local scans, boundaries, retained replay and services."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opsfeast import Instance, ConfigError
from opsfeast import backup_check
from test_core_api import Actor
import recipe_runner
import retention_store
import retention_consumers
from retention_replay import ingest
from backup_retention import validate

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "VERSION = '0.1.0'\nfrom opsfeast.backup_check import execute as check_backups\ndef execute(recipe):\n    return check_backups(recipe)\n"


class LocalScanActor(Actor):
    def exec_command(self, argv, **kwargs):
        if len(argv) > 2 and argv[1:2] == ['-c']:
            result = subprocess.run(argv, input=kwargs['input'], text=True, capture_output=True, timeout=10)
            return SimpleNamespace(stdout=result.stdout, stderr=result.stderr, exitcode=result.returncode,
                                   stdout_truncated=False, stderr_truncated=False)
        return super().exec_command(argv, **kwargs)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.directory = self.base / 'backups'
        self.directory.mkdir()
        self.variables = dict(timezone='Asia/Taipei', retention_days=90, target_python=sys.executable,
            backups=[{'name':'db','directory':str(self.directory),'patterns':['{date}.sql','{date}.myrpki.tar.gz']}])
        self.fixed = datetime(2026,10,25,1,0,tzinfo=timezone.utc)
        self.actor = LocalScanActor()

    def touch(self, name):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic data')

    def execute(self, **overrides):
        recipe = SimpleNamespace(vars=dict(self.variables, **overrides), timeout=10, session=self.actor)
        with patch.object(backup_check, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = self.fixed
            return backup_check.execute(recipe)

    def test_presence_expired_strict_boundary_and_unexpected(self):
        for name in ('2026-10-25.sql','2026-10-25.myrpki.tar.gz','2026-07-26.sql',
                     '2026-07-27.sql','2026-02-30.sql','human-note.txt'):
            self.touch(name)
        result = self.execute()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['assessment']['label'], 'BACKUPS OK · CLEANUP NEEDED')
        self.assertEqual(result['assessment']['severity'], 'warning')
        group = result['data']['backups'][0]
        self.assertEqual(group['health'], 'healthy')
        self.assertEqual([x['path'] for x in group['expired_files']], ['2026-07-26.sql'])
        self.assertEqual({x['path'] for x in group['unexpected_entries']}, {'2026-02-30.sql','human-note.txt'})
        self.assertTrue((self.directory / 'human-note.txt').exists())

    def test_missing_files_and_before_deadline(self):
        self.assertEqual(self.execute()['data']['backups'][0]['health'], 'missing')
        self.variables['backups'][0].update(ready_after='10:00', grace_minutes=5)
        self.assertEqual(self.execute()['data']['backups'][0]['health'], 'pending')

    def test_symlinks_not_followed_and_approved_subdirectory(self):
        self.variables['backups'][0]['patterns'] = ['twnicrms-{date}.tgz','db/rmsbackup-{date}.sql']
        self.touch('twnicrms-2026-10-25.tgz')
        self.touch('db/rmsbackup-2026-10-25.sql')
        (self.directory / 'linked').symlink_to(self.base, target_is_directory=True)
        group = self.execute()['data']['backups'][0]
        self.assertEqual(group['health'], 'healthy')
        self.assertEqual([e['path'] for e in group['unexpected_entries']], ['linked'])

    def test_scan_limit_and_unreadable_do_not_establish_absence(self):
        self.touch('one')
        self.touch('two')
        group = self.execute(max_entries=1)['data']['backups'][0]
        self.assertEqual(group['health'], 'unknown')
        self.assertEqual(group['expected_files'][0]['present'], None)
        self.variables['backups'][0]['directory'] = str(self.base / 'missing')
        self.assertEqual(self.execute()['data']['backups'][0]['scan_status'], 'incomplete')

    def test_timeout_truncation_and_invalid_output_are_unknown_not_empty_success(self):
        for output in (SimpleNamespace(stdout='[]',stderr='',exitcode=0,stdout_truncated=True,stderr_truncated=False),
                       SimpleNamespace(stdout='not json',stderr='',exitcode=0,stdout_truncated=False,stderr_truncated=False)):
            with patch.object(self.actor, 'exec_command', return_value=output):
                self.assertEqual(self.execute()['data']['backups'][0]['health'], 'unknown')
        with patch.object(self.actor, 'exec_command', side_effect=TimeoutError('private text')):
            result = self.execute()
            self.assertEqual(result['status'], 'partial')
            self.assertNotIn('private text', json.dumps(result))

    def test_invalid_inputs_fail_before_execution(self):
        for values in ({'retention_days':True},{'timezone':'bad/zone'}, {'retention_days':-1}):
            with patch.object(self.actor, 'exec_command', side_effect=AssertionError('must not execute')):
                with self.assertRaises(ConfigError):
                    self.execute(**values)
        self.variables['backups'][0]['patterns'] = ['../{date}.sql']
        with self.assertRaises(ConfigError):
            self.execute()

    def test_taipei_date_zero_length_presence_and_configurable_age(self):
        self.fixed = datetime(2026,10,24,17,10,tzinfo=timezone.utc)
        for name in ('2026-10-25.sql','2026-10-25.myrpki.tar.gz','2026-10-24.sql'):
            self.touch(name)
        (self.directory/'2026-10-25.sql').write_bytes(b'')
        result = self.execute(retention_days=0)
        self.assertEqual(result['data']['check_date'], '2026-10-25')
        self.assertEqual(result['data']['backups'][0]['health'], 'healthy')
        self.assertEqual([e['path'] for e in result['data']['backups'][0]['expired_files']], ['2026-10-24.sql'])

    def setup_profile(self):
        with redirect_stdout(io.StringIO()):
            self.profile = Instance.open(self.base).init_profile()
        self.root = self.profile.root
        self.recipe_directory = self.root / 'recipes/backup/files/check/daily-backups'
        self.recipe_directory.mkdir(parents=True)
        self.metadata = backup_check.descriptor({'author':{'name':'Synthetic','contacts':['tests@example.invalid']}, 'license':'MIT'})
        (self.recipe_directory / 'recipe.yaml').write_text(json.dumps(self.metadata))
        (self.recipe_directory / 'main.py').write_text(ENTRY)
        shutil.copy(ROOT / 'schemas/backup-files-check.schema.json', self.recipe_directory)
        self.reference = ':backup/files/check/daily-backups'
        (self.root / 'hosts.yaml').write_text(json.dumps({'hosts':{'h':{'connection':{'local':True},
            'recipes':{self.reference:{'enabled':True,'vars':self.variables}}}}}))
        import yaml
        definition = self.root / 'feast.yaml'
        settings = yaml.safe_load(definition.read_text())
        settings['consumers'] = {'backup-check':{'source':'builtin:backup-check','enabled':True}}
        definition.write_text(yaml.safe_dump(settings))

    def run_recipe(self):
        with patch.object(recipe_runner, 'REPOSITORY_ROOT', self.base):
            return recipe_runner.run(self.root, 'h', recipe=self.reference,
                session_class=lambda:self.actor, runtime={'sshscript':'synthetic-transport'})

    def test_real_runner_retention_vault_todo_and_replay(self):
        self.setup_profile()
        today = datetime.now(timezone.utc).astimezone(backup_check.ZoneInfo('Asia/Taipei')).date().isoformat()
        for suffix in ('.sql','.myrpki.tar.gz'):
            self.touch(today + suffix)
        self.touch('2020-01-01.sql')
        report, path = self.run_recipe()
        self.assertEqual(report['status'], 'success', report)
        self.assertEqual(report['retention']['status'], 'stored', report)
        self.assertEqual(report['content_update']['status'], 'success', report)
        retained = self.profile.retention.query()['records'][0]
        validate(retained['data'])
        todos = self.profile.services.todos.list()
        self.assertEqual(len(todos), 1)
        self.assertEqual(todos[0]['source']['rule'], 'expired-files')
        self.assertFalse(self.profile.services.notifications.list())
        pages = list((self.root/'vault').rglob('current-daily-backups.md'))
        self.assertEqual(len(pages), 1)
        self.assertIn('2020-01-01.sql', pages[0].read_text())
        record_id = retained['record_id']
        history_count = len(self.profile.services.history())
        self.assertEqual(ingest(self.root, [path])['status'], 'success')
        self.assertEqual(len(self.profile.services.history()), history_count)
        # Simulate lost content delivery ack: a re-run still reconciles idempotently.
        retention_consumers.dispatch(self.root)
        self.assertEqual(len(self.profile.services.todos.list()), 1)
        self.assertEqual(self.profile.services.todos.list()[0]['evidence']['record_id'], record_id)
        from host_vault import observation_report_locations
        expected_report = observation_report_locations(self.root, [record_id])[record_id]
        todo_page = self.root/'vault/Services/todo'/ (todos[0]['id']+'.md')
        import re
        from urllib.parse import unquote
        link = re.search(r'\[Source observation report\]\(([^)]+)\)', todo_page.read_text()).group(1)
        self.assertEqual((todo_page.parent/unquote(link)).resolve(), Path(expected_report).resolve())
        import copy
        corrupted = copy.deepcopy(retained['data'])
        corrupted['backups'][0]['expired_files'][0]['age_days'] = 1
        with self.assertRaises(ConfigError):
            validate(corrupted)

    def test_missing_creates_notification_recovery_verifies_todo(self):
        self.setup_profile()
        self.touch('2020-01-01.sql')
        report, _ = self.run_recipe()
        self.assertEqual(report['status'], 'partial', report)
        self.assertEqual(len(self.profile.services.notifications.list()), 1)
        # A later successful observation resolves missing and cleanup conditions.
        (self.directory/'2020-01-01.sql').unlink()
        today = datetime.now(timezone.utc).astimezone(backup_check.ZoneInfo('Asia/Taipei')).date().isoformat()
        for suffix in ('.sql','.myrpki.tar.gz'):
            self.touch(today + suffix)
        self.run_recipe()
        self.assertEqual(self.profile.services.notifications.list()[0]['status'], 'resolved')
        self.assertTrue(self.profile.services.todos.list()[0]['verified'])

    def test_historical_replay_into_fresh_profile_has_no_notifications_or_todos(self):
        self.setup_profile()
        self.touch('2020-01-01.sql')
        _, path = self.run_recipe()
        with redirect_stdout(io.StringIO()):
            receiver = self.profile.instance.init_profile('receiver')
        (receiver.root/'hosts.yaml').write_bytes((self.root/'hosts.yaml').read_bytes())
        # Receiver recipe path must exist for its host-level reference validation.
        shutil.copytree(self.root/'recipes', receiver.root/'recipes', dirs_exist_ok=True)
        import yaml
        definition = receiver.root/'feast.yaml'
        settings = yaml.safe_load(definition.read_text())
        settings['consumers'] = {'backup-check':{'source':'builtin:backup-check','enabled':True}}
        definition.write_text(yaml.safe_dump(settings))
        self.assertEqual(ingest(receiver.root, [path])['status'], 'success')
        self.assertEqual(len(receiver.retention.query()['records']), 1)
        self.assertFalse(receiver.services.notifications.list())
        self.assertFalse(receiver.services.todos.list())


if __name__ == '__main__':
    unittest.main()
