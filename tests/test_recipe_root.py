"""Recipe.root console, typed failures, scope ownership and shared policy; synthetic only."""
from contextlib import contextmanager
import json
import threading
from types import SimpleNamespace
import unittest

from opsfeast import CoreError, Recipe, RootUnavailableError
import test_core_api as fixture
import test_core_delivery as delivery
import host_runtime as hr
import inventory_actor
import root_access


class RootActor(fixture.Actor):
    def __init__(self, name='operator', uid=1000, owner=None):
        super().__init__(name, uid, owner)
        self.latest = None
        if owner is None:
            self.failures = set()
            self.exit_failures = set()
            self.restore_failures = set()
            self.calls = []
            self.shell_failure = False
            self.shell_wrong_identity = False

    def __call__(self, command, **kwargs):
        self.owner.calls.append(('command', self.name, command, kwargs))
        self.latest = super().__call__(command, **kwargs)
        return self.latest

    @property
    def stdout(self):
        return self.latest.stdout

    @property
    def stderr(self):
        return self.latest.stderr

    @property
    def exitcode(self):
        return self.latest.exitcode

    def start(self, command, **kwargs):
        self.owner.calls.append(('start', self.name, command, kwargs))
        return SimpleNamespace(command=command, actor=self.name)

    @contextmanager
    def enter(self, command, **kwargs):
        self.owner.calls.append(('enter', self.name, command, kwargs))
        yield self

    def expect(self, value, **kwargs):
        self.owner.calls.append(('expect', self.name, value, kwargs))
        return 'prompt'

    def input(self, value, **kwargs):
        self.owner.calls.append(('input', self.name, value, kwargs))
        return 'prompt'

    def send(self, value):
        self.owner.calls.append(('send', self.name, value, {}))

    @contextmanager
    def switch(self, mode, target, password):
        self.owner.transitions.append((mode, target, password))
        if (self.name, mode, target) in self.owner.failures:
            raise PermissionError('synthetic-private-rejection')
        uid = {'operator': 1000, 'app': 1001, 'root': 0}[target]
        child = RootActor(target, 2000 if self.owner.wrong_identity else uid, self.owner)
        try:
            yield child
        finally:
            if (self.name, mode, target) in self.owner.exit_failures:
                raise RuntimeError('synthetic-private-cleanup')
            if (self.name, mode, target) in self.owner.restore_failures:
                self.uid = 5555

    def sudo(self, *, username, password, enter_timeout):
        return self.switch('sudo', username, password)

    def su(self, user, *, password, enter_timeout):
        return self.switch('su', user, password)

    @contextmanager
    def shell(self, shell):
        self.owner.transitions.append(('shell', shell, None))
        if self.owner.shell_failure:
            raise RuntimeError('synthetic shell unavailable')
        child = RootActor(self.name, 500 if self.owner.shell_wrong_identity else self.uid, self.owner)
        try:
            yield child
        finally:
            if ('shell', shell) in self.owner.exit_failures:
                raise RuntimeError('synthetic shell cleanup failed')


