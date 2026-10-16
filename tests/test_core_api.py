"""Core 0.1.0 contracts: temporary installations and synthetic transports only."""
from contextlib import contextmanager, redirect_stdout
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opsfeast import Instance, Recipe, CoreError, ConfigError
from opsfeast.identity import initialize_identity, read_identity, NIL_UUID, DEVELOPMENT_UUID, FILENAME


class Actor:
    def __init__(self, name='operator', uid=1000, owner=None):
        self.name, self.uid = name, uid
        self.owner = owner or self
        if owner is None:
            self.closed = 0
            self.close_failure = False
            self.restore_failure = False
            self.entry_failure = False
            self.wrong_identity = False
            self.transitions = []

    def exec_command(self, argv, **kwargs):
        if argv[:2] == ['id', '-un']:
            output = self.name
        elif argv[:2] == ['id', '-u']:
            output = str({'root': 0, 'operator': 1000, 'app': 1001}.get(argv[2], 2000)) if len(argv) > 2 else str(self.uid)
        else:
            output = self.name
        return SimpleNamespace(stdout=output + '\n', stderr='', exitcode=0)

    def __call__(self, command, **kwargs):
        import shlex
        return self.exec_command(shlex.split(command), **kwargs)

    @contextmanager
    def sudo(self, *, username, password, enter_timeout):
        self.owner.transitions.append(('sudo', username, password))
        if self.owner.entry_failure:
            raise PermissionError('synthetic-private-password')
        child = Actor(username, 2000 if self.owner.wrong_identity else {'root': 0, 'app': 1001}[username], self.owner)
        try:
            yield child
        finally:
            if self.owner.restore_failure:
                self.uid = 5555

    @contextmanager
    def su(self, user, *, password, enter_timeout):
        self.owner.transitions.append(('su', user, password))
        child = Actor(user, {'root': 0, 'app': 1001}[user], self.owner)
        yield child

    def close(self, strict=False):
        self.closed += 1
        if self.close_failure:
            raise RuntimeError('synthetic-private-password')


class CoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.installation = self.root / 'installation'
        self.installation.mkdir()
        self.instance = Instance.open(self.installation)
        self.management = self.installation / 'feasts/main'
        self.management.mkdir(parents=True)
        self.settings = {'hosts': {'h': {'connection': {'local': True},
                                      'users': {'operator': {'password': 'private-login'},
                                                'app': {'password': 'private-app'}},
                                      'vars': {'token': 'private-token'}}}}
        self.write()
        with redirect_stdout(io.StringIO()):
            self.instance.profiles.attach(self.management, name='main')
        self.profile = self.instance.profile()

    def write(self):
        (self.management / 'hosts.yaml').write_text(json.dumps(self.settings))

    def connection(self, actor=None):
        actor = actor or Actor()
        return self.profile.sessions._connect('h', session_class=lambda: actor), actor

    def test_missing_identity_inspection_has_no_writes(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.instance.inspect()
        self.assertEqual(result['identity']['id'], NIL_UUID)
        self.profile.inspect()
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertFalse((self.installation / FILENAME).exists())

    def test_identity_init_update_repeat_and_required_name(self):
        first = self.instance.initialize()
        self.assertEqual(first['name'], first['id'])
        self.assertEqual(self.instance.initialize()['id'], first['id'])
        changed = self.instance.update_metadata(name='Development', description='A test instance')
        self.assertEqual(changed['id'], first['id'])
        self.assertEqual(changed['name'], 'Development')
        with self.assertRaises(ConfigError):
            self.instance.update_metadata(name=' ')
        self.assertEqual(self.instance.identity['name'], 'Development')

    def test_reserved_development_id_and_clone_copy_renewal(self):
        initialize_identity(self.installation, identifier=DEVELOPMENT_UUID)
        copied = self.root / 'copy'
        shutil.copytree(self.installation, copied)
        other = Instance.open(copied)
        self.assertEqual(other.identity['id'], NIL_UUID)
        fresh = other.initialize()
        self.assertNotEqual(fresh['id'], DEVELOPMENT_UUID)
        self.assertEqual(fresh['name'], fresh['id'])
        self.assertEqual(self.instance.identity['id'], DEVELOPMENT_UUID)

    def test_custom_name_preserved_on_copy_and_move_preserves_id(self):
        old = self.instance.initialize(name='Custom', description='Keep this')
        copied = self.root / 'copy'
        shutil.copytree(self.installation, copied)
        fresh = Instance.open(copied).initialize()
        self.assertEqual((fresh['name'], fresh['description']), ('Custom', 'Keep this'))
        moved = self.root / 'moved'
        self.installation.rename(moved)
        relocated = Instance.open(moved).relocate_identity()
        self.assertEqual(relocated['id'], old['id'])

    def test_invalid_id_symlink_and_explicit_nil(self):
        self.instance.initialize()
        path = self.installation / FILENAME
        data = json.loads(path.read_text())
        data['id'] = 'invalid'
        path.write_text(json.dumps(data))
        with self.assertRaises(ConfigError):
            self.instance.identity
        self.assertEqual(self.instance.inspect()['status'], 'partial')
        data['id'] = NIL_UUID
        path.write_text(json.dumps(data))
        self.assertEqual(self.instance.identity['identity_status'], 'placeholder')
        path.unlink()
        path.symlink_to(self.management / 'hosts.yaml')
        with self.assertRaises(ConfigError):
            self.instance.initialize()

    def test_missing_id_field_uses_placeholder(self):
        self.instance.initialize()
        path = self.installation / FILENAME
        data = json.loads(path.read_text())
        del data['id']
        path.write_text(json.dumps(data))
        self.assertEqual(self.instance.identity['id'], NIL_UUID)

    def test_hosts_snapshot_reload_and_secret_selection(self):
        self.assertNotIn('private-login', json.dumps(self.profile.hosts.list()))
        self.assertEqual(self.profile.hosts.get('h', reveal_secrets=True)['users']['app']['password'], 'private-app')
        self.settings['hosts']['new'] = {'connection': {'local': True}}
        self.write()
        self.assertNotIn('new', self.profile.hosts.list())
        self.profile.reload()
        self.assertIn('new', self.profile.hosts.list())
        returned = self.profile.hosts.get('h', reveal_secrets=True)
        returned['users'].clear()
        self.assertTrue(self.profile.hosts.get('h')['users'])

    def test_include_and_rejected_duplicate_and_escape(self):
        (self.management / 'hosts.yaml').write_text('include: [extra.yaml]\nhosts: {}\n')
        (self.management / 'extra.yaml').write_text(json.dumps(self.settings))
        self.profile.reload()
        self.assertIn('h', self.profile.hosts.list())
        (self.management / 'hosts.yaml').write_text('hosts: {}\nhosts: {}\n')
        with self.assertRaises(ConfigError):
            self.profile.reload()
        self.assertIn('h', self.profile.hosts.list())
        (self.management / 'hosts.yaml').write_text('include: [../outside.yaml]\n')
        with self.assertRaises(ConfigError):
            self.profile.reload()

    def test_profiles_multi_instance_and_active_snapshot(self):
        external = self.root / 'external'
        external.mkdir()
        (external / 'hosts.yaml').write_text('{hosts: {}}')
        self.instance.profiles.attach(external, name='other')
        self.instance.profiles.use('other')
        self.assertEqual(self.instance.profile().name, 'other')
        self.assertEqual(self.profile.name, 'main')
        self.assertEqual(self.instance.profile('main').name, 'main')
        self.assertEqual(self.instance.profile().name, 'other')
        self.instance.profiles.detach('other')
        self.assertTrue(external.exists())
        self.assertEqual(self.instance.profile().name, 'main')
        second = self.root / 'second'
        second.mkdir()
        self.assertEqual(Instance.open(second).profiles.list(), {})
        with self.assertRaises(ConfigError):
            self.instance.profiles.detach('main')

    def test_scope_owned_cleanup_borrowed_close_and_lifetime(self):
        scope, actor = self.connection()
        with scope as recipe:
            self.assertEqual(recipe.session.exec_command(['whoami']).stdout.strip(), 'operator')
            with self.assertRaises(CoreError):
                recipe.session.close()
        self.assertEqual(actor.closed, 1)
        with self.assertRaises(CoreError):
            recipe.session.exec_command(['whoami'])

    def test_cleanup_failure_and_original_exception_preserved(self):
        actor = Actor()
        actor.close_failure = True
        scope, _ = self.connection(actor)
        with self.assertRaisesRegex(CoreError, 'session_cleanup_failed'):
            with scope:
                pass
        scope, _ = self.connection(actor)
        with self.assertRaisesRegex(ValueError, 'original') as error:
            with scope:
                raise ValueError('original')
        self.assertTrue(error.exception.__notes__)

    def test_disabled_host_and_timeout_before_connection(self):
        self.settings['hosts']['h']['enabled'] = False
        self.write()
        self.profile.reload()
        scope, actor = self.connection()
        with self.assertRaisesRegex(CoreError, 'host_disabled'):
            with scope:
                pass
        self.assertEqual(actor.closed, 0)
        for value in (0, -1, True, float('nan'), float('inf')):
            with self.assertRaises(ConfigError):
                with self.profile.sessions._connect('h', timeout=value, session_class=Actor):
                    pass

    def test_thread_ownership(self):
        scope, _ = self.connection()
        failures = []
        with scope as recipe:
            def use():
                try:
                    recipe.session.exec_command(['whoami'])
                except CoreError as exc:
                    failures.append(exc.code)
            thread = threading.Thread(target=use)
            thread.start()
            thread.join()
        self.assertEqual(failures, ['session_scope_unavailable'])

    def test_sudo_su_nested_identity_and_parent_guard(self):
        scope, actor = self.connection()
        with scope as recipe:
            with recipe.su('app') as app:
                self.assertEqual(app.session.exec_command(['whoami']).stdout.strip(), 'app')
                with self.assertRaises(CoreError):
                    recipe.session.exec_command(['whoami'])
                with app.sudo() as root:
                    self.assertEqual(root.session.exec_command(['whoami']).stdout.strip(), 'root')
            self.assertEqual(recipe.session.exec_command(['whoami']).stdout.strip(), 'operator')
            self.assertTrue(all(p['restoration_verified'] for p in recipe.report['privileges']))
        self.assertEqual(actor.transitions, [('su', 'app', 'private-app'), ('sudo', 'root', 'private-app')])
        with self.assertRaises(CoreError):
            root.session.exec_command(['whoami'])

    def test_sudo_disabled_and_empty_credential_precedence(self):
        account = self.settings['hosts']['h']['users']['operator']
        account['sudo'] = False
        self.write()
        self.profile.reload()
        scope, actor = self.connection()
        with scope as recipe:
            with self.assertRaisesRegex(CoreError, 'sudo_disabled'):
                with recipe.sudo():
                    pass
        self.assertEqual(actor.transitions, [])
        del account['sudo']
        account['sudo-password'] = None
        self.write()
        self.profile.reload()
        scope, actor = self.connection()
        with scope as recipe:
            with recipe.sudo():
                pass
        self.assertEqual(actor.transitions, [('sudo', 'root', '')])

    def test_unknown_su_and_missing_credential(self):
        scope, actor = self.connection()
        with scope as recipe:
            with self.assertRaises(ConfigError):
                with recipe.su('undeclared'):
                    pass
        del self.settings['hosts']['h']['users']['app']['password']
        self.write()
        self.profile.reload()
        scope, actor = self.connection()
        with scope as recipe:
            with self.assertRaisesRegex(CoreError, 'missing_su_password'):
                with recipe.su('app'):
                    pass
        self.assertEqual(actor.transitions, [])

    def test_entry_rejection_no_retry_and_identity_mismatch(self):
        actor = Actor()
        actor.entry_failure = True
        scope, _ = self.connection(actor)
        with scope as recipe:
            with self.assertRaises(PermissionError):
                with recipe.sudo():
                    self.fail('must not run')
            self.assertTrue(recipe.report['privileges'][0]['restoration_verified'])
        self.assertEqual(len(actor.transitions), 1)
        actor = Actor()
        actor.wrong_identity = True
        scope, _ = self.connection(actor)
        with scope as recipe:
            with self.assertRaises(RuntimeError):
                with recipe.sudo():
                    self.fail('identity must be verified')

    def test_failed_restoration_disables_session_even_when_caught(self):
        actor = Actor()
        actor.restore_failure = True
        scope, _ = self.connection(actor)
        with self.assertRaises(CoreError):
            with scope as recipe:
                with self.assertRaisesRegex(CoreError, 'identity_restoration_failed'):
                    with recipe.sudo():
                        pass
                with self.assertRaisesRegex(CoreError, 'session_scope_unavailable'):
                    recipe.session.exec_command(['whoami'])

    def test_privilege_body_exception_kept_on_restoration_failure(self):
        actor = Actor()
        actor.restore_failure = True
        scope, _ = self.connection(actor)
        with self.assertRaisesRegex(ValueError, 'body') as error:
            with scope as recipe:
                with recipe.sudo():
                    raise ValueError('body')
        self.assertTrue(error.exception.__notes__)

    def test_jump_chain_and_disabled_jump_before_session_creation(self):
        class Transport(Actor):
            calls = []
            @staticmethod
            def resolve_connection(hostname, **settings):
                settings.pop('ssh_config', None)
                return dict(settings, hostname=hostname)
            def connect(self, hostname, **settings):
                self.calls.append((hostname, settings))
                return Transport(owner=self.owner)
        self.settings['hosts'] = {
            'jump': {'connection': {'hostname': 'jump.example.invalid', 'user': 'operator', 'allow_agent': True}},
            'h': {'connection': {'hostname': 'target.example.invalid', 'allow_agent': True, 'via': {'host': 'jump'}, 'user': 'operator'}}}
        self.write()
        self.profile.reload()
        actor = Transport()
        class Factory:
            resolve_connection = staticmethod(Transport.resolve_connection)
            def __call__(self):
                return actor
        with self.profile.sessions._connect('h', session_class=Factory()) as recipe:
            self.assertEqual(len(recipe.report['hops']), 2)
        self.assertEqual([host for host, _ in Transport.calls], ['jump.example.invalid', 'target.example.invalid'])
        for _, settings in Transport.calls:
            self.assertIs(settings['allow_agent'], True)
            self.assertIs(settings['look_for_keys'], False)
        self.assertEqual(actor.closed, 1)
        self.settings['hosts']['jump']['enabled'] = False
        self.write()
        self.profile.reload()
        actor.closed = 0
        Transport.calls.clear()
        with self.assertRaises(ConfigError):
            with self.profile.sessions._connect('h', session_class=Factory()):
                self.fail('must reject disabled jump')
        self.assertEqual(Transport.calls, [])
        self.assertEqual(actor.closed, 0)

    def test_run_identity_snapshot_survives_metadata_renewal(self):
        old = self.instance.initialize()['id']
        scope, _ = self.connection()
        with scope as recipe:
            self.instance.renew_identity()
            self.assertEqual(recipe.instance_id, old)
            with recipe.sudo() as root:
                self.assertEqual(root.instance_id, old)

    def test_invalid_initial_identity_poisoned_if_caught(self):
        class BadIdentity(Actor):
            def exec_command(self, argv, **kwargs):
                result = super().exec_command(argv, **kwargs)
                if argv == ['id', '-u']:
                    result.stdout = 'invalid'
                return result
        scope, _ = self.connection(BadIdentity())
        with self.assertRaisesRegex(CoreError, 'identity_verification_failed'):
            with scope as recipe:
                with self.assertRaises(CoreError):
                    with recipe.sudo():
                        self.fail('unverified identity')
                with self.assertRaises(CoreError):
                    recipe.session.exec_command(['whoami'])

    def test_inspection_detects_current_invalid_config_without_replacing_snapshot(self):
        (self.management / 'hosts.yaml').write_text('hosts: [invalid]')
        snapshot = self.instance.inspect()
        self.assertEqual(snapshot['status'], 'partial')
        self.assertEqual(snapshot['profiles']['main']['configuration_status'], 'invalid')
        self.assertIn('h', self.profile.hosts.list())

    def test_instance_cli_read_and_metadata(self):
        script = Path(__file__).resolve().parents[1] / 'tools/opsfeast.py'
        for action, options in [('inspect', []), ('init', ['--name', 'CLI']), ('set', ['--description', 'Description'])]:
            result = subprocess.run([sys.executable, '-B', str(script), 'instance', action,
                                     '--installation', str(self.installation), *options],
                                    capture_output=True, text=True, timeout=20, cwd='/')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)
        self.assertEqual(self.instance.identity['name'], 'CLI')


if __name__ == '__main__':
    unittest.main()
