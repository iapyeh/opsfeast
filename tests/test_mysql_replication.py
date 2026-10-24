"""Credential-free consumer/retention/runner tests; no real database or SSH."""
import copy
import contextlib
from datetime import datetime, timezone
import importlib.util
import json
import io
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
DIRECTORY = ROOT / 'recipes/database/mysql/check/replication'
from opsfeast import ConfigError, read_yaml, Validator
import recipe_contract
from recipe_inputs import prepare_vars
import retention_store as store
import retention_replay as replay
import retention_contracts
import host_vault as vault
import vault_content
import test_host_vault as vault_fixtures
from opsfeast import main as cli

main = runpy.run_path(str(DIRECTORY / 'main.py'))
probe = runpy.run_path(str(DIRECTORY / 'probe.py'))
SECRET = 'synthetic-credential-canary"\\#'


def rows_xml(rows):
    root = ET.Element('resultset')
    for values in rows:
        row = ET.SubElement(root, 'row')
        for key, value in values.items():
            field = ET.SubElement(row, 'field', name=key)
            if value is None:
                field.set('{http://www.w3.org/2001/XMLSchema-instance}nil', 'true')
            else: field.text = str(value)
    return ET.tostring(root, encoding='unicode')


def status(**updates):
    value = {'Channel_Name': '', 'Source_Host': 'source.example', 'Source_Port': '3306',
             'Replica_IO_Running': 'Yes', 'Replica_SQL_Running': 'Yes', 'Seconds_Behind_Source': '0',
             'Last_IO_Errno': '0', 'Last_SQL_Errno': '0', 'Last_IO_Error': '', 'Last_SQL_Error': '',
             'Source_Log_File': 'bin.000003', 'Read_Source_Log_Pos': '42',
             'Relay_Source_Log_File': 'bin.000003', 'Exec_Source_Log_Pos': '42', 'SQL_Delay': '0',
             'Replicate_Do_DB': 'example'}
    return dict(value, **updates)


def identity(version='8.0.46', comment='MySQL Community Server'):
    return {'version': version, 'version_comment': comment, 'hostname': 'replica',
            'server_id': '4', 'authenticated_user': 'monitor@localhost'}