class RecipeRootTests(unittest.TestCase):
    setUp = fixture.CoreTests.setUp
    write = fixture.CoreTests.write
    connection = fixture.CoreTests.connection

    def reload(self, users):
        self.settings['hosts']['h']['users'] = users
        self.write()
        self.profile.reload()

    def test_returns_callable_console_and_original_command_result(self):
        scope, actor = self.connection(RootActor())
        with scope as recipe:
            with recipe.root() as root:
                self.assertTrue(callable(root))
                self.assertNotIsInstance(root, Recipe)
                self.assertFalse(hasattr(root, 'session'))
                result = root('id -u', check=True)
                self.assertEqual(result.stdout.strip(), '0')
                self.assertEqual(root.stdout, result.stdout)
                self.assertEqual(root.stderr, '')
                self.assertEqual(root.exitcode, 0)
                self.assertEqual(root.exec_command('whoami').stdout.strip(), 'root')
                self.assertEqual(actor.calls[-1][-1]['command_timeout'], recipe.timeout)
                with self.assertRaises(CoreError):
                    recipe.session.exec_command(['whoami'])
            self.assertEqual(recipe.session.exec_command(['whoami']).stdout.strip(), 'operator')
            evidence = recipe.report['privileges'][0]
            self.assertEqual(evidence['operation'], 'root')
            self.assertTrue(evidence['restoration_verified'])
        self.assertEqual(result.stdout.strip(), '0')
        with self.assertRaises(CoreError):
            root('whoami')
        self.assertEqual(actor.closed, 1)

    def test_root_second_su_precedes_login_sudo(self):
        self.reload({'operator': {}, 'root': {'password': 'private-root'}})
        scope, actor = self.connection(RootActor())
        with scope as recipe:
            with recipe.root() as root:
                self.assertEqual(root('id -u').stdout.strip(), '0')
            self.assertEqual(recipe.report['privileges'][0]['candidate_users'], ['root', 'operator'])
        self.assertEqual(actor.transitions, [('su', 'root', 'private-root')])

    def test_first_eligible_other_user_uses_su_then_sudo(self):
        self.reload({'operator': {'sudo': False}, 'app': {'password': 'private-app'},
                     'root': {'password': 'private-unused'}})
        scope, actor = self.connection(RootActor())
        with scope as recipe:
            with recipe.root() as root:
                self.assertEqual(root('id -u').stdout.strip(), '0')
        self.assertEqual(actor.transitions, [('su', 'app', 'private-app'), ('sudo', 'root', 'private-app')])

    def test_typed_failure_never_runs_body_and_keeps_login_usable(self):
        self.reload({'operator': {}, 'app': {'password': 'private-app'}, 'root': {'password': 'private-unused'}})
        actor = RootActor()
        actor.failures = {('operator', 'sudo', 'root'), ('app', 'sudo', 'root')}
        scope, _ = self.connection(actor)
        with scope as recipe:
            with self.assertRaises(RootUnavailableError) as caught:
                with recipe.root():
                    self.fail('root body must not execute')
            self.assertIsInstance(caught.exception, CoreError)
            self.assertEqual(caught.exception.code, 'root_unavailable')
            evidence = caught.exception.report
            self.assertTrue(evidence['restoration_verified'])
            self.assertEqual(len(evidence['attempts']), 2)
            self.assertNotIn('private-', json.dumps(evidence))
            evidence['attempts'].clear()
            self.assertEqual(len(caught.exception.report['attempts']), 2)
            self.assertEqual(recipe.session.exec_command(['whoami']).stdout.strip(), 'operator')
        self.assertEqual(len(actor.transitions), 3)

    def test_disabled_login_without_candidate_raises_and_no_required_option(self):
        self.reload({'operator': {'sudo': False}})
        scope, actor = self.connection(RootActor())
        with scope as recipe:
            with self.assertRaises(TypeError):
                recipe.root(required=False)
            with self.assertRaises(RootUnavailableError):
                with recipe.root():
                    self.fail('must raise')
        self.assertEqual(actor.transitions, [])

    def test_already_root_uses_console_without_sudo_even_when_disabled(self):
        self.reload({'root': {'sudo': False}})
        scope, actor = self.connection(RootActor('root', 0))
        with scope as recipe:
            with recipe.root() as root:
                self.assertEqual(root('id -u').stdout.strip(), '0')
            self.assertTrue(recipe.report['privileges'][0]['console_cleanup_verified'])
        self.assertEqual(actor.transitions, [('shell', 'bash', None)])

    def test_console_start_and_interactive_calls_keep_native_conventions(self):
        scope, actor = self.connection(RootActor())
        with scope as recipe:
            with recipe.root() as root:
                job = root.start('printf ready', timeout=7)
                self.assertEqual(job.actor, 'root')
                root.start('printf default')
                self.assertEqual(actor.calls[-1][-1]['timeout'], recipe.timeout)
                with root.enter('synthetic-program', prompt='ready') as program:
                    self.assertEqual(program.name, 'root')
                self.assertEqual(root.expect('ready'), 'prompt')
                self.assertEqual(root.input('answer'), 'prompt')
                root.send('exact\n')
                self.assertEqual(actor.calls[-1][2], 'exact\n')

    def test_wrong_identity_stops_and_disables_scope(self):
        actor = RootActor()
        actor.wrong_identity = True
        scope, _ = self.connection(actor)
        with self.assertRaisesRegex(CoreError, 'root_scope_failed'):
            with scope as recipe:
                with self.assertRaises(hr.IdentityProbeError):
                    with recipe.root():
                        self.fail('identity unverified')
                with self.assertRaises(CoreError):
                    recipe.session.exec_command(['whoami'])

    def test_nested_restoration_or_exit_failure_cannot_be_safe_unavailable(self):
        for kind in ('restore_failures', 'exit_failures'):
            self.reload({'operator': {'sudo': False}, 'app': {'password': 'private-app'}})
            actor = RootActor()
            getattr(actor, kind).add(('app', 'sudo', 'root'))
            scope, _ = self.connection(actor)
            with self.subTest(kind=kind), self.assertRaisesRegex(CoreError, 'root_scope_failed'):
                with scope as recipe:
                    with self.assertRaises(RuntimeError) as caught:
                        with recipe.root() as root:
                            root('whoami')
                    self.assertNotIsInstance(caught.exception, RootUnavailableError)
                    with self.assertRaises(CoreError):
                        recipe.session.exec_command(['whoami'])

    def test_already_root_console_entry_identity_and_exit_failures_disable_scope(self):
        for kind in ('shell_failure', 'shell_wrong_identity', 'exit'):
            actor = RootActor('root', 0)
            if kind == 'exit':
                actor.exit_failures.add(('shell', 'bash'))
            else:
                setattr(actor, kind, True)
            scope, _ = self.connection(actor)
            with self.subTest(kind=kind), self.assertRaises(CoreError):
                with scope as recipe:
                    with self.assertRaises(RuntimeError) as caught:
                        with recipe.root():
                            pass
                    self.assertNotIsInstance(caught.exception, RootUnavailableError)
                    with self.assertRaises(CoreError):
                        recipe.session.exec_command(['whoami'])

    def test_body_error_preserved_and_healthy_scope_can_continue(self):
        scope, _ = self.connection(RootActor())
        with scope as recipe:
            with self.assertRaisesRegex(ValueError, 'original body failure'):
                with recipe.root():
                    raise ValueError('original body failure')
            self.assertEqual(recipe.session.exec_command(['whoami']).stdout.strip(), 'operator')

    def test_body_error_preserved_with_cleanup_note_and_disabled_scope(self):
        actor = RootActor()
        actor.exit_failures.add(('operator', 'sudo', 'root'))
        scope, _ = self.connection(actor)
        with self.assertRaisesRegex(ValueError, 'original body failure') as caught:
            with scope as recipe:
                with recipe.root():
                    raise ValueError('original body failure')
        self.assertIn('session disabled', caught.exception.__notes__[0])
        self.assertEqual(recipe.report['privileges'][0]['cleanup_error'], 'RuntimeError')
        self.assertEqual(recipe.report['privileges'][0]['error_type'], 'ValueError')

    def test_cross_thread_cached_method_and_explicit_privilege_scope_guards(self):
        scope, _ = self.connection(RootActor())
        with scope as recipe:
            with recipe.su('app') as app:
                with self.assertRaisesRegex(CoreError, 'root_requires_login_scope'):
                    with app.root():
                        pass
            errors = []
            with recipe.root() as root:
                call = root.exec_command
                def use():
                    try:
                        root('whoami')
                    except CoreError as exc:
                        errors.append(exc.code)
                thread = threading.Thread(target=use)
                thread.start()
                thread.join()
            self.assertEqual(errors, ['session_scope_unavailable'])
            with self.assertRaises(CoreError):
                call('whoami')

    def test_shared_root_unavailable_report_is_safe_and_inventory_catches_only_entry(self):
        config = self.profile.hosts._config
        actor = RootActor()
        actor.failures = {('operator', 'sudo', 'root'), ('operator', 'su', 'app')}
        evidence = {}
        with self.assertRaises(RootUnavailableError) as caught:
            with root_access.root_actor(actor, config, 'h', 5, evidence):
                self.fail('strict helper must not fall back')
        self.assertTrue(caught.exception.report['restoration_verified'])
        with self.assertRaises(RootUnavailableError):
            with inventory_actor.collection_actor(RootActor(), config, 'h', 5, {}) as selected:
                raise RootUnavailableError({'restoration_verified': True})


