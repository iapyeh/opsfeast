"""Public, credential-free service lifecycle, adapter and CLI regressions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import io
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opsfeast import Instance, main
from opsfeast.services import Services, ServiceError
from opsfeast.service_adapters import smtp


class ServicesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with redirect_stdout(io.StringIO()):
            self.profile = Instance.open(self.temp.name).init_profile()
        self.root = self.profile.root
        self.services = self.profile.services
        self.source = dict(host_id='h', recipe_reference=':backup/check/test', subject='db', rule='missing')

    def reconcile(self, *, at='2026-10-25T01:00:00Z', active=True, **kwargs):
        values = dict(source=self.source, owner='policy', observed_at=at,
            evidence={'record_id': 'source:' + at}, active=active, title='Backup issue', body='Safe summary',
            notification=True, todo=True)
        values.update(kwargs)
        return self.services.reconcile(**values)

    def settings(self, value):
        import yaml
        p = self.root / 'feast.yaml'
        settings = yaml.safe_load(p.read_text())
        settings['services'] = value
        p.write_text(yaml.safe_dump(settings))

    def test_read_only_discovery_does_not_create_storage_or_probe(self):
        with patch('smtplib.SMTP', side_effect=AssertionError('network')):
            self.assertEqual(self.services.notifications.list(), [])
            self.assertFalse(self.services.inspect()['initialized'])
            self.assertEqual(self.services.dispatch()['status'], 'success')
        self.assertFalse((self.root / 'services').exists())

    def test_atomic_dedup_resolution_and_recurrence(self):
        self.reconcile()
        self.reconcile()
        self.reconcile(at='2026-10-26T01:00:00Z')
        self.assertEqual(len(self.services.notifications.list()), 1)
        self.assertEqual(len(self.services.todos.list()), 1)
        self.reconcile(at='2026-10-27T01:00:00Z', active=False)
        self.assertEqual(self.services.notifications.list()[0]['status'], 'resolved')
        self.assertTrue(self.services.todos.list()[0]['verified'])
        self.reconcile(at='2026-10-28T01:00:00Z')
        self.assertEqual(len(self.services.todos.list()), 2)
        self.assertEqual(len(self.services.history()), 8)

    def test_unknown_watermark_cannot_resolve_or_allow_stale_recovery(self):
        self.reconcile()
        self.reconcile(at='2026-10-27T01:00:00Z', active=None)
        result = self.reconcile(at='2026-10-26T01:00:00Z', active=False)
        self.assertEqual(result['reason_code'], 'duplicate_or_stale_observation')
        self.assertTrue(self.services.todos.list()[0]['condition_active'])

    def test_owner_conflict_rolls_back(self):
        self.reconcile()
        with self.assertRaisesRegex(ServiceError, 'condition_owner_conflict'):
            self.reconcile(at='2026-10-26T01:00:00Z', owner='other')
        self.assertEqual(len(self.services.history()), 2)

    def test_concurrent_cas_and_human_fields_survive_observation(self):
        self.reconcile()
        todo = self.services.todos.list()[0]
        def update(actor):
            try:
                return self.services.todos.update(todo['id'], expected_revision=todo['revision'], actor=actor, assignee=actor)
            except ServiceError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(update, ('alice', 'bob')))
        self.assertEqual(outcomes.count('revision_conflict'), 1)
        winner = next(o for o in outcomes if isinstance(o, dict))['assignee']
        self.reconcile(at='2026-10-26T01:00:00Z')
        self.assertEqual(self.services.todos.show(todo['id'])['assignee'], winner)

    def test_manual_done_requires_verification_and_later_failure_reopens(self):
        self.reconcile()
        todo = self.services.todos.list()[0]
        result = self.services.todos.update(todo['id'], expected_revision=1, actor='human', status='done')
        self.assertFalse(result['verified'])
        self.reconcile(at='2026-10-26T01:00:00Z')
        self.assertEqual(self.services.todos.show(todo['id'])['status'], 'open')

    def test_replay_permissions_suppress_objects_and_live_retry_survives(self):
        historical = Services(self.root, permitted_records=set())
        with patch.object(self, 'services', historical):
            self.assertEqual(self.reconcile()['reason_code'], 'historical_service_effects_disabled')
        self.assertFalse((self.root / 'services').exists())
        self.reconcile()
        reopened = Services(self.root)
        self.assertEqual(len(reopened.todos.list()), 1)

    def test_bad_changes_and_schedule_order_rejected_without_revision_change(self):
        self.reconcile()
        todo = self.services.todos.list()[0]
        for changes in ({'condition_active':False}, {'status':'invented'},
                        {'due_at':'no-timezone'}, {'start_at':'2026-10-26T01:00:00Z', 'due_at':'2026-10-25T01:00:00Z'}):
            with self.assertRaises(ServiceError):
                self.services.todos.update(todo['id'], expected_revision=1, actor='human', **changes)
        self.assertEqual(self.services.todos.show(todo['id'])['revision'], 1)

    def mail_settings(self):
        self.settings({'presentations':{}, 'deliveries':{'mail':{'source':'builtin:smtp','enabled':True,
            'config':{'host':'relay.invalid','sender':'ops@example.invalid','recipients':['user@example.invalid']}}},
            'routes':[{'minimum_severity':'warning','channels':['mail']}]})

    def test_outbox_idempotence_and_unknown_requires_explicit_retry(self):
        self.mail_settings()
        self.reconcile()
        self.reconcile(at='2026-10-26T01:00:00Z')
        self.assertEqual(len(self.services.deliveries()), 1)
        with patch('opsfeast.service_adapters.smtp', return_value={'status':'unknown'}) as send:
            self.assertEqual(self.services.dispatch()['status'], 'failed')
            self.services.dispatch()
            self.assertEqual(send.call_count, 1)
        with patch('opsfeast.service_adapters.smtp', return_value={'status':'delivered'}) as send:
            self.services.dispatch(retry_unknown=True)
            self.services.dispatch()
            self.assertEqual(send.call_count, 1)
        self.assertEqual(self.services.deliveries()[0]['status'], 'delivered')

    def test_notification_mute_read_are_independent_of_resolution(self):
        self.mail_settings()
        self.reconcile()
        obj = self.services.notifications.list()[0]
        self.services.notifications.update(obj['id'], expected_revision=1, actor='human', read=True,
                                           muted_until='2999-01-01T00:00:00Z')
        with patch('opsfeast.service_adapters.smtp', side_effect=AssertionError('must not send')):
            self.assertEqual(self.services.dispatch()['status'], 'success')
        self.assertEqual(self.services.notifications.show(obj['id'])['status'], 'active')

    def test_vault_presentation_and_unmanaged_collision(self):
        self.reconcile()
        result = self.services.dispatch()
        self.assertEqual(result['status'], 'success', result)
        index = self.root / 'vault/Services/SUMMARY.md'
        self.assertIn('Backup issue', index.read_text())
        self.assertIn('Last modified:', index.read_text())
        self.assertEqual(self.services.inspect()['presentation_receipts']['vault']['status'], 'success')
        obj = self.services.todos.list()[0]
        page = self.root / ('vault/Services/todo/' + obj['id'] + '.md')
        self.assertIn('Source record', page.read_text())
        # A second adapter cannot take another owner's output paths.
        custom = self.root / 'service-adapters/custom.py'
        custom.parent.mkdir()
        custom.write_text("API_VERSION='0.1.0'\ndef render(snapshot, config):\n    return {'Services/SUMMARY.md':'collision'}\n")
        self.settings({'presentations':{'other':{'source':'local:service-adapters/custom.py','enabled':True,
            'sha256':hashlib.sha256(custom.read_bytes()).hexdigest()}}})
        self.assertEqual(self.services.dispatch()['status'], 'failed')
        self.assertIn('Backup issue', index.read_text())

    def test_local_adapter_discovery_does_not_execute_and_drift_is_rejected(self):
        custom = self.root / 'service-adapters/custom.py'
        custom.parent.mkdir()
        custom.write_text("raise AssertionError('never import')")
        self.settings({'presentations':{'custom':{'source':'local:service-adapters/custom.py','enabled':True,
            'sha256':hashlib.sha256(custom.read_bytes()).hexdigest()}}})
        self.assertEqual(self.services.inspect()['adapters'][0]['status'], 'available')
        custom.write_text('changed')
        self.assertEqual(self.services.inspect()['adapters'][0]['status'], 'unavailable')

    def test_cli_lifecycle_and_secret_free_failure(self):
        self.reconcile()
        obj = self.services.todos.list()[0]
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(['services','update',obj['id'],'--kind','todo','--revision','1','--actor','human',
                         '--changes','{"status":"in_progress"}','--root',str(self.root),'--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['object']['status'], 'in_progress')

    def test_smtp_secure_defaults_headers_and_uncertain_send(self):
        self.reconcile(title='Hello\r\nBcc: injected')
        obj = self.services.notifications.list()[0]
        config = {'host':'relay.invalid','sender':'ops@example.invalid','recipients':['user@example.invalid']}
        with patch('smtplib.SMTP') as smtp_class:
            client = smtp_class.return_value
            client.send_message.return_value = {}
            self.assertEqual(smtp(obj, config, 'stable')['status'], 'delivered')
            client.starttls.assert_called_once()
            message = client.send_message.call_args.args[0]
            self.assertNotIn('Bcc', message)
            self.assertEqual(message['Message-ID'], '<stable@opsfeast.local>')
            client.send_message.side_effect = TimeoutError()
            self.assertEqual(smtp(obj, config, 'stable')['status'], 'unknown')
            client.close.assert_called()

    def test_guarded_recipe_service_cannot_escape_scope(self):
        def unavailable():
            raise RuntimeError('scope expired')
        view = Services(self.root, guard=unavailable)
        with self.assertRaisesRegex(RuntimeError, 'scope expired'):
            view.todos.list()

    def test_concurrent_observations_create_one_episode(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.reconcile(), range(8)))
        self.assertEqual(len(self.services.notifications.list()), 1)
        self.assertEqual(len(self.services.todos.list()), 1)

    def test_first_write_failure_rolls_back_objects_and_outbox(self):
        self.mail_settings()
        with patch.object(self.services, '_queue', side_effect=RuntimeError('synthetic transaction failure')):
            with self.assertRaises(RuntimeError):
                self.reconcile()
        self.assertEqual(self.services._list(), [])
        self.assertEqual(self.services.history(), [])
        self.assertEqual(self.services.deliveries(), [])
        self.reconcile()
        self.assertEqual(len(self.services.todos.list()), 1)

    def test_crashed_inflight_delivery_is_never_automatically_resent(self):
        self.mail_settings()
        self.reconcile()
        with self.services._db(True) as db:
            db.execute("UPDATE deliveries SET status='sending',attempts=1")
        with patch('opsfeast.service_adapters.smtp', side_effect=AssertionError('must not resend')):
            self.assertEqual(self.services.dispatch()['status'], 'failed')

    def test_resolved_condition_cancels_pending_notification_delivery(self):
        self.mail_settings()
        self.reconcile()
        self.reconcile(at='2026-10-26T01:00:00Z', active=False)
        with patch('opsfeast.service_adapters.smtp', side_effect=AssertionError('must not send')):
            self.assertEqual(self.services.dispatch()['status'], 'success')
        self.assertEqual(self.services.deliveries()[0]['status'], 'cancelled')

    def test_retry_backoff_and_disabled_channel(self):
        self.mail_settings()
        self.reconcile()
        with patch('opsfeast.service_adapters.smtp', return_value={'status':'failed'}) as send:
            self.services.dispatch()
            self.services.dispatch()
            self.assertEqual(send.call_count, 1)
        import yaml
        path = self.root/'feast.yaml'
        data = yaml.safe_load(path.read_text())
        data['services']['deliveries']['mail']['enabled'] = False
        path.write_text(yaml.safe_dump(data))
        with patch('opsfeast.service_adapters.smtp', side_effect=AssertionError('disabled channel')):
            self.services.dispatch()

    def test_both_object_creation_facades_share_one_condition(self):
        values = dict(source=self.source, owner='policy', observed_at='2026-10-25T01:00:00Z',
            evidence={'record_id':'r'}, title='Issue', body='Details')
        self.services.notifications.create(**values)
        self.services.todos.create(**values)
        self.assertEqual(len(self.services.notifications.list()), 1)
        self.assertEqual(len(self.services.todos.list()), 1)

    def test_independent_presentations_survive_another_adapter_failure(self):
        custom = self.root/'service-adapters/custom.py'
        custom.parent.mkdir()
        custom.write_text("API_VERSION='0.1.0'\ndef render(snapshot, config):\n    raise RuntimeError('private value')\n")
        self.settings({'presentations':{'broken':{'source':'local:service-adapters/custom.py','enabled':True,
            'sha256':hashlib.sha256(custom.read_bytes()).hexdigest()},
            'vault':{'source':'builtin:vault','enabled':True}}})
        self.reconcile()
        result = self.services.dispatch()
        self.assertEqual(result['status'], 'failed')
        self.assertTrue((self.root/'vault/Services/SUMMARY.md').exists())
        self.assertNotIn('private value', json.dumps(result))

    def test_cancelled_todo_is_not_silently_overridden_by_observations(self):
        self.reconcile()
        obj = self.services.todos.list()[0]
        self.services.todos.update(obj['id'], expected_revision=1, actor='human', status='cancelled')
        self.reconcile(at='2026-10-26T01:00:00Z')
        self.reconcile(at='2026-10-27T01:00:00Z', active=False)
        self.assertEqual(self.services.todos.show(obj['id'])['status'], 'cancelled')

    def test_html_and_vault_presentations_run_together_with_independent_ownership(self):
        custom = self.root/'service-adapters/html.py'
        custom.parent.mkdir()
        custom.write_text("API_VERSION='0.1.0'\ndef render(snapshot, config):\n    return {'index.html':'<html><body>Tasks</body></html>'}\n")
        self.settings({'presentations':{
            'html':{'source':'local:service-adapters/html.py','enabled':True,'destination':'files',
                    'sha256':hashlib.sha256(custom.read_bytes()).hexdigest()},
            'vault':{'source':'builtin:vault','enabled':True}}})
        self.reconcile()
        self.assertEqual(self.services.dispatch()['status'], 'success')
        self.assertTrue((self.root/'services/presentations/html/index.html').is_file())
        self.assertTrue((self.root/'vault/Services/SUMMARY.md').is_file())
        from opsfeast.service_adapters import publish_files
        with self.assertRaises(ServiceError):
            publish_files(self.root, 'html', {'../escape.html':'bad'})
        unmanaged = self.root/'services/presentations/html/human.html'
        unmanaged.write_text('human')
        with self.assertRaises(ServiceError):
            publish_files(self.root, 'html', {'human.html':'overwrite'})

    def test_public_recipe_facade_expires_with_the_session(self):
        from test_core_api import Actor
        from opsfeast import CoreError
        (self.root/'hosts.yaml').write_text(json.dumps({'hosts':{'h':{'connection':{'local':True}}}}))
        self.profile.reload()
        with self.profile.sessions._connect('h', session_class=Actor) as recipe:
            services = recipe.services
            self.assertEqual(services.todos.list(), [])
        with self.assertRaises(CoreError):
            services.todos.list()

    def test_concurrent_dispatch_delivers_once(self):
        self.mail_settings()
        self.reconcile()
        with patch('opsfeast.service_adapters.smtp', return_value={'status':'delivered'}) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _:self.services.dispatch(), range(2)))
        self.assertTrue(all(r['status']=='success' for r in results))
        self.assertEqual(send.call_count, 1)

    def test_installed_package_services_and_registered_schema_are_self_contained(self):
        import build_backend
        import subprocess
        import zipfile
        import os
        wheel_dir = self.root/'wheel'
        wheel_dir.mkdir()
        wheel = wheel_dir/build_backend.build_wheel(wheel_dir)
        installed = self.root/'installed'
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(installed)
        code = '''
from opsfeast import Instance
from opsfeast.backup_check import descriptor
from retention_contracts import validate_declaration, location, normalizer_digest, implementation
import tempfile
with tempfile.TemporaryDirectory() as root:
    profile = Instance.open(root).init_profile()
    assert profile.services.inspect()['lifecycle'] == 'platform'
    metadata = descriptor({'author': {'name':'Synthetic','contacts':['x@example.invalid']},'license':'MIT'})
    declaration = validate_declaration(metadata)
    assert location(('backup-files-check','0.1.0'))[0].is_file()
    assert implementation(('backup-files-check','0.1.0'),normalizer_digest(declaration))['CONTRACT'] == 'backup-files-check'
'''
        result = subprocess.run([sys.executable,'-B','-c',code], cwd=self.root,
            env=dict(os.environ,PYTHONPATH=str(installed)+os.pathsep+os.environ.get('PYTHONPATH','')), capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_resolution_between_pending_read_and_claim_cannot_resurrect_delivery(self):
        self.mail_settings()
        self.reconcile()
        original = self.services.deliveries
        def pending_then_resolve():
            pending = original()
            self.reconcile(at='2026-10-26T01:00:00Z', active=False)
            return pending
        with patch.object(self.services, 'deliveries', side_effect=pending_then_resolve):
            with patch('opsfeast.service_adapters.smtp', side_effect=AssertionError('cancelled delivery')):
                self.assertEqual(self.services.dispatch()['status'], 'success')
        self.assertEqual(original()[0]['status'], 'cancelled')

    def test_resolution_during_failed_send_cancels_future_retry(self):
        self.mail_settings()
        self.reconcile()
        def send(*args):
            self.reconcile(at='2026-10-26T01:00:00Z', active=False)
            return {'status':'failed'}
        with patch('opsfeast.service_adapters.smtp', side_effect=send):
            self.services.dispatch()
        self.assertEqual(self.services.deliveries()[0]['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