class ProbeTests(unittest.TestCase):
    def collect(self, rows=None, options=None, version='8.0.46', comment='MySQL Community Server', failure=None):
        self.calls, self.paths = [], []
        options = dict({'user': 'monitor', 'password': SECRET}, **(options or {}))
        def run(argv, **kwargs):
            self.calls.append((argv, kwargs))
            path = Path(argv[1].split('=', 1)[1])
            self.paths.append(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertNotIn(SECRET, repr(argv))
            self.assertNotIn('env', kwargs)
            if failure and len(self.calls) == 2:
                if isinstance(failure, Exception): raise failure
                return SimpleNamespace(returncode=1, stdout='', stderr='ERROR 1227 secret: ' + SECRET)
            data = [identity(version, comment)] if len(self.calls) == 1 else ([status()] if rows is None else rows)
            return SimpleNamespace(returncode=0, stdout=rows_xml(data), stderr='')
        with patch('shutil.which', return_value='/usr/bin/mysql'), patch('subprocess.run', side_effect=run):
            result = probe['collect']({'options': options, 'budget': 5, 'delay': 60})
        return result

    def test_healthy_fixed_queries_and_credential_cleanup(self):
        result = self.collect()
        self.assertEqual(result['health'], 'healthy')
        self.assertEqual(result['cleanup'], 'confirmed')
        self.assertTrue(all(not p.exists() for p in self.paths))
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(self.calls[1][1]['input'], 'SHOW REPLICA STATUS;\n')
        self.assertEqual(result['channels'][0]['delay_seconds'], 0)

    def test_mariadb_all_channels_and_mysql57_statement(self):
        old = {'Connection_name': 'west', 'Master_Host': 'source.example', 'Master_Port': '3306',
               'Slave_IO_Running': 'Yes', 'Slave_SQL_Running': 'Yes', 'Seconds_Behind_Master': '0',
               'Last_IO_Errno': '0', 'Last_SQL_Errno': '0', 'Gtid_IO_Pos': '0-1-100'}
        result = self.collect([old, dict(old, Connection_name='east')], version='10.11.10-MariaDB', comment='MariaDB')
        self.assertEqual(result['health'], 'healthy')
        self.assertEqual(len(result['channels']), 2)
        self.assertEqual(self.calls[1][1]['input'], 'SHOW ALL SLAVES STATUS;\n')
        self.collect(version='5.7.44')
        self.assertEqual(self.calls[1][1]['input'], 'SHOW SLAVE STATUS;\n')

    def test_stopped_delayed_missing_and_wrong_source(self):
        for row, expected in [(status(Replica_SQL_Running='No'), 'unhealthy'),
                              (status(Seconds_Behind_Source='61'), 'unhealthy'),
                              (status(Seconds_Behind_Source=None), 'unknown'),
                              (status(Last_SQL_Errno='1062', Last_SQL_Error=SECRET), 'unhealthy')]:
            with self.subTest(expected=expected):
                result = self.collect([row]); self.assertEqual(result['health'], expected)
                self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(self.collect(options={'expected_source': 'other'})['health'], 'unhealthy')
        self.assertEqual(self.collect([])['health'], 'not_configured')
        self.assertEqual(self.collect(options={'expected_sources': {'missing': 'source'}})['reason'], 'expected_channel_missing')

    def test_timeout_permission_and_cleanup_failure_are_unknown(self):
        for failure in ('denied', subprocess.TimeoutExpired('mysql', 5)):
            result = self.collect(failure=failure)
            self.assertEqual(result['health'], 'unknown')
            self.assertNotIn(SECRET, json.dumps(result))
            self.assertTrue(all(not p.exists() for p in self.paths))
        with patch('os.unlink', side_effect=OSError):
            result = self.collect()
        self.assertEqual(result['cleanup'], 'unknown')
        self.assertEqual(result['health'], 'unknown')
        for path in set(self.paths):
            if path.exists(): path.unlink()

    def test_client_missing_unsafe_option_file_and_xml_rejection(self):
        with patch('shutil.which', return_value=None):
            result = probe['collect']({'options': {}, 'budget': 2, 'delay': 0})
        self.assertEqual(result['reason'], 'client_unavailable')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'options'; path.write_text('[client]\n'); path.chmod(0o644)
            with patch('shutil.which', return_value='/usr/bin/mysql'), patch('subprocess.run') as run:
                result = probe['collect']({'options': {'option_file': str(path)}, 'budget': 2, 'delay': 0})
            run.assert_not_called(); self.assertEqual(result['health'], 'unknown'); self.assertTrue(path.exists())
        for xml in ('<!DOCTYPE x><resultset/>', '<wrong/>', '<resultset><row>'):
            with self.assertRaises((ValueError, ET.ParseError)): probe['xml_rows'](xml)

    def test_tcp_tls_verifies_with_the_selected_client_dialect(self):
        for version_text, expected_flag in [('mysql Ver 8.0', '--ssl-mode=VERIFY_IDENTITY'),
                                            ('mysql Ver 15.1 Distrib 10.11-MariaDB', '--ssl-verify-server-cert')]:
            commands = []
            def run(argv, **kwargs):
                commands.append(argv)
                if '--version' in argv:
                    return SimpleNamespace(returncode=0, stdout=version_text, stderr='')
                self.assertIn('--protocol=TCP', argv)
                self.assertIn('--host=db.example.invalid', argv)
                self.assertIn(expected_flag, argv)
                return SimpleNamespace(returncode=0, stdout=rows_xml([identity()] if kwargs['input'].startswith('SELECT') else [status()]), stderr='')
            with patch('shutil.which', return_value='/usr/bin/mysql'), patch('subprocess.run', side_effect=run):
                result = probe['collect']({'options': {'user': 'monitor', 'password': '', 'transport': 'tcp',
                    'host': 'db.example.invalid', 'tls': {'ca': '/synthetic/ca.pem'}}, 'budget': 5, 'delay': 0})
            self.assertEqual(result['health'], 'healthy')
            self.assertEqual(len(commands), 3)
            self.assertEqual(result['probes'][0]['operation'], ['/usr/bin/mysql', '--no-defaults', '--version'])

    def test_empty_source_zero_delay_and_option_escaping(self):
        self.assertEqual(probe['channel'](status(Source_Host=''), {}, 0)['health'], 'unknown')
        self.assertEqual(probe['channel'](status(Seconds_Behind_Source='1'), {}, 0)['health'], 'unhealthy')
        self.assertEqual(probe['option_text']('a"\\#'), '"a\\"\\\\#"')
        with self.assertRaises(ValueError): probe['option_text']('line\nbreak')


class RecipeTests(unittest.TestCase):
    def test_configuration_is_validated_before_remote_execution(self):
        for options in ({'user': 'root'}, {'user': 'root', 'password': '', 'port': 3306},
                        {'option_file': '/safe', 'password': 'secret'},
                        {'user': 'root', 'password': '', 'sql': 'DELETE FROM x'},
                        {'user': 'root', 'password': '', 'transport': 'tcp'},
                        {'user': 'root', 'password': '', 'tls': {'verify': False}}):
            session = SimpleNamespace(exec_command=unittest.mock.Mock())
            result = main['execute'](SimpleNamespace(vars={'instances': {'main': options}}, session=session, timeout=10))
            self.assertEqual(result['status'], 'failed'); session.exec_command.assert_not_called()

    def test_multiple_instances_redaction_and_unknown_on_transport_failure(self):
        sample = ProbeTests().collect()
        sample['server']['hostname'] = SECRET
        session = unittest.mock.Mock()
        session.exec_command.side_effect = [SimpleNamespace(exitcode=0, stdout=json.dumps(sample), stdout_truncated=False, stderr_truncated=False), RuntimeError(SECRET)]
        result = main['execute'](SimpleNamespace(vars={'instances': {n: {'user': 'monitor', 'password': SECRET} for n in ('one', 'two')}}, session=session, timeout=10))
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['data']['instances'][1]['cleanup'], 'unknown')
        self.assertNotIn(SECRET, json.dumps(result))
        for call in session.exec_command.call_args_list:
            self.assertNotIn(SECRET, repr(call.args))
            self.assertIn(SECRET, json.loads(call.kwargs['input'])['options']['password'])

    def test_descriptor_and_host_recipe_variable_inheritance(self):
        metadata = read_yaml(DIRECTORY/'recipe.yaml')
        recipe_contract.validate(DIRECTORY, metadata)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'hosts.yaml').write_text('''default:
  recipes:
    database/mysql/check/replication:
      vars: {max_delay_seconds: 30}
hosts:
  node:
    connection: {local: true}
    recipes:
      database/mysql/check/replication:
        vars:
          instances:
            main: {user: monitor, password: "", expected_source: source.example}
''')
            config = Validator(root); config.load(root/'hosts.yaml')
            options = config.recipe_options('node', 'database/mysql/check/replication')
            values = prepare_vars(metadata, {}, options['vars'], {'max_delay_seconds': 0})
            main['configuration'](values)
            self.assertEqual(values['max_delay_seconds'], 0)
            self.assertEqual(values['instances']['main']['password'], '')

    def test_helper_nonzero_or_truncated_output_preserves_exit_and_unknown_cleanup(self):
        for exitcode, truncated in ((7, False), (0, True)):
            session = unittest.mock.Mock()
            session.exec_command.return_value = SimpleNamespace(exitcode=exitcode, stdout=SECRET,
                                                                stdout_truncated=truncated, stderr_truncated=False)
            result = main['execute'](SimpleNamespace(vars={'instances': {'main': {'user': 'monitor', 'password': SECRET}}},
                                                    session=session, timeout=10))
            item = result['data']['instances'][0]
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(item['probes'][0]['exitcode'], exitcode)
            self.assertEqual(item['cleanup'], 'unknown')
            self.assertNotIn(SECRET, json.dumps(result))


