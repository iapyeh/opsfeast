"""Public recipe-menu/review/worker/retention tests; synthetic data, no SSH."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from opsfeast import ConfigError, Instance
from opsfeast.recipe_runs import RecipeRuns, prepare_pair


class RecipeRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()): self.profile = Instance.open(self.root).init_profile()
        self.hosts = self.profile.root / 'hosts.yaml'
        self.hosts.write_text('hosts: {node: {connection: {local: true}}, other: {connection: {local: true}}}\n')
        self.service = RecipeRuns(self.root, self.root)
        self.addCleanup(self.service.close)

    def selection(self, reference='system/account/inventory/local-users', *, variables=None, hosts=None):
        return {'profile': 'main', 'hosts': ['node'] if hosts is None else hosts,
                'recipes': [{'reference': reference, 'vars': variables or {}, 'inputs': []}], 'timeout': 30}

    def wait(self, identifier):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            result = self.service.show(identifier, 'main')
            if result['state'] not in ('running', 'stopping'): return result
            time.sleep(.03)
        self.fail('synthetic worker did not complete')

    def test_menu_uses_current_catalog_blueprint_and_never_executes(self):
        from opsfeast.recipe_menu import menu
        with patch('subprocess.Popen', side_effect=AssertionError('no execution during discovery')):
            data = menu(self.profile)
        self.assertEqual(len(data['items']), 25)
        self.assertEqual(len(data['blueprint']['capabilities']), 39)
        self.assertEqual(sum(c['integration'] == 'partial' for c in data['blueprint']['capabilities']), 27)
        ssh = next(i for i in data['items'] if i['reference'].endswith('/ssh-policy'))
        self.assertIn('identity.authentication', ssh['capabilities'])
        self.assertIn('Match', ssh['purpose'])
        self.assertTrue(all(i['runnable'] for i in data['items']))

    def test_preview_is_read_only_explicit_scope_typed_and_nonsecret(self):
        before = {str(p): p.read_bytes() for p in self.profile.root.rglob('*') if p.is_file()}
        with patch('subprocess.Popen', side_effect=AssertionError('preview cannot execute')):
            preview = self.service.preview(self.selection(variables={'max_items': 12}))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.profile.root.rglob('*') if p.is_file()})
        self.assertFalse(self.service.directory.exists())
        self.assertEqual(preview['pairs'][0]['variable_names'], ['command_timeout_seconds', 'max_items'])
        self.assertFalse(preview['pairs'][0]['identity']['verified'])
        self.assertTrue(preview['explicit_host_override'])
        self.assertNotIn('effective_vars', json.dumps(preview))
        for bad in [self.selection(variables={'max_items': '12'}), self.selection(hosts=['absent']), self.selection(hosts=[]), self.selection(variables={'password': 'secret'})]:
            with self.assertRaises(ConfigError): self.service.preview(bad)
        bad = self.selection(); bad['recipes'][0]['reference'] = 'linux-local-accounts'
        with self.assertRaises(ConfigError): self.service.preview(bad)

    def test_all_hosts_minus_localhost_has_no_host_or_invocation_count_limit(self):
        hosts=['localhost']+['node-'+str(i) for i in range(160)]
        self.hosts.write_text(json.dumps({'hosts':{h:{'connection':{'local':True}} for h in hosts}}))
        def pair(root,reference,host,variables,inputs,selection=None):
            return {'reference':reference,'host_id':host,'invocation':[],'composition':None},{}
        with patch('opsfeast.recipe_runs.prepare_pair',side_effect=pair),patch('recipe_catalog.choose',return_value={'kind':'operation'}):
            body=self.selection(hosts=hosts[1:])
            body['recipes']=[{'reference':'synthetic-'+str(i),'vars':{},'inputs':[]} for i in range(32)]
            plan=self.service.preview(body)
        self.assertEqual(len(plan['pairs']),5120)
        self.assertNotIn('threads',plan)
        self.assertNotIn('localhost',{p['host_id'] for p in plan['pairs']})
        self.assertFalse(self.service.directory.exists())

    def test_confirmation_expiry_changed_configuration_and_descriptor_fail_closed(self):
        preview = self.service.preview(self.selection())
        for confirmed in (False, 1, 'true'):
            with self.assertRaises(ConfigError): self.service.start(preview['preview_id'], confirmed)
        self.hosts.write_text(self.hosts.read_text() + '# changed after review\n')
        with self.assertRaisesRegex(ConfigError, 'changed'): self.service.start(preview['preview_id'], True)
        preview = self.service.preview(self.selection())
        self.service.plans[preview['preview_id']]['expires'] = 0
        with self.assertRaisesRegex(ConfigError, 'expired'): self.service.start(preview['preview_id'], True)
        with self.assertRaises(ConfigError): self.service.show('../outside', 'main')

    def test_nested_meal_preview_unions_fields_and_rejects_changed_definition_before_start(self):
        from opsfeast.menu_preferences import inspect,mutate
        ref='system/inventory/hardware-sensors'
        def save(fields):
            return mutate(self.root,profile='main',expected_revision=inspect(self.profile)['revision'],action='set.create',changes={'title':'Sensors','description':'','recipes':[ref],'meals':[],'selections':{ref:{'properties':fields}}})['sets'][-1]['id']
        a=save(['sensors.fans']);b=save(['sensors.temperatures'])
        selection={'profile':'main','hosts':['node','other'],'recipes':[],'meals':[a,b],'timeout':30}
        plan=self.service.preview(selection)
        self.assertEqual(len(plan['pairs']),2)
        for pair in plan['pairs']:
            self.assertEqual(set(pair['inventory_selection']['properties']),{'sensors.fans','sensors.temperatures'})
        mutate(self.root,profile='main',expected_revision=inspect(self.profile)['revision'],action='set.delete',changes={'id':a})
        with patch('subprocess.Popen',side_effect=AssertionError('must not start')):
            with self.assertRaises(ConfigError):self.service.start(plan['preview_id'],True)
        self.assertFalse(self.service.directory.exists())

    def test_nested_offline_report_worker_runs_duplicate_recipe_only_once(self):
        from opsfeast.menu_preferences import inspect,mutate
        ids=[]
        for title in ('Inner A','Inner B'):
            state=mutate(self.root,profile='main',expected_revision=inspect(self.profile)['revision'],action='set.create',changes={'title':title,'description':'','recipes':['feast/report/retention-summary'],'meals':[],'selections':{}})
            ids.append(state['sets'][-1]['id'])
        plan=self.service.preview({'profile':'main','hosts':[],'recipes':[],'meals':ids,'timeout':30})
        self.assertEqual(len(plan['pairs']),1)
        record=self.wait(self.service.start(plan['preview_id'],True)['id'])
        self.assertEqual(record['state'],'completed',record)
        self.assertEqual(len(record['tasks']),1)
        self.assertEqual(record['selected_meals'],ids)
        self.assertTrue(record['tasks'][0]['result']['artifacts'])

    def test_real_offline_report_worker_and_saved_artifact_no_host(self):
        selection = self.selection('feast/report/retention-summary', variables={'title': 'Synthetic feast'}, hosts=[])
        preview = self.service.preview(selection)
        self.assertIsNone(preview['pairs'][0]['host_id'])
        started = self.service.start(preview['preview_id'], True)
        record = self.wait(started['id'])
        self.assertEqual(record['state'], 'completed', record)
        result = record['tasks'][0]['result']
        self.assertEqual(result['status'], 'success')
        self.assertTrue((self.profile.root / result['result_id']).is_file())
        self.assertTrue(result['artifacts'])
        self.assertNotIn('"vars"', (self.service.directory / (record['id']+'.json')).read_text())
        self.assertEqual(result['artifacts'][0]['title'], 'Synthetic feast')
        repeated = self.service.start(preview['preview_id'], True)
        self.assertEqual(repeated['id'], record['id'])
        recovered = RecipeRuns(self.root, self.root)
        self.assertEqual(recovered.show(record['id'], 'main')['state'], 'completed')
        with self.assertRaises(ConfigError): recovered.show(record['id'], 'other')

    def test_report_inputs_are_saved_result_ids_not_arbitrary_server_files(self):
        for input_id in ('/etc/passwd', '../hosts.yaml', 'hosts.yaml'):
            selection = self.selection('feast/report/execution-summary', hosts=[])
            selection['recipes'][0]['inputs'] = [input_id]
            with self.assertRaises(ConfigError): self.service.preview(selection)

    def test_worker_operation_uses_same_runner_retention_and_typed_overrides(self):
        from opsfeast.recipe_run_worker import main
        from test_linux_profile import files, probe, Actor, Result
        from opsfeast.profiling import inspect_host
        import recipe_runner
        target = self.root / 'synthetic-target'; target.mkdir(); files(target)
        class SyntheticActor(Actor):
            def exec_command(actor, argv, **options):
                if argv[:3] == ['python3', '-B', '-']:
                    return Result(json.dumps(probe.snapshot(argv[3], int(argv[4]), 5, root=target)), '', 0)
                return super().exec_command(argv, **options)
        choice = self.selection(variables={'max_items': 1})
        preview = self.service.preview(choice)
        spec = {'root': str(self.profile.root), 'reference': choice['recipes'][0]['reference'], 'host': 'node',
                'vars': {'max_items': 1}, 'inputs': [], 'fingerprint': preview['pairs'][0]['fingerprint'], 'timeout': 30}
        run = recipe_runner.run
        def synthetic(*args, **kwargs):
            return run(*args, **kwargs, session_class=SyntheticActor, runtime={'verification': 'synthetic-only'})
        stdout = io.StringIO()
        with patch('sys.stdin', type('Input', (), {'buffer': io.BytesIO(json.dumps(spec).encode())})()), \
             patch.object(recipe_runner, 'run', side_effect=synthetic), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)  # max_items is enforced and incomplete enumeration stays partial.
        result = json.loads(stdout.getvalue())
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['retention']['status'], 'stored')
        self.profile.reload()
        saved = inspect_host(self.profile, 'node', domain='identity')
        row = next(r for r in saved['items'] if r['property_id'] == 'identity.local_users')
        self.assertTrue(row['evidence'])

    def test_worker_uses_packaged_web_and_module_resources(self):
        import build_backend
        resources = {p.as_posix() for p in build_backend.source_files()}
        for path in ('web/index.html', 'web/assets/recipe-menu.mjs', 'web/assets/locales/recipe-menu-zh-TW.mjs',
                     'opsfeast/recipe_run_worker.py', 'docs/web-recipe-menu.md'):
            self.assertIn(path, resources)

    def test_rebound_profile_cannot_continue_preview_or_read_another_roots_history(self):
        preview = self.service.preview(self.selection())
        original = self.service._profile_binding('main')
        with patch.object(self.service, '_profile_binding', return_value='different-root'):
            with self.assertRaisesRegex(ConfigError, 'changed'):
                self.service.start(preview['preview_id'], True)
        record = {'id': '00000000-0000-4000-8000-000000000002', 'profile': 'main',
                  'profile_binding': original, 'state': 'completed', 'created_at': '2026-11-09T00:00:00Z', 'tasks': []}
        self.service._save(record)
        with patch.object(self.service, '_profile_binding', return_value='different-root'):
            with self.assertRaises(ConfigError): self.service.show(record['id'], 'main')
            self.assertEqual(self.service.list('main')['items'], [])

    def test_worker_limits_and_malformed_output_are_failures_without_stopping_following_tasks(self):
        real = subprocess.Popen
        def launch(argv, **kwargs):
            return real([sys.executable,'-u','-c','import sys; sys.stdin.read(); print("x"*1000); print("progress"*100,file=sys.stderr)'], **kwargs)
        preview = self.service.preview(self.selection(hosts=['node','other']))
        with patch('opsfeast.recipe_runs.subprocess.Popen', side_effect=launch), \
             patch('opsfeast.recipe_runs.MAX_STDOUT', 100), patch('opsfeast.recipe_runs.MAX_PROGRESS', 32):
            result = self.wait(self.service.start(preview['preview_id'], True)['id'])
        self.assertEqual(result['state'], 'completed_with_gaps')
        self.assertTrue(all(t['reason_code']=='worker_output_limit' for t in result['tasks']))
        self.assertTrue(all(t['progress_truncated'] and len(t['progress'])<=32 for t in result['tasks']))

    def test_worker_wall_deadline_confirms_only_owned_local_termination(self):
        real = subprocess.Popen
        def launch(argv, **kwargs):
            return real([sys.executable,'-u','-c','import sys,time; sys.stdin.read(); time.sleep(30)'], **kwargs)
        preview = self.service.preview(self.selection())
        with patch('opsfeast.recipe_runs.subprocess.Popen', side_effect=launch), patch('opsfeast.recipe_runs.WORKER_DEADLINE', .1):
            result = self.wait(self.service.start(preview['preview_id'], True)['id'])
        self.assertEqual(result['tasks'][0]['reason_code'], 'worker_deadline')
        self.assertEqual(result['tasks'][0]['local_termination'], 'confirmed')
        self.assertEqual(result['remote_cleanup'], 'unknown')

    def test_stop_owned_worker_skips_remaining_and_never_claims_remote_cleanup(self):
        selection = self.selection(hosts=['node', 'other'])
        preview = self.service.preview(selection)
        real = subprocess.Popen
        def launch(argv, **kwargs):
            return real([sys.executable, '-u', '-c', 'import sys,time; sys.stdin.read(); print("synthetic-progress",file=sys.stderr,flush=True); time.sleep(30)'], **kwargs)
        with patch('opsfeast.recipe_runs.subprocess.Popen', side_effect=launch):
            started = self.service.start(preview['preview_id'], True, threads=1)
            deadline = time.monotonic() + 3
            while not self.service.show(started['id'], 'main')['tasks'][0]['progress'] and time.monotonic() < deadline: time.sleep(.02)
            with self.assertRaisesRegex(ConfigError, 'already_running'):
                self.service.start(self.service.preview(self.selection())['preview_id'], True)
            self.service.stop(started['id'], 'main')
            result = self.wait(started['id'])
        self.assertEqual(result['state'], 'stopped')
        self.assertEqual(result['tasks'][0]['local_termination'], 'confirmed')
        self.assertEqual(result['tasks'][1]['state'], 'skipped')
        self.assertEqual(result['remote_cleanup'], 'unknown')
        self.assertIn('synthetic-progress', result['tasks'][0]['progress'])

    def test_interrupted_record_is_never_replayed_or_signalled(self):
        record = {'id': '00000000-0000-4000-8000-000000000001', 'profile': 'main', 'state': 'running', 'created_at': '2026-11-09T00:00:00Z'}
        record['profile_binding'] = self.service._profile_binding('main')
        self.service._save(record)
        with patch('subprocess.Popen', side_effect=AssertionError()), patch('os.killpg', side_effect=AssertionError()):
            result = self.service.show(record['id'], 'main')
        self.assertEqual(result['state'], 'interrupted')
        self.assertEqual(result['remote_cleanup'], 'unknown')
        self.assertEqual(self.service.list('main')['total'], 1)


    def test_compatible_recipes_use_one_worker_and_distribute_child_receipts(self):
        choice=self.selection('system/inventory/system')
        choice['recipes'][0]['inventory_selection']={'properties':['system.hostname']}
        choice['recipes'].append({'reference':'system/inventory/storage-capacity','vars':{},'inputs':[],'inventory_selection':{'properties':['storage.filesystems.used_percent']}})
        reviewed=self.service.preview(choice)
        self.assertEqual(len(reviewed['connection_groups']),1)
        calls=[]
        def invoke(task,spec,record):
            calls.append(spec)
            task.update(state='success',progress='Shared worker: synthetic routines completed',result={'status':'success','meal_run_id':'synthetic-meal','content_update':{'status':'success'},'children':[{'recipe':{'reference':member['reference']},'status':'success','retention':{'status':'stored'},'result_path':'observations/synthetic.json'} for member in spec['batch']]})
        with patch.object(self.service,'_invoke',invoke):
            started=self.service.start(reviewed['preview_id'],True)
            result=self.wait(started['id'])
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0]['batch']),2)
        self.assertEqual(result['state'],'completed')
        self.assertTrue(all(t['state']=='success' and 'Shared worker' in t['progress'] for t in result['tasks']))
        self.assertEqual({t['result']['recipe']['reference'] for t in result['tasks']},{r['reference'] for r in choice['recipes']})


import test_web_preview as web

@unittest.skipUnless(web.WEB_AVAILABLE, 'optional Web dependencies absent')
class RecipeRunWebTests(unittest.IsolatedAsyncioTestCase):
    setUp = web.WebPreviewTests.setUp
    request = web.WebPreviewTests.request

    async def test_auth_origin_exact_confirmation_and_read_only_discovery(self):
        from opsfeast.web.app import create_app
        with contextlib.redirect_stdout(io.StringIO()): profile = Instance.open(self.root).init_profile()
        (profile.root/'hosts.yaml').write_text('groups: {web: {label: Web servers, hosts: {node: {connection: {local: true}}}}}\n')
        app = create_app(self.root, agent_token='r'*32)
        auth = [(b'authorization', b'Bearer '+b'r'*32)]
        content = [(b'content-type', b'application/json')]
        self.assertEqual((await self.request('/api/v1/recipe-menu', app=app))[0], 401)
        status, _, raw = await self.request('/api/v1/recipe-menu?profile=main', headers=auth, app=app)
        self.assertEqual(status, 200); self.assertEqual(len(json.loads(raw)['items']), 25)
        self.assertEqual(json.loads(raw)['groups'],[{'id':'web','title':'Web servers','host_ids':['node']}])
        self.assertNotIn('login_user',json.loads(raw)['hosts'][0])
        body = json.dumps({'profile':'main','hosts':['node'],'recipes':[{'reference':'system/account/inventory/local-users','vars':{},'inputs':[]}],'timeout':30}).encode()
        for headers, expected in ((content,401),(auth+content+[(b'origin',b'https://outside.invalid')],403)):
            self.assertEqual((await self.request('/api/v1/recipe-runs/preview','POST',body=body,headers=headers,app=app))[0],expected)
        status, _, raw = await self.request('/api/v1/recipe-runs/preview','POST',body=body,headers=auth+content,app=app)
        self.assertEqual(status,200); preview=json.loads(raw)
        with patch.object(app.state.recipe_runs, '_invoke', side_effect=lambda task,spec,record: task.update(state='success')):
            confirmed=json.dumps({'preview_id':preview['preview_id'],'confirmed':True}).encode()
            status, _, raw = await self.request('/api/v1/recipe-runs','POST',body=confirmed,headers=auth+content,app=app)
            self.assertEqual(status,200)
            app.state.recipe_runs.thread.join(2)
        run=json.loads(raw)
        self.assertEqual((await self.request('/api/v1/recipe-runs/'+run['id']+'?profile=main',headers=auth,app=app))[0],200)
        self.assertEqual((await self.request('/api/v1/recipe-runs/preview','POST',body=b'{}',headers=auth,app=app))[0],415)
        self.assertEqual((await self.request('/api/v1/recipe-runs/preview','POST',body=b'x'*65537,headers=auth+content,app=app))[0],413)
        app.state.recipe_runs.close()
