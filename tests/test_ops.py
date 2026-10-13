"""Public, synthetic validation cases; no SSH or private host data."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('opsfeast_test', Path(__file__).parents[1] / 'tools/opsfeast.py')
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


class OpsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'feasts'
        self.root.mkdir()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def check(self):
        return ops.Validator(self.root).check()

    def test_init_preserves_existing_content(self):
        ops.initialize(self.root)
        path = self.root / 'hosts.yaml'
        original = path.read_bytes()
        data = ops.read_yaml(path)
        self.assertEqual(list(data['hosts']), ['localhost', 'host-01'])
        self.assertEqual(data['hosts']['localhost']['connection'], {'local': True})
        self.assertEqual(data['hosts']['host-01']['connection'], {'hostname': 'host.example'})
        self.assertEqual(len(self.check().hosts), 2)
        path.write_text('hosts: {}\n# user note\n')
        ops.initialize(self.root)
        self.assertEqual(path.read_text(), 'hosts: {}\n# user note\n')
        self.assertIn(b'via:', original)
        self.assertFalse((self.root / 'recipes').exists())
        self.assertTrue(all((self.root / name).is_dir() for name in ('hosts', 'observations', 'records', 'runs')))

    def test_default_init_and_commands_from_other_cwd(self):
        with patch.object(ops, 'REPOSITORY_ROOT', Path(self.temp.name)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ops.main(['init']), 0)
            self.assertEqual(ops.read_yaml(self.root / 'main/feast.yaml'), ops.INSTANCE_SCHEMA)
            self.assertEqual(ops.read_yaml(Path(self.temp.name) / '.opsfeast.yaml')['profiles']['main']['root'], 'feasts/main')
            # Locator resolution never depends on the invoking shell directory.
            with contextlib.chdir('/'):
                self.assertEqual(ops.resolve_root(), (self.root / 'main').resolve())
                self.assertEqual(ops.main(['check']), 0)
                self.assertEqual(ops.main(['dump', 'hosts.localhost']), 0)
                session_class, local, remote = self.session_double()
                with patch.object(ops, 'load_session_class', return_value=session_class):
                    self.assertEqual(ops.main(['test-connection', 'localhost']), 0)
                local.connect.assert_not_called()

    def test_custom_init_remembered_and_explicit_override(self):
        checkout = Path(self.temp.name) / 'checkout'
        checkout.mkdir()
        other = Path(self.temp.name) / 'custom'
        with patch.object(ops, 'REPOSITORY_ROOT', checkout), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ops.main(['init', str(other)]), 0)
            self.assertEqual(ops.resolve_root(), other.resolve())
            self.assertEqual(ops.resolve_root(self.root), self.root)
            # New init registers main without switching the existing selection.
            self.assertEqual(ops.main(['init']), 0)
            self.assertEqual(ops.resolve_root(), other.resolve())
            self.assertEqual(ops.resolve_root(profile='main'), (checkout / 'feasts/main').resolve())

    def test_failed_init_does_not_switch_default(self):
        with patch.object(ops, 'REPOSITORY_ROOT', Path(self.temp.name)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ops.main(['init']), 0)
            pointer = Path(self.temp.name) / '.opsfeast.yaml'
            original = pointer.read_bytes()
            other = Path(self.temp.name) / 'broken'
            other.mkdir()
            (other / 'hosts.yaml').write_text('hosts: []')
            self.assertEqual(ops.main(['init', str(other)]), 1)
            self.assertEqual(pointer.read_bytes(), original)

    def test_default_missing_or_invalid_definition_fails_without_fallback(self):
        with patch.object(ops, 'REPOSITORY_ROOT', Path(self.temp.name)):
            with self.assertRaises(ops.ConfigError):
                ops.resolve_root()
            ops.initialize(self.root)
            (Path(self.temp.name) / '.opsfeast.yaml').write_text('schema_version: 1\nroot: feasts\n')
            self.write('feast.yaml', 'schema_version: true\nkind: opsfeast\n')
            with self.assertRaisesRegex(ops.ConfigError, 'unsupported management'):
                ops.resolve_root()
            self.write('feast.yaml', 'schema_version: 1\nkind: opsfeast\n')
            pointer = Path(self.temp.name) / '.opsfeast.yaml'
            pointer.write_text('schema_version: 1\nroot: missing\n')
            with self.assertRaisesRegex(ops.ConfigError, 'not found'):
                ops.resolve_root()
            pointer.write_text('schema_version: 1\nroot: [invalid]\n')
            with self.assertRaises(ops.ConfigError):
                ops.resolve_root()

    def test_definition_preserved_and_symlink_rejected_before_scaffolding(self):
        definition = self.write('feast.yaml', '# note\nschema_version: 1\nkind: opsfeast\n')
        ops.initialize(self.root)
        self.assertTrue(definition.read_text().startswith('# note'))
        definition.unlink()
        outside = Path(self.temp.name) / 'definition.yaml'
        outside.write_text('schema_version: 1\nkind: opsfeast\n')
        definition.symlink_to(outside)
        with self.assertRaisesRegex(ops.ConfigError, 'scaffold symlink'):
            ops.initialize(self.root)

    def test_cross_file_reference_and_relative_recipe(self):
        self.write('hosts.yaml', 'include: [hosts/jump.yaml, hosts/web.yaml]\n')
        self.write('hosts/jump.yaml', 'hosts: {jump: {connection: {hostname: jump.example}}}\n')
        self.write('hosts/web.yaml', 'hosts:\n  web:\n    connection: {hostname: web.internal, via: {host: jump}}\n    recipes: [{recipe: ../recipes/basic}]\n')
        recipe = self.write('recipes/basic/recipe.yaml', 'id: inventory.basic\n').parent
        result = self.check()
        self.assertEqual(result.edges['web'], ['jump'])
        self.assertEqual(result.selected['web'], [recipe.resolve()])

    def test_checkout_recipes_work_from_included_yaml_without_copy(self):
        self.write('hosts.yaml', 'include: [hosts/web.yaml]\n')
        self.write('hosts/web.yaml', 'hosts: {web: {connection: {local: true}, recipes: [{recipe: recipes/inventory/system}]}}')
        self.assertEqual(self.check().selected['web'], [ops.REPOSITORY_RECIPES / 'inventory/system'])
        self.assertFalse((self.root / 'recipes').exists())

    def test_checkout_glob_directory_and_dedup(self):
        for selector in ('{directory: recipes/inventory}', '{directory: recipes, recursive: true}',
                         '{glob: "recipes/**/system"}'):
            with self.subTest(selector=selector):
                self.write('hosts.yaml', f'hosts: {{web: {{connection: {{local: true}}, recipes: [{selector}, {{recipe: recipes/inventory/system}}]}}}}')
                expected = ([ops.REPOSITORY_RECIPES / 'check/port', ops.REPOSITORY_RECIPES / 'inventory/system']
                            if selector == '{directory: recipes, recursive: true}' else [ops.REPOSITORY_RECIPES / 'inventory/system'])
                self.assertEqual(self.check().selected['web'], expected)

    def test_checkout_boundary_does_not_allow_include_or_recipe_escape(self):
        for recipe in ('recipes/../../outside', 'recipes/../tools', 'recipes/../tools/*'):
            with self.subTest(recipe=recipe):
                self.write('hosts.yaml', f'hosts: {{web: {{connection: {{local: true}}, recipes: [{{glob: "{recipe}"}}]}}}}')
                with self.assertRaises(ops.ConfigError):
                    self.check()
        self.write('hosts.yaml', f'include: [{ops.REPOSITORY_ROOT / "recipes/inventory/system/recipe.yaml"}]')
        with self.assertRaisesRegex(ops.ConfigError, 'outside management root'):
            self.check()

    def test_checkout_recipe_never_uses_same_named_instance_copy(self):
        self.write('recipes/inventory/system/recipe.yaml', 'id: different\n')
        self.write('hosts.yaml', 'hosts: {web: {connection: {local: true}, recipes: [{recipe: recipes/inventory/system}]}}')
        self.assertEqual(self.check().selected['web'], [ops.REPOSITORY_RECIPES / 'inventory/system'])

    def test_dump_merged_hosts_and_nested_values(self):
        self.write('hosts.yaml', 'include: [hosts/web.yaml]\nhosts: {localhost: {connection: {local: true}}}')
        self.write('hosts/web.yaml', '''hosts:
  host-01:
    connection: {hostname: host.example}
    vars: {label: 測試, enabled: true, count: 2, empty: null}
    recipes: [{recipe: ./recipes/not-installed}]
''')
        expected = self.check_loaded_hosts()
        for setting, value in (
            ('include', ['hosts/web.yaml']),
            ('hosts', expected), ('hosts.host-01', expected['host-01']),
            ('hosts.host-01.vars', expected['host-01']['vars']),
            ('hosts.host-01.vars.empty', None),
        ):
            with self.subTest(setting=setting):
                output, errors = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    code = ops.main(['dump', setting, str(self.root)])
                self.assertEqual(code, 0)
                self.assertEqual(errors.getvalue(), '')
                self.assertEqual(output.getvalue(), json.dumps(value, indent=4, ensure_ascii=False) + '\n')

    def check_loaded_hosts(self):
        result = ops.Validator(self.root)
        result.load(self.root / 'hosts.yaml')
        return result.hosts

    def test_dump_errors_have_no_partial_output(self):
        cases = (
            ('hosts: {a: {connection: {hostname: a}}}', 'hosts.missing'),
            ('hosts: {a: {connection: {hostname: a}}}', 'hosts..a'),
            ('hosts: {a: {vars: {date: 2026-10-10}}}', 'hosts'),
            ('hosts: {a: {vars: {value: .nan}}}', 'hosts'),
            ('hosts: {a: {vars: &v {self: *v}}}', 'hosts'),
            ('hosts: {}\nhosts: {}', 'hosts'),
        )
        for content, setting in cases:
            with self.subTest(content=content, setting=setting):
                self.write('hosts.yaml', content)
                output, errors = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    code = ops.main(['dump', setting, str(self.root)])
                self.assertEqual(code, 1)
                self.assertEqual(output.getvalue(), '')
                self.assertTrue(errors.getvalue().startswith('ERROR: '))

    def test_self_via_cycle(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a, via: {host: a}}}}')
        with self.assertRaisesRegex(ops.ConfigError, 'via cycle: a -> a'):
            self.check()

    def test_indirect_nested_via_cycle(self):
        self.write('hosts.yaml', 'hosts:\n  a:\n    connection: {hostname: a, via: {hostname: inline, via: {host: b}}}\n  b:\n    connection: {hostname: b, via: {host: a}}\n')
        with self.assertRaisesRegex(ops.ConfigError, 'a -> b -> a'):
            self.check()

    def test_unknown_reference(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a, via: {host: missing}}}}')
        with self.assertRaisesRegex(ops.ConfigError, 'unknown host reference'):
            self.check()

    def test_include_cycle(self):
        self.write('hosts.yaml', 'include: [nested.yaml]')
        self.write('nested.yaml', 'include: [hosts.yaml]')
        with self.assertRaisesRegex(ops.ConfigError, 'include cycle'):
            self.check()

    def test_repeated_include_once(self):
        self.write('hosts.yaml', 'include: [a.yaml, b.yaml]')
        self.write('a.yaml', 'include: [common.yaml]')
        self.write('b.yaml', 'include: [common.yaml]')
        self.write('common.yaml', 'hosts: {a: {connection: {hostname: a}}}')
        self.assertEqual(len(self.check().hosts), 1)

    def test_duplicate_host_sources(self):
        self.write('hosts.yaml', 'include: [a.yaml]\nhosts: {a: {connection: {hostname: a}}}')
        self.write('a.yaml', 'hosts: {a: {connection: {hostname: b}}}')
        with self.assertRaisesRegex(ops.ConfigError, 'duplicate host a:'):
            self.check()

    def test_duplicate_yaml_key(self):
        self.write('hosts.yaml', 'hosts: {}\nhosts: {}')
        with self.assertRaisesRegex(ops.ConfigError, 'duplicate YAML key'):
            self.check()

    def test_yaml_error_does_not_echo_value(self):
        self.write('hosts.yaml', 'hosts: [SECRET-VALUE')
        with self.assertRaises(ops.ConfigError) as raised:
            self.check()
        self.assertNotIn('SECRET-VALUE', str(raised.exception))

    def test_recursive_yaml_alias(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}, vars: &v {self: *v}}}')
        with self.assertRaises(ops.ConfigError):
            self.check()

    def test_invalid_port_and_alias_mix(self):
        for connection in ('{hostname: a, port: true}', '{hostname: a, ssh_config_alias: a}'):
            with self.subTest(connection=connection):
                self.write('hosts.yaml', 'hosts: {a: {connection: ' + connection + '}}')
                with self.assertRaises(ops.ConfigError):
                    self.check()

    def test_local_connection_and_proxy_command(self):
        self.write('hosts.yaml', '''hosts:
  localhost:
    connection: {local: true}
  remote:
    connection:
      hostname: target.example
      proxy_command: "ssh -W target.example:22 jump-user@jump.example"
''')
        result = self.check()
        self.assertEqual(result.edges, {'localhost': [], 'remote': []})

    def test_multiple_user_accounts_and_dump(self):
        self.write('hosts.yaml', 'include: [hosts/web.yaml]')
        self.write('hosts/web.yaml', '''hosts:
  host-01:
    connection: {hostname: host.example, user: operator}
    users:
      operator:
        password: "012345"
        vars: {workspace: /home/operator, enabled: true}
      appuser:
        password: example-su-password
        vars: {app_root: /srv/app, workers: 2}
      root: {}
    vars: {shared: host-value}
''')
        host = self.check().hosts['host-01']
        self.assertEqual(host['connection']['user'], 'operator')
        self.assertEqual(host['users']['operator']['password'], '012345')
        self.assertEqual(host['users']['appuser']['vars']['workers'], 2)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = ops.main(['dump', 'hosts.host-01.users.appuser', str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), host['users']['appuser'])

    def test_invalid_user_accounts(self):
        for users in (
            '[]', '{"": {}}', '{operator: null}', '{operator: {password: 123}}',
            '{operator: {password: null}}', '{operator: {vars: []}}',
            '{operator: {unsupported: true}}', '{operator: {vars: {date: 2026-10-10}}}',
            '{operator: {vars: &v {self: *v}}}', '{operator: {}, operator: {}}',
        ):
            with self.subTest(users=users):
                self.write('hosts.yaml', 'hosts:\n  a:\n    connection: {local: true}\n    users: ' + users)
                with self.assertRaises(ops.ConfigError):
                    self.check()

    def connection_cli(self, host, session_class, *flags):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(ops, 'load_session_class', return_value=session_class), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = ops.main(['test-connection', host, str(self.root), '--timeout', '5', *flags])
        return code, output.getvalue(), errors.getvalue()

    def session_double(self):
        local, remote = Mock(), Mock()
        local.connect.return_value = remote
        local.exec_command.side_effect = remote.exec_command.side_effect = [('test-host\n', '', 0), ('test-date\n', '', 0)]
        session_class = Mock(return_value=local)
        session_class.resolve_connection.side_effect = lambda host, username=None, port=None, ssh_config=None, **kw: dict(hostname=host, username=username, port=port or 22, **kw)
        return session_class, local, remote

    def test_connection_password_and_command_output(self):
        self.write('hosts.yaml', '''hosts:
  a:
    connection: {hostname: host.example, user: operator}
    users: {operator: {password: SYNTHETIC-SECRET}}
    recipes: [{recipe: ./recipes/not-installed}]
''')
        session_class, local, remote = self.session_double()
        code, output, errors = self.connection_cli('a', session_class)
        report = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(errors, '')
        self.assertTrue(report['success'])
        self.assertEqual([item['command'] for item in report['commands']], ['hostname', 'date'])
        self.assertEqual(report['commands'][0]['stdout'], 'test-host\n')
        self.assertEqual(local.connect.call_args.kwargs['password'], 'SYNTHETIC-SECRET')
        self.assertFalse(local.connect.call_args.kwargs['allow_agent'])
        self.assertEqual(remote.exec_command.call_args_list[0].args, (['hostname'],))
        self.assertEqual(remote.exec_command.call_args_list[0].kwargs['command_timeout'], 5)
        self.assertNotIn('SYNTHETIC-SECRET', output)
        local.close.assert_called_once_with(strict=True)

    def test_connection_local_and_unknown_host(self):
        self.write('hosts.yaml', 'hosts: {localhost: {connection: {local: true}}}')
        session_class, local, remote = self.session_double()
        code, output, errors = self.connection_cli('localhost', session_class)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)['connected'])
        local.connect.assert_not_called()
        remote.exec_command.assert_not_called()
        local.close.assert_called_once_with(strict=True)
        code, output, errors = self.connection_cli('missing', session_class)
        self.assertEqual(code, 1)
        self.assertEqual(output, '')
        self.assertIn('unknown host ID', errors)

    def test_connection_jump_credentials_and_relative_key(self):
        self.write('hosts.yaml', 'include: [hosts/nodes.yaml]')
        self.write('hosts/nodes.yaml', '''hosts:
  jump:
    connection: {hostname: jump.example, user: jumper, proxy_command: "nc jump.example 22"}
    users: {jumper: {password: jump-password}}
  target:
    connection: {hostname: target.example, user: operator, identity_file: keys/id_rsa, via: {host: jump}}
    users: {operator: {password: target-password}}
''')
        session_class, local, jump = self.session_double()
        target = Mock()
        target.exec_command.side_effect = [('test-host\n', '', 0), ('test-date\n', '', 0)]
        jump.connect.return_value = target
        code, output, errors = self.connection_cli('target', session_class)
        self.assertEqual(code, 0)
        self.assertEqual(local.connect.call_args.kwargs['password'], 'jump-password')
        self.assertEqual(local.connect.call_args.kwargs['proxyCommand'], 'nc jump.example 22')
        self.assertEqual(jump.connect.call_args.kwargs['password'], 'target-password')
        self.assertEqual(jump.connect.call_args.kwargs['pkey_path'], 'keys/id_rsa')
        self.assertNotIn('key_filename', jump.connect.call_args.kwargs)
        self.assertNotIn('look_for_keys', jump.connect.call_args.kwargs)
        jump.exec_command.assert_not_called()

    def test_identity_file_paths_are_passed_literally(self):
        for path in ('iap/.ssh/id_rsa', '~iap/.ssh/id_rsa', '/home/iap/.ssh/id_rsa'):
            with self.subTest(path=path):
                self.write('hosts.yaml', 'hosts:\n  target:\n    connection:\n      hostname: target.example\n      identity_file: ' + json.dumps(path))
                session_class, local, remote = self.session_double()
                code, output, errors = self.connection_cli('target', session_class)
                self.assertEqual(code, 0)
                self.assertEqual(local.connect.call_args.kwargs['pkey_path'], path)
                self.assertNotIn('key_filename', local.connect.call_args.kwargs)

    def test_connection_alias_proxy_conflict_before_connect(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {ssh_config_alias: alias, via: {hostname: jump}}}}')
        session_class, local, remote = self.session_double()
        session_class.resolve_connection.side_effect = [
            {'hostname': 'jump', 'username': 'jumper', 'port': 22},
            {'hostname': 'target', 'username': 'operator', 'port': 22, 'proxyCommand': 'proxy SECRET'},
        ]
        code, output, errors = self.connection_cli('a', session_class)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)['error']['stage'], 'connection settings')
        session_class.assert_not_called()
        self.assertNotIn('SECRET', output)

    def test_jump_failure_diagnostics_without_credentials(self):
        self.write('hosts.yaml', '''hosts:
  iapdev:
    connection: {hostname: jump.example, user: iap, proxy_command: "proxy TOKEN-SECRET"}
    users: {iap: {password: JUMP-SECRET}}
  rms4:
    connection: {hostname: target.example, user: operator, identity_file: /home/iap/.ssh/id_rsa, via: {host: iapdev}}
    users: {operator: {password: TARGET-SECRET}}
''')
        for flags in ((), ('--verbose',), ('--debug', '--traceback')):
            with self.subTest(flags=flags):
                session_class, local, jump = self.session_double()
                jump.connect.side_effect = FileNotFoundError('proxy TOKEN-SECRET JUMP-SECRET TARGET-SECRET')
                code, output, errors = self.connection_cli('rms4', session_class, *flags)
                report = json.loads(output)
                self.assertEqual(code, 1)
                self.assertEqual([hop['connected'] for hop in report['hops']], [True, False])
                self.assertEqual(report['error']['hop']['host'], 'rms4')
                self.assertEqual(report['error']['hop']['parent'], 'iapdev')
                self.assertEqual(report['error']['hop']['key_source'], 'iapdev')
                self.assertIn('readable', report['error']['hint'])
                for secret in ('TOKEN-SECRET', 'JUMP-SECRET', 'TARGET-SECRET'):
                    self.assertNotIn(secret, output + errors)
                jump.exec_command.assert_not_called()
                local.close.assert_called_once_with(strict=True)
                if '--debug' in flags:
                    self.assertIn('DEBUG ', errors)
                    self.assertIn('"password_supplied": true', errors)
                    self.assertIn('Traceback (frames only): FileNotFoundError', errors)
                    self.assertIn(' in test_connection', errors)
                elif flags:
                    self.assertIn('iapdev: connected', errors)
                    self.assertIn('iapdev -> rms4: connecting', errors)
                    self.assertNotIn('DEBUG ', errors)
                else:
                    self.assertEqual(errors, '')

    def test_first_hop_failure_identifies_jump(self):
        self.write('hosts.yaml', 'hosts: {jump: {connection: {hostname: jump}}, target: {connection: {hostname: target, via: {host: jump}}}}')
        session_class, local, remote = self.session_double()
        local.connect.side_effect = TimeoutError('secret')
        code, output, errors = self.connection_cli('target', session_class, '--debug')
        report = json.loads(output)
        self.assertEqual(code, 1)
        self.assertEqual(report['error']['reason'], 'timeout')
        self.assertEqual(report['error']['hop']['host'], 'jump')
        self.assertEqual(report['error']['hop']['parent'], 'localhost')
        self.assertEqual(len(report['hops']), 1)
        remote.connect.assert_not_called()

    def test_command_and_cleanup_tracebacks_preserve_json(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}}}')
        session_class, local, remote = self.session_double()
        remote.exec_command.side_effect = [TimeoutError('COMMAND-SECRET'), ('date\n', '', 0)]
        local.close.side_effect = RuntimeError('CLEANUP-SECRET')
        code, output, errors = self.connection_cli('a', session_class, '--traceback')
        report = json.loads(output)
        self.assertEqual(code, 1)
        self.assertTrue(report['connected'])
        self.assertEqual(report['commands'][1]['exitcode'], 0)
        self.assertEqual(report['cleanup_error'], 'RuntimeError')
        self.assertIn('Traceback (frames only): TimeoutError', errors)
        self.assertIn('Traceback (frames only): RuntimeError', errors)
        self.assertNotIn('COMMAND-SECRET', output + errors)
        self.assertNotIn('CLEANUP-SECRET', output + errors)

    def test_connection_failures_and_cleanup(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}}}')
        for failure in ('connect', 'command', 'exitcode', 'cleanup'):
            with self.subTest(failure=failure):
                session_class, local, remote = self.session_double()
                if failure == 'connect':
                    local.connect.side_effect = RuntimeError('SYNTHETIC-SECRET')
                elif failure == 'command':
                    remote.exec_command.side_effect = [TimeoutError('SYNTHETIC-SECRET'), ('test-date\n', '', 0)]
                elif failure == 'exitcode':
                    remote.exec_command.side_effect = [('', 'command failed\n', 1), ('test-date\n', '', 0)]
                else:
                    local.close.side_effect = RuntimeError('SYNTHETIC-SECRET')
                code, output, errors = self.connection_cli('a', session_class)
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(output)['success'])
                self.assertNotIn('SYNTHETIC-SECRET', output + errors)
                local.close.assert_called_once_with(strict=True)

    def test_connection_error_categories_do_not_echo_secrets(self):
        for name, message, reason in (
            ('BadHostKeyException', 'SYNTHETIC-SECRET', 'host_key_mismatch'),
            ('SSHException', 'Server iapdev not found in known_hosts: SYNTHETIC-SECRET', 'unknown_host_key'),
            ('SSHException', 'Error reading SSH protocol banner SYNTHETIC-SECRET', 'ssh_banner_unavailable'),
            ('AuthenticationException', 'SYNTHETIC-SECRET', 'authentication_failed'),
        ):
            with self.subTest(reason=reason):
                exc = type(name, (Exception,), {})(message)
                result = ops.connection_error(exc)
                self.assertEqual(result, {'type': name, 'reason': reason})
                self.assertNotIn('SYNTHETIC-SECRET', json.dumps(result))

    def test_invalid_local_and_proxy_connections(self):
        connections = (
            '{local: false}', '{local: "true"}', '{local: true, hostname: localhost}',
            '{hostname: a, via: {local: true}}',
            '{hostname: a, via: {host: localhost}}',
            '{hostname: a, proxy_command: ""}', '{hostname: a, proxy_command: 123}',
            '{hostname: a, proxy_command: nc, via: {hostname: jump}}',
            '{ssh_config_alias: a, proxy_command: nc}',
        )
        for connection in connections:
            with self.subTest(connection=connection):
                self.write('hosts.yaml', 'hosts:\n  localhost:\n    connection: {local: true}\n  a:\n    connection: ' + connection)
                with self.assertRaises(ops.ConfigError):
                    self.check()

    def test_outside_and_symlink_include(self):
        outside = Path(self.temp.name) / 'outside.yaml'
        outside.write_text('hosts: {}')
        for target in ('../outside.yaml', str(outside)):
            self.write('hosts.yaml', f'include: [{target}]')
            with self.assertRaisesRegex(ops.ConfigError, 'outside management root'):
                self.check()
        (self.root / 'link.yaml').symlink_to(outside)
        self.write('hosts.yaml', 'include: [link.yaml]')
        with self.assertRaisesRegex(ops.ConfigError, 'outside management root'):
            self.check()

    def test_absolute_internal_include(self):
        included = self.write('hosts/empty.yaml', 'hosts: {}')
        self.write('hosts.yaml', f'include: [{included}]')
        self.assertEqual(len(self.check().loaded), 2)

    def test_glob_order_and_dedup(self):
        for name in ('basic-b-storage', 'basic-a-storage', 'other'):
            self.write(f'recipes/{name}/recipe.yaml', f'id: {name}\n')
        self.write('hosts.yaml', 'hosts:\n  a:\n    connection: {hostname: a}\n    recipes:\n      - glob: ./recipes/basic-*-storage\n      - directory: ./recipes\n')
        self.assertEqual([p.name for p in self.check().selected['a']], ['basic-a-storage', 'basic-b-storage', 'other'])

    def test_recursive_directory_and_double_star(self):
        self.write('recipes/category/basic/recipe.yaml', 'id: basic')
        for selector in ('{directory: ./recipes, recursive: true}', '{glob: "./recipes/**/basic"}'):
            self.write('hosts.yaml', f'hosts: {{a: {{connection: {{hostname: a}}, recipes: [{selector}]}}}}')
            self.assertEqual(len(self.check().selected['a']), 1)

    def test_empty_match_and_duplicate_recipe_id(self):
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}, recipes: [{glob: ./recipes/no-*}]}}')
        (self.root / 'recipes').mkdir()
        with self.assertRaisesRegex(ops.ConfigError, 'matched no recipes'):
            self.check()
        for name in ('a', 'b'):
            self.write(f'recipes/{name}/recipe.yaml', 'id: same')
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}, recipes: [{directory: ./recipes}]}}')
        with self.assertRaisesRegex(ops.ConfigError, 'duplicate recipe ID'):
            self.check()

    def test_recipe_symlink_escape_and_glob_escape(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'recipes').mkdir()
        (self.root / 'recipes/link').symlink_to(outside)
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}, recipes: [{glob: "./recipes/**"}]}}')
        with self.assertRaisesRegex(ops.ConfigError, 'outside management root'):
            self.check()
        self.write('hosts.yaml', 'hosts: {a: {connection: {hostname: a}, recipes: [{glob: "../outside/*"}]}}')
        with self.assertRaisesRegex(ops.ConfigError, 'outside management root'):
            self.check()

    def test_init_symlink_preflight(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'records').symlink_to(outside)
        with self.assertRaisesRegex(ops.ConfigError, 'scaffold symlink'):
            ops.initialize(self.root)
        self.assertFalse((self.root / 'hosts.yaml').exists())


if __name__ == '__main__':
    unittest.main()
