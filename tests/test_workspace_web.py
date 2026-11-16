"""Credential-free Web data tests; no managed hosts, recipe imports or writes."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_web_preview as fixtures


@unittest.skipUnless(fixtures.WEB_AVAILABLE, 'optional Web dependencies not installed')
class WorkspaceWebTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.WebPreviewTests.setUp
    request = fixtures.WebPreviewTests.request

    def initialize(self):
        from opsfeast import Instance, admin
        from opsfeast.web.app import create_app
        with redirect_stdout(io.StringIO()):
            profile = Instance.open(self.root).init_profile()
        admin.configure(self.root, username='synthetic', password='fixture', expected_revision=0)
        (self.root / 'VERSION').write_text('0.0.fixture')
        return profile, create_app(self.root, agent_token='a' * 32)

    async def get(self, app, path, authorized=True):
        headers = [(b'authorization', b'Bearer ' + b'a' * 32)] if authorized else []
        status, _, body = await self.request(path, headers=headers, app=app)
        return status, json.loads(body)

    async def test_authentication_and_parameter_boundaries(self):
        _, app = self.initialize()
        for section in ('summary', 'recipes', 'work', 'retention', 'logs'):
            self.assertEqual((await self.get(app, '/api/v1/workspace/' + section, False))[0], 401)
        for query in ('?limit=0', '?limit=251', '?offset=-1'):
            self.assertEqual((await self.get(app, '/api/v1/workspace/work' + query))[0], 422)
        self.assertEqual((await self.get(app, '/api/v1/workspace/missing'))[0], 404)
        self.assertEqual((await self.get(app, '/api/v1/workspace/work?profile=missing'))[0], 422)
        status, versions = await self.get(app, '/api/v1/updates')
        self.assertEqual(status, 200)
        self.assertEqual(versions['opsfeast']['version'], '0.0.fixture')
        self.assertIn('supported_version', versions['sshscript'])

    async def test_empty_views_are_read_only_and_catalog_is_real(self):
        profile, app = self.initialize()
        def snapshot():
            return {str(p.relative_to(profile.root)): p.read_bytes() for p in profile.root.rglob('*') if p.is_file()}
        before = snapshot()
        for section in ('work', 'retention', 'logs'):
            status, data = await self.get(app, '/api/v1/workspace/' + section)
            self.assertEqual(status, 200)
            self.assertEqual(data['items'], [])
            self.assertEqual(data['total'], 0)
            self.assertIsNone(data['next_offset'])
            self.assertEqual(data['profile'], 'main')
        _, data = await self.get(app, '/api/v1/workspace/recipes?limit=1')
        self.assertGreater(data['total'], 1)
        self.assertEqual(data['next_offset'], 1)
        self.assertEqual(len(data['items']), 1)
        self.assertNotIn('directory', data['items'][0])
        self.assertNotIn('descriptor', data['items'][0])
        _, selected = await self.get(app, '/api/v1/workspace/recipes?item_id=system/inventory/overview')
        self.assertEqual(selected['total'], 1)
        self.assertEqual(selected['items'][0]['reference'], 'system/inventory/overview')
        self.assertEqual(snapshot(), before)

    async def test_real_services_profile_selection_and_partial_failure(self):
        profile, app = self.initialize()
        profile.services.reconcile(source=dict(host_id='fixture-host', recipe_reference=':check/test', subject='db', rule='missing'),
            owner='fixture', observed_at='2026-11-01T01:00:00Z', evidence={'record_id':'fixture'},
            title='<script>fixture</script>', body='Saved evidence', active=True, notification=True, todo=True)
        _, data = await self.get(app, '/api/v1/workspace/work?profile=main&limit=1')
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['next_offset'], 1)
        _, summary = await self.get(app, '/api/v1/workspace/summary')
        self.assertEqual(summary['components']['notifications']['total'], 1)
        self.assertEqual(summary['components']['todos']['items'][0]['body'], 'Saved evidence')
        from opsfeast.services import Objects
        with patch.object(Objects, 'list', side_effect=OSError('private/path')):
            status, summary = await self.get(app, '/api/v1/workspace/summary')
            self.assertEqual(status, 200)
            self.assertEqual(summary['status'], 'partial')
            self.assertEqual(summary['components']['todos'], {'status':'unavailable'})
            self.assertNotIn('private/path', json.dumps(summary))
            self.assertEqual((await self.get(app, '/api/v1/workspace/work'))[0], 503)

    async def test_retention_and_console_history_use_saved_sources(self):
        profile, app = self.initialize()
        from opsfeast.core import Profile
        from opsfeast.console_records import Records
        from types import SimpleNamespace
        retained = {'record_id':'saved-id', 'host_id':'fixture', 'recipe_reference':':check/test',
                    'observed_at':'2026-11-01T01:00:00Z', 'kind':'observation', 'data':{'status':'partial', 'private_payload':'not-in-index'}}
        with patch.object(Profile, 'retention', new_callable=lambda: property(lambda _: SimpleNamespace(query=lambda: {'records':[retained]}, runs=lambda: []))):
            _, data = await self.get(app, '/api/v1/workspace/retention')
            self.assertEqual(data['items'][0]['status'], 'partial')
            self.assertEqual(data['items'][0]['observed_at'], retained['observed_at'])
            self.assertNotIn('not-in-index', json.dumps(data))
        sid = '11af0ac8-f21c-49ec-a5de-8f99d8116aac'
        session = {'session_id':sid, 'title':'Saved console', 'created_at':'2026-11-01T01:00:00Z'}
        calls=[]
        def saved(_, host, **kwargs):
            calls.append(host)
            return {'sessions':[session], 'next_cursor':None}
        with patch.object(Records, 'list_sessions', saved):
            _, data = await self.get(app, '/api/v1/workspace/logs')
        self.assertTrue(calls)
        self.assertTrue(all(host.startswith('main / ') for host in calls))
        self.assertEqual(data['total'], 1)  # Shared sessions are deduplicated.
        self.assertEqual(data['items'][0]['url'], '/console/' + sid + '/history')

    async def test_document_allowlist_symlinks_and_untrusted_text(self):
        _, app = self.initialize()
        docs = self.root / 'docs'
        docs.mkdir()
        (docs / 'guide.md').write_text('# Fixture\n<script>inert source</script>')
        (self.root / 'private.md').write_text('never exposed')
        (docs / 'escape.md').symlink_to(self.root / 'private.md')
        (self.root / 'README.md').write_text('# Public entry')
        status, data = await self.get(app, '/api/v1/library', False)
        self.assertEqual(status, 200)
        self.assertEqual({item['path'] for item in data['items']}, {'README.md','docs/guide.md'})
        _, data = await self.get(app, '/api/v1/library/content?path=docs/guide.md', False)
        self.assertIn('<script>', data['content'])  # JSON source, never executable HTML.
        for name in ('../private.md', 'private.md', 'docs/escape.md', '.opsfeast.yaml', 'AGENTS.local.md'):
            self.assertEqual((await self.get(app, '/api/v1/library/content?path=' + name, False))[0], 404)
        self.assertEqual((await self.get(app, '/api/v1/library?kind=private', False))[0], 422)

    async def test_recipe_settings_separate_bundle_from_profile_sources(self):
        _, app = self.initialize()
        from opsfeast.core import Instance
        with patch.object(Instance, 'profile', side_effect=AssertionError('bundle must not open a Profile')):
            status, data = await self.get(app, '/api/v1/workspace/recipes?scope=bundle')
        self.assertEqual(status, 200)
        self.assertIsNone(data['profile'])
        self.assertTrue(data['items'])
        self.assertTrue(all(item['source']=='repository' for item in data['items']))
        status, data = await self.get(app, '/api/v1/workspace/recipes?scope=user&profile=main')
        self.assertEqual(status, 200)
        self.assertEqual(data['profile'], 'main')
        self.assertEqual(data['items'], [])
        self.assertEqual((await self.get(app, '/api/v1/workspace/recipes?scope=invalid'))[0], 422)
        catalog={'status':'failed','sources':[
            {'name':'repository','enabled':True,'status':'unavailable','errors':['fixture bundle failure']},
            {'name':'profile','enabled':True,'status':'available','errors':[]}],
            'recipes':[{'reference':':fixture','source':'profile','status':'success'}]}
        with patch('recipe_catalog.catalog',return_value=catalog):
            _, data = await self.get(app, '/api/v1/workspace/recipes?scope=user&profile=main')
        self.assertEqual(data['status'],'success')
        self.assertEqual([item['name'] for item in data['sources']],['profile'])

    async def test_diagnosis_uses_selected_profile_and_requires_login(self):
        selected, app=self.initialize()
        path='/api/v1/results/diagnosis?profile=main&result_id=fixture&limit=10'
        self.assertEqual((await self.get(app,path,False))[0],401)
        with patch('result_diagnostics.diagnose',return_value={'status':'partial','coverage_gaps':[{'reason_code':'unsupported_platform_or_probe'}]}) as diagnose:
            status,data=await self.get(app,path)
        self.assertEqual(status,200)
        self.assertEqual(data['profile'],'main')
        self.assertEqual(data['status'],'partial')
        diagnose.assert_called_once_with(selected.root.resolve(),'fixture',limit=10,kind='operation')
        self.assertEqual((await self.get(app,path.replace('limit=10','limit=51')))[0],422)

    async def test_activity_recipe_and_meal_titles_search_and_path_fallback(self):
        profile, app = self.initialize()
        from opsfeast.core import Profile
        from types import SimpleNamespace
        from opsfeast.recipe_menu import GUIDANCE
        from uuid import uuid4
        service=app.state.recipe_runs
        record_id=str(uuid4());record={'id':record_id,'profile':'main','profile_binding':service._profile_binding('main'),'state':'completed','tasks':[
            {'reference':'system/software/check/package-security','title':'Saved recipe title','meal_titles':['Saved meal <name>'],'result':{'observation_run_id':'saved'}},
        ]}
        service._save(record)
        runs=[{'run_id':key,'started_at':'2026-11-01T01:00:00Z','recipe_reference':ref,'status':'success'} for key,ref in [('saved','system/software/check/package-security'),('cli','system/inventory/system'),('missing',':removed/check')]]
        with patch.object(Profile,'retention',new_callable=lambda:property(lambda _:SimpleNamespace(runs=lambda:runs))):
            _,data=await self.get(app,'/api/v1/workspace/logs')
            rows={r['id']:r for r in data['items']}
            self.assertEqual(rows['saved']['title'],'Saved meal <name> · Saved recipe title')
            self.assertEqual(rows['saved']['recipe_reference'],'system/software/check/package-security')
            self.assertEqual(rows['cli']['title'],GUIDANCE['system/inventory/system'][0])
            self.assertEqual(rows['missing']['title'],':removed/check')
            for query in ('Saved%20meal','system/software/check/package-security'):
                _,filtered=await self.get(app,'/api/v1/workspace/logs?q='+query)
                self.assertEqual([r['id'] for r in filtered['items']],['saved'])
        self.assertEqual(service.show(record_id,'main')['tasks'][0]['title'],'Saved recipe title')

    async def test_activity_existing_meals_resolve_names_without_rewriting_history(self):
        profile, app = self.initialize()
        from opsfeast.recipe_activity import history_labels
        from uuid import uuid4
        service=app.state.recipe_runs;identifier=str(uuid4())
        record={'id':identifier,'profile':'main','profile_binding':service._profile_binding('main'),'state':'completed','selected_meals':['bundle:package-security'],'tasks':[{'reference':'system/software/check/package-security','result':{'observation_run_id':'old'}}]}
        service._save(record);before=service._path(identifier).read_bytes()
        _,labels=history_labels(profile,service)
        self.assertIn('OS 套件弱點分析套餐',labels['old']['title'])
        self.assertEqual(service._path(identifier).read_bytes(),before)

    async def test_selected_activity_loads_bounded_result_summary_but_list_does_not(self):
        profile,app=self.initialize()
        from opsfeast.core import Profile
        from types import SimpleNamespace
        run={'run_id':'run','recipe_reference':'system/software/check/package-security','started_at':'2026-11-01T01:00:00Z','status':'partial','targets':[{'host_id':'node','status':'partial'}]}
        saved=[{'observation_run_id':'run','host_id':'node','status':'partial','result_id':'observations/synthetic.json','short_id':'synthetic'}]
        raw={'data':{'stages':[{'stage':'advisories','status':'failed','reason_code':'vendor_acquisition_failed'}]}}
        with patch.object(Profile,'retention',new_callable=lambda:property(lambda _:SimpleNamespace(runs=lambda:[run]))),patch('recipe_reports.results',return_value={'results':saved,'errors':[]}),patch('recipe_reports.show_result',return_value=raw) as read:
            _,listing=await self.get(app,'/api/v1/workspace/logs');read.assert_not_called()
            self.assertEqual(listing['items'][0]['summary']['incomplete_hosts'],1)
            _,detail=await self.get(app,'/api/v1/workspace/logs?item_id=run')
            self.assertEqual(read.call_count,1);self.assertTrue(detail['items'][0]['expanded'])
            self.assertEqual(detail['items'][0]['summary']['issues'][0]['stages'][0]['stage'],'advisories')
