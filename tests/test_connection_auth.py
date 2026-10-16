"""Public synthetic authentication policy tests; no SSH or real credentials."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import opsfeast as ops


class ConnectionAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.resolver = Mock()
        self.resolver.resolve_connection.side_effect = self.resolve

    @staticmethod
    def resolve(host, username=None, port=None, ssh_config=None, **options):
        return dict(hostname=host, username=username or 'operator', port=port or 22, **options)

    def config(self, connection, users=None, others=None):
        hosts = dict(others or {})
        hosts['target'] = {'connection': connection, 'users': users or {}}
        (self.root / 'hosts.yaml').write_text(yaml.safe_dump({'hosts': hosts}))
        config = ops.Validator(self.root)
        config.load(self.root / 'hosts.yaml')
        config.check_connections()
        return config

    def test_boolean_combinations_with_password_and_key(self):
        for alias in (False, True):
            for agent in (False, True):
                for keys in (False, True):
                    with self.subTest(alias=alias, agent=agent, keys=keys):
                        connection = ({'ssh_config_alias': 'example'} if alias else
                                      {'hostname': 'example', 'identity_file': '/synthetic/key'})
                        connection.update(allow_agent=agent, look_for_keys=keys)
                        config = self.config(connection, {'operator': {'password': 'synthetic'}})
                        hop, = ops.connection_plan(config, 'target', self.resolver)
                        self.assertIs(hop['allow_agent'], agent)
                        self.assertIs(hop['look_for_keys'], keys)
                        self.assertEqual(hop['password'], 'synthetic')

    def test_strict_boolean_validation_including_inline_hops(self):
        for field in ('allow_agent', 'look_for_keys'):
            for value in (None, 'false', 'true', 0, 1, [], {}):
                for kind in ('explicit', 'alias', 'inline'):
                    with self.subTest(field=field, value=value, kind=kind):
                        connection = ({'ssh_config_alias': 'example'} if kind == 'alias'
                                      else {'hostname': 'example'})
                        connection[field] = value
                        if kind == 'inline':
                            connection = {'hostname': 'target', 'via': connection}
                        with self.assertRaisesRegex(ops.ConfigError, field + ': must be a Boolean'):
                            self.config(connection)

    def test_local_and_reference_connections_reject_flags(self):
        for connection in ({'local': True, 'allow_agent': False},
                           {'hostname': 'target', 'via': {'host': 'jump', 'look_for_keys': True}}):
            with self.subTest(connection=connection), self.assertRaises(ops.ConfigError):
                self.config(connection, others={'jump': {'connection': {'hostname': 'jump'}}})

    def test_defaults_false_for_password_empty_password_and_explicit_key(self):
        for password in ('synthetic', ''):
            for key in (None, '/synthetic/key'):
                with self.subTest(password=password, key=key):
                    connection = {'hostname': 'example'}
                    if key:
                        connection['identity_file'] = key
                    config = self.config(connection, {'operator': {'password': password}})
                    hop, = ops.connection_plan(config, 'target', self.resolver)
                    self.assertIs(hop['allow_agent'], False)
                    self.assertIs(hop['look_for_keys'], False)
                    self.assertEqual(hop['password'], password)
        config = self.config({'hostname': 'example', 'identity_file': '/synthetic/key'})
        hop, = ops.connection_plan(config, 'target', self.resolver)
        self.assertIs(hop['allow_agent'], False)
        self.assertIs(hop['look_for_keys'], False)

    def test_alias_identity_file_preserved_but_ambient_defaults_overridden(self):
        self.resolver.resolve_connection.return_value = None
        self.resolver.resolve_connection.side_effect = lambda *a, **kw: {
            'hostname': 'example', 'username': 'operator', 'port': 22,
            'key_filename': ['/synthetic/config-key'], 'allow_agent': True, 'look_for_keys': True}
        config = self.config({'ssh_config_alias': 'example'})
        hop, = ops.connection_plan(config, 'target', self.resolver)
        self.assertEqual(hop['key_filename'], ['/synthetic/config-key'])
        self.assertIs(hop['allow_agent'], False)
        self.assertIs(hop['look_for_keys'], False)

    def test_opt_in_without_explicit_credentials(self):
        for field in ('allow_agent', 'look_for_keys'):
            config = self.config({'hostname': 'example', field: True})
            hop, = ops.connection_plan(config, 'target', self.resolver)
            self.assertIs(hop[field], True)

    def test_each_hop_is_independent_for_inline_and_referenced_jump(self):
        jump = {'hostname': 'jump', 'allow_agent': True}
        for via in (jump, {'host': 'jump'}):
            config = self.config({'hostname': 'example', 'identity_file': '/synthetic/key', 'via': via},
                                 others={'jump': {'connection': jump}})
            first, second = ops.connection_plan(config, 'target', self.resolver)
            self.assertIs(first['allow_agent'], True)
            self.assertIs(first['look_for_keys'], False)
            self.assertIs(second['allow_agent'], False)
            self.assertIs(second['look_for_keys'], False)

    def test_no_source_is_static_valid_but_fails_before_session_creation(self):
        for connection in ({'hostname': 'example'}, {'ssh_config_alias': 'example'},
                           {'hostname': 'example', 'via': {'hostname': 'jump', 'allow_agent': True}}):
            with self.subTest(connection=connection):
                self.config(connection)
                output = io.StringIO()
                with patch.object(ops, 'load_session_class', return_value=self.resolver), \
                        contextlib.redirect_stdout(output):
                    code = ops.main(['test-connection', 'target', str(self.root), '--json'])
                report = json.loads(output.getvalue())
                self.assertEqual(code, 1)
                self.assertEqual(report['error']['stage'], 'connection settings')
                self.assertEqual(report['error']['reason'], 'missing_authentication_source')
                self.assertIn('connection.allow_agent', report['error']['hint'])
                self.resolver.assert_not_called()
                with self.assertRaisesRegex(ops.ConfigError, 'no SSH authentication source configured'):
                    config = self.config(connection)
                    ops.connection_plan(config, 'target', self.resolver)

    def test_auth_failure_does_not_retry_with_ambient_sources(self):
        self.config({'hostname': 'example', 'identity_file': '/synthetic/key'})
        local = Mock()
        local.connect.side_effect = RuntimeError('synthetic auth failure')
        self.resolver.return_value = local
        output = io.StringIO()
        with patch.object(ops, 'load_session_class', return_value=self.resolver), \
                contextlib.redirect_stdout(output):
            code = ops.main(['test-connection', 'target', str(self.root), '--json'])
        self.assertEqual(code, 1)
        local.connect.assert_called_once()
        self.assertIs(local.connect.call_args.kwargs['allow_agent'], False)
        self.assertIs(local.connect.call_args.kwargs['look_for_keys'], False)


if __name__ == '__main__':
    unittest.main()
