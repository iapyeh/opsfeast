"""Authenticated read-only profiling HTTP integration, with synthetic saved data."""
from contextlib import redirect_stdout
import io
import json
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_web_preview as web
import test_inventory_jobs as inventory


@unittest.skipUnless(web.WEB_AVAILABLE, 'optional Web dependencies not installed')
class ProfilingWebTests(unittest.IsolatedAsyncioTestCase):
    setUp = web.WebPreviewTests.setUp
    request = web.WebPreviewTests.request

    def initialize(self):
        from opsfeast import Instance
        from opsfeast.web.app import create_app
        with redirect_stdout(io.StringIO()):
            profile = Instance.open(self.root).init_profile()
        (profile.root / 'hosts.yaml').write_text('hosts: {node: {connection: {local: true}}}\n')
        return profile, create_app(self.root, agent_token='p' * 32)

    async def get(self, app, path, authorized=True):
        headers = [(b'authorization', b'Bearer ' + b'p' * 32)] if authorized else []
        status, _, body = await self.request(path, headers=headers, app=app)
        return status, json.loads(body)

    async def test_auth_scope_validation_empty_data_and_safe_storage_failure(self):
        profile, app = self.initialize()
        path = '/api/v1/profiling/host?profile=main&host_id=node'
        for route in ('/api/v1/profiling/catalog', path):
            self.assertEqual((await self.get(app, route, False))[0], 401)
        from opsfeast.core import Instance, Profile
        with patch.object(Instance, 'profile', side_effect=AssertionError('catalog requires no profile')):
            status, catalog = await self.get(app, '/api/v1/profiling/catalog?domain=identity')
        self.assertEqual(status, 200)
        self.assertEqual(catalog['domains'][0]['id'], 'identity')
        before = {str(p): p.read_bytes() for p in profile.root.rglob('*') if p.is_file()}
        status, empty = await self.get(app, path)
        self.assertEqual(status, 200)
        self.assertEqual(empty['profile'], 'main')
        self.assertTrue(all(row['state'] == 'not_collected' for row in empty['items']))
        self.assertEqual(before, {str(p): p.read_bytes() for p in profile.root.rglob('*') if p.is_file()})
        for query in ('&limit=0', '&limit=251', '&offset=-1', '&domain=missing'):
            self.assertEqual((await self.get(app, path + query))[0], 422)
        self.assertEqual((await self.get(app, path.replace('host_id=node','host_id=absent')))[0], 422)
        self.assertEqual((await self.get(app, path.replace('profile=main','profile=absent')))[0], 422)
        with patch.object(Profile, 'retention', property(lambda _: SimpleNamespace(query=lambda **_: (_ for _ in ()).throw(sqlite3.OperationalError('private/path'))))):
            status, error = await self.get(app, path)
        self.assertEqual(status, 503)
        self.assertNotIn('private/path', json.dumps(error))

    async def test_recipe_retention_http_values_times_and_no_acquisition_on_read(self):
        profile, app = self.initialize()
        acquired = inventory.InventoryJobTests.acquire(SimpleNamespace(root=profile.root), inventory.Actor(),
            properties=['storage.filesystems.used_percent'], save=True)
        self.assertEqual(acquired['retention']['status'], 'stored', acquired)
        with patch.object(inventory.service, 'connected', side_effect=AssertionError('HTTP must not acquire')):
            status, data = await self.get(app, '/api/v1/profiling/host?profile=main&host_id=node&domain=storage&limit=250')
        self.assertEqual(status, 200)
        row = next(row for row in data['items'] if row['property_id'] == 'storage.filesystems.used_percent')
        self.assertEqual(row['state'], 'complete')
        self.assertEqual(row['evidence'][0]['samples'][0]['value_preview'], '82.0')
        self.assertEqual(row['evidence'][0]['observed_at'], acquired['groups'][0]['coverage'][0]['observed_at'])
        self.assertTrue(row['evidence'][0]['record_id'])
        self.assertTrue(all(row['domain'] == 'storage' for row in data['items']))
        for asset in ('profiling.mjs', 'locales/profiling-zh-TW.mjs'):
            self.assertEqual((await self.request('/assets/' + asset, app=app))[0], 200)

    async def test_new_linux_collectors_reach_same_web_projection_without_refresh(self):
        profile, app = self.initialize()
        from test_linux_profile import files, REFERENCES
        from test_core_api import Actor, Result
        from opsfeast import linux_profile_probe as probe
        import recipe_runner
        target = self.root / 'synthetic-linux'; target.mkdir(); files(target)
        class ProfileActor(Actor):
            def exec_command(actor, argv, **kwargs):
                if argv[:3] == ['python3', '-B', '-']:
                    return Result(json.dumps(probe.snapshot(argv[3], 1000, 5, root=target)), '', 0)
                return super().exec_command(argv, **kwargs)
        for reference in REFERENCES.values():
            raw, _ = recipe_runner.run(profile.root, 'node', recipe=reference,
                session_class=ProfileActor, runtime={'verification':'synthetic-only'})
            self.assertEqual(raw['retention']['status'], 'stored', raw)
        with patch('opsfeast.linux_profile.collect', side_effect=AssertionError('viewer must not collect')):
            status, data = await self.get(app, '/api/v1/profiling/host?profile=main&host_id=node&limit=250')
        self.assertEqual(status, 200)
        users = next(p for p in data['items'] if p['property_id']=='identity.local_users')
        processes = next(p for p in data['items'] if p['property_id']=='processes.snapshot')
        self.assertEqual(users['state'], 'complete'); self.assertEqual(processes['state'], 'complete')
        self.assertIn('daemon', json.dumps(users)); self.assertIn('start_ticks', json.dumps(processes))

    async def test_policy_recipes_retain_basis_scope_and_safe_query_evidence_for_web(self):
        profile, app = self.initialize()
        from test_linux_policy import files, snapshot, REFERENCES, SECRET
        from test_core_api import Actor, Result
        import recipe_runner
        target = self.root / 'synthetic-policy'; target.mkdir(); files(target)
        class PolicyActor(Actor):
            def exec_command(actor, argv, **options):
                if argv[:3] == ['python3', '-B', '-']:
                    return Result(json.dumps(snapshot(target, argv[3], options=json.loads(argv[6]))), '', 0)
                return super().exec_command(argv, **options)
        for reference in REFERENCES.values():
            raw, _ = recipe_runner.run(profile.root, 'node', recipe=reference,
                session_class=PolicyActor, runtime={'verification':'synthetic-only'})
            self.assertEqual(raw['retention']['status'], 'stored', raw)
        with patch('opsfeast.linux_profile.collect', side_effect=AssertionError('viewer cannot acquire')):
            status, data = await self.get(app, '/api/v1/profiling/host?profile=main&host_id=node&limit=250')
        self.assertEqual(status, 200)
        self.assertEqual(data['retained_record_count'], 5)
        self.assertNotIn(SECRET, json.dumps(data))
        ssh = next(p for p in data['items'] if p['property_id']=='policy.ssh_policy')
        self.assertEqual(ssh['evidence'][0]['samples'][0]['basis'], 'configured')
        self.assertTrue(ssh['evidence'][0]['source_scope'])
        self.assertEqual(ssh['evidence'][0]['commands'][0]['argv'], ['sshd','-T'])
        clock = next(p for p in data['items'] if p['property_id']=='policy.clock_state')
        self.assertEqual(clock['state'], 'complete')
        self.assertIn('NTPSynchronized', json.dumps(clock)); self.assertIn('"no"', clock['evidence'][0]['samples'][3]['value_preview'])
