"""Two-candidate inventory policy, nested cleanup and runner regressions; synthetic only."""
import contextlib
import io
import json
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import host_runtime as hr
import inventory_actor as policy
import access_check as access
import opsfeast as ops
import recipe_runner as runner
from test_inventory_access import SyntheticSession
from test_esxi_identity import EsxiSession, result


class Actor:
    uids = {'operator': 1001, 'maintainer': 1002, 'third': 1003, 'root': 0}

    def __init__(self, name='operator', events=None, failures=None, broken=None):
        self.name = name
        self.events = [] if events is None else events
        self.failures = {} if failures is None else failures
        self.broken = set() if broken is None else broken
        self.poisoned = False

    def exec_command(self, argv, **kwargs):
        if self.poisoned:
            raise RuntimeError('unverified parent recovery')
        if argv == ['id', '-un']:
            return result(self.name + '\n')
        if argv[:2] == ['id', '-u']:
            return result(str(self.uids[argv[2] if len(argv) == 3 else self.name]) + '\n')
        return result(self.name)

    def __call__(self, command, **kwargs):
        return self.exec_command(shlex.split(command), **kwargs)

    @contextlib.contextmanager
    def switch(self, mode, target, password):
        key = (self.name, mode, target)
        self.events.append(key)
        if key in self.failures:
            if key in self.broken:
                self.poisoned = True
            raise self.failures[key]('synthetic private rejection')
        actor = Actor(target, self.events, self.failures, self.broken)
        if ('identity', target) in self.broken:
            actor.name = 'third'
        try:
            yield actor
        finally:
            self.events.append(('exit', mode, target))
            if ('exit', target) in self.broken:
                raise RuntimeError('synthetic exit failure')
            if ('restore', target) in self.broken:
                self.poisoned = True

    def su(self, user, password, **kwargs):
        return self.switch('su', user, password)

    def sudo(self, username, password, **kwargs):
        return self.switch('sudo', username, password)