class RecipeRootRunnerTests(unittest.TestCase):
    setUp = delivery.CoreDeliveryTests.setUp
    write = delivery.CoreDeliveryTests.write
    run_recipe = delivery.CoreDeliveryTests.run_recipe

    def test_runner_supplied_recipe_uses_callable_root_and_saves_evidence(self):
        self.write('''VERSION = '0.1.0'
def execute(recipe):
    with recipe.root() as root:
        value = root('id -u', check=True).stdout.strip()
    return {'status': 'success', 'reason_code': 'observed', 'message': 'Synthetic root.',
            'data': {'uid': value}}
''')
        report, path = self.run_recipe(RootActor())
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['data']['uid'], '0')
        self.assertTrue(report['privileges'][0]['restoration_verified'])
        self.assertEqual(json.loads(path.read_text())['privileges'][0]['operation'], 'root')

    def test_runner_never_marks_suppressed_unsafe_root_as_success(self):
        self.write('''VERSION = '0.1.0'
def execute(recipe):
    try:
        with recipe.root():
            pass
    except Exception:
        pass
    return {'status': 'success', 'reason_code': 'observed', 'message': 'Suppressed failure.', 'data': {}}
''')
        actor = RootActor()
        actor.wrong_identity = True
        report, _ = self.run_recipe(actor)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['reason_code'], 'root_scope_failed')
        self.assertEqual(report['privileges'][0]['error_type'], 'IdentityProbeError')