class RetentionTests(unittest.TestCase):
    setUp = vault_fixtures.VaultTests.setUp
    enable = vault_fixtures.VaultTests.enable

    def sample(self):
        metadata = read_yaml(DIRECTORY/'recipe.yaml')
        instance = ProbeTests().collect()
        instance.update(instance='main', observed_at='2026-10-24T00:00:00.000000+00:00')
        return metadata, {'host_id': 'node', 'status': 'partial', 'evidence_kind': 'ssh',
            'completed_at': instance['observed_at'], 'execution_access_mode': 'read',
            'source_observation_id': str(uuid4()),
            'recipe': {'id': metadata['id'], 'version': metadata['version'], 'reference': 'database/mysql/check/replication'},
            'data': {'instances': [instance], 'policy': {'max_delay_seconds': 60}, 'source_verification': 'not_performed'}}

    def test_structured_retention_replay_and_vault_end_to_end(self):
        self.enable()
        metadata, raw = self.sample()
        raw['retention_snapshot'] = replay.snapshot(metadata, DIRECTORY)
        receipt = store.retain_general(self.root, raw, metadata, DIRECTORY)
        self.assertIn(receipt['status'], ('retained', 'stored', 'success', 'duplicate'))
        selected = store.query(self.root, hosts=['node'])['records']
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['data']['instances'][0]['channels'][0]['delay_seconds'], 0)
        self.assertNotIn(SECRET, json.dumps(selected))
        self.assertEqual(store.retain_general(self.root, raw, metadata, DIRECTORY)['status'], 'already_stored')
        vault.rebuild(self.root)
        pages = list((self.root/'vault').rglob('*mysql-replication*.md'))
        self.assertGreaterEqual(len(pages), 2)
        current = next(p for p in pages if p.name.startswith('current-')).read_text()
        self.assertIn('source.example', current)
        self.assertIn('monitor@localhost', current)
        historical = next(p for p in pages if '/reports/' in str(p)).read_text()
        self.assertIn('SHOW REPLICA STATUS', historical)
        self.assertIn('replicate_do_db', historical)

    def test_unknown_retained_failed_excluded_and_schema_rejects_secret_keys(self):
        self.enable(); metadata, raw = self.sample()
        raw['data']['instances'][0].update(health='unknown', cleanup='unknown', reason='credential_cleanup_failed')
        store.retain_general(self.root, raw, metadata, DIRECTORY)
        record = store.query(self.root)['records'][0]
        self.assertEqual(record['data']['instances'][0]['cleanup'], 'unknown')
        raw['status'] = 'failed'
        self.assertEqual(store.retain_general(self.root, raw, metadata, DIRECTORY)['status'], 'skipped')
        altered = copy.deepcopy(record['data']); altered['instances'][0]['password'] = SECRET
        with self.assertRaises(ConfigError): retention_contracts.validate_payload(('mysql-replication', '0.1.0'), altered)

        altered = copy.deepcopy(record['data']); altered['instances'][0]['health'] = 'healthy'
        with self.assertRaises(ConfigError): retention_contracts.validate_payload(('mysql-replication', '0.1.0'), altered)

    def test_real_local_runner_and_helper_with_protocol_fixture(self):
        """Real SSHScript local processes; fake database client, no network or native SQL server."""
        self.enable()
        client = self.root/'fixture-client'
        identity_xml, status_xml = rows_xml([identity()]), rows_xml([status()])
        client.write_text('#!/usr/bin/env python3\n' +
            'import sys,os,stat\nfrom pathlib import Path\n' +
            'p=Path(sys.argv[1].split("=",1)[1])\n' +
            'assert stat.S_IMODE(p.stat().st_mode)==0o600\n' +
            'assert "password=" in p.read_text()\n' +
            'sql=sys.stdin.read()\n' +
            'assert sql in (' + repr(probe['IDENTITY_SQL']+'\n') + ', "SHOW REPLICA STATUS;\\n")\n' +
            'print(' + repr(identity_xml) + ' if sql.startswith("SELECT") else ' + repr(status_xml) + ')\n')
        client.chmod(0o700)
        values = {'instances': {'main': {'client': str(client), 'user': 'monitor', 'password': SECRET,
                                       'expected_source': 'source.example'}}}
        config = {'hosts': {'node': {'connection': {'local': True}, 'group': ['production'],
                  'recipes': {'database/mysql/check/replication': {'vars': values}}}}}
        (self.root/'hosts.yaml').write_text(json.dumps(config))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli(['recipes', 'run', 'database/mysql/check/replication', '--root', str(self.root),
                        '--host', 'node', '--json'])
        self.assertEqual(code, 0, out.getvalue())
        report = json.loads(out.getvalue())
        self.assertEqual(report['status'], 'success')
        raw = json.loads(Path(report['result_path']).read_text())
        self.assertNotIn(SECRET, json.dumps(raw))
        self.assertNotEqual(raw['retention']['status'], 'failed')
        self.assertEqual(len(store.query(self.root)['records']), 1)
        self.assertTrue(list((self.root/'vault').rglob('current-mysql-replication.md')))


if __name__ == '__main__': unittest.main()