class InventoryActorTests(unittest.TestCase):
    def config(self, users):
        return SimpleNamespace(hosts={'h': {'connection': {'local': True}, 'users': users,
                                          'vars': {'sudo': {'password': 'private-host'}}}})

    def collect(self, users, actor=None, preflight=None):
        actor = actor or Actor()
        report = {}
        with policy.collection_actor(actor, self.config(users), 'h', 5, report,
                                     preflight=preflight) as selected:
            self.assertEqual(selected.exec_command(['id', '-u']).stdout.strip(),
                             str(report['actual_identity']['effective_uid']))
        self.assertTrue(report['restoration_verified'])
        self.assertNotIn('private-', json.dumps(report))
        return report, actor.events

    def test_login_sudo_success_never_contacts_second(self):
        report, events = self.collect({'operator': {}, 'maintainer': {'password': 'private-su'}})
        self.assertEqual(events, [('operator', 'sudo', 'root'), ('exit', 'sudo', 'root')])
        self.assertEqual(report['selected_user'], 'operator')

    def test_disabled_login_uses_only_first_eligible_yaml_user(self):
        users = {'operator': {'sudo': False}, 'third': {'sudo': False},
                 'maintainer': {'password': 'private-su'}, 'root': {'password': 'private-root'}}
        report, events = self.collect(users)
        self.assertEqual(report['candidate_users'], ['operator', 'maintainer'])
        self.assertEqual(report['selected_user'], 'maintainer')
        self.assertEqual(report['mode'], 'root')
        self.assertEqual(events[:2], [('operator', 'su', 'maintainer'), ('maintainer', 'sudo', 'root')])
        self.assertEqual(report['attempts'][1]['steps'][1]['password_source'], 'users.<account>.password')

    def test_root_second_is_tried_before_login_sudo(self):
        users = {'operator': {}, 'root': {'sudo': True, 'password': 'private-root'}}
        report, events = self.collect(users)
        self.assertEqual(report['candidate_users'], ['root', 'operator'])
        self.assertEqual(events, [('operator', 'su', 'root'), ('exit', 'su', 'root')])
        self.assertEqual(report['selected_user'], 'root')

    def test_root_su_failure_then_login_sudo(self):
        actor = Actor(failures={('operator', 'su', 'root'): PermissionError})
        report, events = self.collect({'operator': {}, 'root': {'password': 'private-root'}}, actor)
        self.assertEqual(events[:2], [('operator', 'su', 'root'), ('operator', 'sudo', 'root')])
        self.assertEqual(report['selected_user'], 'operator')

    def test_missing_root_password_uses_login_sudo_and_empty_su_is_explicit(self):
        report, events = self.collect({'operator': {}, 'root': {}})
        self.assertEqual(events[0], ('operator', 'sudo', 'root'))
        self.assertEqual(report['attempts'][0]['reason_code'], 'missing_su_password')
        report, events = self.collect({'operator': {}, 'root': {'vars': {'su': {'password': ''}}}})
        self.assertEqual(events[0], ('operator', 'su', 'root'))
        self.assertTrue(report['attempts'][0]['steps'][0]['password_supplied'])

    def test_second_account_override_rejection_has_no_credential_retry(self):
        actor = Actor(failures={('maintainer', 'sudo', 'root'): PermissionError})
        report, events = self.collect({'operator': {'sudo': False},
            'maintainer': {'password': 'private-login', 'sudo-password': 'private-override'}}, actor)
        self.assertEqual(report['mode'], 'fallback_user')
        self.assertEqual(events.count(('maintainer', 'sudo', 'root')), 1)
        self.assertEqual(report['attempts'][1]['steps'][1]['password_source'], 'users.<account>.sudo-password')

    def test_login_sudo_failure_then_su_sudo(self):
        actor = Actor(failures={('operator', 'sudo', 'root'): PermissionError})
        report, events = self.collect({'operator': {}, 'maintainer': {'password': 'private-su'}}, actor)
        self.assertEqual(events[:3], [('operator', 'sudo', 'root'), ('operator', 'su', 'maintainer'),
                                     ('maintainer', 'sudo', 'root')])
        self.assertEqual(report['selected_user'], 'maintainer')

    def test_both_fail_fallback_and_no_third_candidate(self):
        actor = Actor(failures={('operator', 'sudo', 'root'): PermissionError,
                                ('maintainer', 'sudo', 'root'): PermissionError})
        users = {'operator': {}, 'maintainer': {'password': 'private-su'}, 'third': {'password': 'private-third'}}
        report, events = self.collect(users, actor)
        self.assertEqual(report['mode'], 'fallback_user')
        self.assertTrue(report['degraded'])
        self.assertEqual(report['actual_identity']['username'], 'operator')
        self.assertFalse(any('third' in event for event in events))

    def test_missing_su_password_skips_without_third_candidate(self):
        report, events = self.collect({'operator': {'sudo': False}, 'maintainer': {},
                                       'root': {'password': 'private-root'}})
        self.assertEqual(events, [])
        self.assertEqual(report['attempts'][1]['reason_code'], 'missing_su_password')
        self.assertEqual(report['mode'], 'fallback_user')

    def test_root_login_never_switches_and_root_disabled_is_not_candidate(self):
        report, events = self.collect({'root': {}, 'maintainer': {}}, Actor('root'))
        self.assertEqual(events, [])
        self.assertEqual(report['mode'], 'root')
        report, events = self.collect({'operator': {'sudo': False}, 'root': {'sudo': False}})
        self.assertEqual(report['mode'], 'user')
        self.assertEqual(report['candidate_users'], ['operator'])
        self.assertEqual(events, [])

    def test_preflight_failures_are_reused_without_authentication_retry(self):
        users = {'operator': {}, 'maintainer': {'password': 'private-su'}}
        failures = {('operator', 'sudo', 'root'): PermissionError,
                    ('maintainer', 'sudo', 'root'): PermissionError}
        preflight, _ = self.collect(users, Actor(failures=failures))
        report, events = self.collect(users, Actor(), {'access': preflight})
        self.assertEqual(events, [])
        self.assertEqual(report['mode'], 'fallback_user')
        self.assertTrue(all(a['reused_from_preflight'] for a in report['attempts']))

    def test_preflight_success_reentered_but_prior_failure_not_retried(self):
        users = {'operator': {}, 'maintainer': {'password': 'private-su'}}
        preflight, _ = self.collect(users, Actor(failures={('operator', 'sudo', 'root'): PermissionError}))
        report, events = self.collect(users, Actor(), {'access': preflight})
        self.assertEqual(events[0], ('operator', 'su', 'maintainer'))
        self.assertEqual(report['mode'], 'root')

    def test_successful_preflight_route_can_later_fail_and_use_remaining_candidate(self):
        users = {'operator': {}, 'root': {'password': 'private-root'}}
        preflight, _ = self.collect(users)
        actor = Actor(failures={('operator', 'su', 'root'): PermissionError})
        report, events = self.collect(users, actor, {'access': preflight})
        self.assertEqual(report['selected_user'], 'operator')
        self.assertEqual(events[:2], [('operator', 'su', 'root'), ('operator', 'sudo', 'root')])

    def test_unknown_identity_exit_or_nested_recovery_stops_without_fallback(self):
        users = {'operator': {'sudo': False}, 'maintainer': {'password': 'private-su'}}
        cases = [({('identity', 'maintainer')}, {}), ({('exit', 'root')}, {}),
                 ({('restore', 'root')}, {}),
                 ({('maintainer', 'sudo', 'root')}, {('maintainer', 'sudo', 'root'): TimeoutError})]
        for broken, failures in cases:
            with self.subTest(broken=broken):
                report = {}
                actor = Actor(broken=broken, failures=failures)
                with self.assertRaises(RuntimeError):
                    with policy.collection_actor(actor, self.config(users), 'h', 5, report):
                        pass
                self.assertFalse(any(a.get('user') == 'third' for a in report['attempts']))
                if ('identity', 'maintainer') not in broken:
                    self.assertFalse(report['restoration_verified'])

    def test_collection_body_failure_is_not_retried_or_hidden(self):
        actor = Actor()
        report = {}
        with self.assertRaisesRegex(ValueError, 'collection failure'):
            with policy.collection_actor(actor, self.config({'operator': {}, 'maintainer': {}}), 'h', 5, report):
                raise ValueError('collection failure')
        self.assertTrue(report['restoration_verified'])
        self.assertEqual(len(report['attempts']), 1)

    def test_root_name_without_uid_zero_is_not_root_collection(self):
        actor = Actor()
        with patch.dict(Actor.uids, {'root': 500}):
            with self.assertRaises(hr.IdentityProbeError):
                self.collect({'operator': {}}, actor)


    def test_dryrun_table_retains_alternate_attempts_and_fallback_reason(self):
        actor = Actor(failures={('operator', 'su', 'root'): PermissionError,
                                ('operator', 'sudo', 'root'): PermissionError})
        report, _ = self.collect({'operator': {}, 'root': {'password': 'private-root'}}, actor)
        rows = access.summary_tests({'host': 'h', 'status': 'success', 'connected': True,
                                     'access': report})
        self.assertEqual([(r['test'], r['user']) for r in rows],
                         [('connection', 'operator'), ('su', 'root'), ('sudo', 'operator'), ('selection', 'operator')])
        self.assertIn('fallback_user', rows[-1]['reason_code'])

    def test_real_loader_preserves_users_order_through_include_and_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'hosts.yaml').write_text('include: [child.yaml]\n')
            (root / 'child.yaml').write_text('groups:\n  test:\n    hosts:\n      h:\n        connection: {local: true}\n        users:\n          operator: {sudo: false}\n          maintainer: {}\n          root: {}\n')
            config = hr.load_config(root, 'h')
            self.assertEqual(policy.candidates(config, 'h', 'operator'), ['operator', 'maintainer'])

    def test_inventory_preflight_fallback_is_usable_and_diagnostics_stay_strict(self):
        cls = type('Session', (SyntheticSession,), {'fail_sudo': True, 'sudo_passwords': [], 'instances': []})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'hosts.yaml').write_text('hosts:\n  h:\n    connection: {local: true}\n    users:\n      operator: {}\n')
            config = hr.load_config(root, 'h')
            diagnostic = access.check_access(config, 'h', session_class=cls)
            inventory = access.check_access(config, 'h', session_class=cls, inventory=True)
        self.assertEqual(diagnostic['status'], 'failed')
        self.assertEqual(inventory['status'], 'success')
        self.assertEqual(inventory['access']['mode'], 'fallback_user')
