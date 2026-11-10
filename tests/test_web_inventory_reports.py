"""Scoped inventory and report viewing through real shared services, no SSH."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opsfeast import ConfigError, Instance
from opsfeast.recipe_runs import prepare_pair
from opsfeast import report_view
import test_recipe_runs as run_fixtures
import test_web_preview as web


class InventorySelectionTests(unittest.TestCase):
    setUp = run_fixtures.RecipeRunTests.setUp
    selection = run_fixtures.RecipeRunTests.selection
    wait = run_fixtures.RecipeRunTests.wait

    def choice(self, scope=None):
        body = self.selection('system/inventory/overview')
        if scope is not None: body['recipes'][0]['inventory_selection'] = scope
        return body

    def test_catalog_defaults_and_explicit_sensor_scope_are_static_and_precise(self):
        from opsfeast.recipe_menu import menu
        with patch('subprocess.Popen', side_effect=AssertionError('no execution')):
            item = next(i for i in menu(self.profile)['items'] if i['reference']=='system/inventory/overview')
            default = self.service.preview(self.choice())['pairs'][0]['inventory_selection']
            fan_pair = self.service.preview(self.choice({'properties':['sensors.fans']}))['pairs'][0]
            fans = fan_pair['inventory_selection']
            both = self.service.preview(self.choice({'jobs':['hardware-sensors']}))['pairs'][0]['inventory_selection']
        self.assertEqual(len(item['inventory_catalog']['jobs']),11)
        self.assertEqual(len(item['inventory_catalog']['properties']),72)
        self.assertFalse(item['inventory_catalog']['jobs']['hardware-sensors']['enabled'])
        self.assertEqual(len(default['jobs']),10)
        self.assertNotIn('hardware-sensors',default['jobs'])
        self.assertEqual(fans['properties'],['sensors.fans'])
        self.assertIn('--property',fan_pair['invocation'])
        self.assertIn('sensors.fans',fan_pair['invocation'])
        self.assertNotIn('--verbose',fan_pair['invocation'])
        self.assertEqual(set(both['properties']),{'sensors.fans','sensors.temperatures'})
        self.assertFalse(self.service.directory.exists())

    def test_invalid_empty_mixed_unknown_and_cross_recipe_selection_cannot_run(self):
        for scope in ({'jobs':[]},{'properties':[]},{'jobs':['bad']},{'properties':['bad']},
                      {'jobs':['hardware-sensors'],'properties':['sensors.fans']},
                      {'properties':['sensors.fans','sensors.fans']}, {'jobs':'hardware-sensors'}):
            with self.assertRaises(ConfigError): self.service.preview(self.choice(scope))
        body=self.selection();body['recipes'][0]['inventory_selection']={'jobs':['hardware-sensors']}
        with self.assertRaises(ConfigError): self.service.preview(body)

    def test_selected_property_worker_retains_only_requested_sensor_and_no_schedule_change(self):
        import inventory_jobs
        from test_inventory_jobs import Actor, framed
        from opsfeast.recipe_run_worker import main
        class SensorActor(Actor):
            def exec_command(actor,argv,**kwargs):
                if 'fan*_input' in argv[-1]:
                    actor.commands.append(argv[-1])
                    return SimpleNamespace(stdout=framed(argv[-1],'/sys/class/hwmon/hwmon0/fan1_input 1200\n\n__OPSFEAST_EXIT_0\n'),stderr='',exitcode=0)
                return super().exec_command(argv,**kwargs)
        actor=SensorActor()
        @contextlib.contextmanager
        def connected(*args,**kwargs): yield actor
        @contextlib.contextmanager
        def selected(session,config,host,timeout,report,**kwargs):
            report.update(actual_identity={'username':'synthetic','effective_uid':1000},mode='user');yield actor
        body=self.choice({'properties':['sensors.fans']})
        pair=self.service.preview(body)['pairs'][0]
        spec={'root':str(self.profile.root),'reference':pair['reference'],'host':'node','vars':{},'inputs':[],
              'fingerprint':pair['fingerprint'],'timeout':30,'inventory_selection':body['recipes'][0]['inventory_selection']}
        output=io.StringIO()
        with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(spec).encode()))), \
             patch('opsfeast.routine_execution.connected',lambda *args:__import__('routine_transport_fixture').connection(actor,*args)), \
             patch('opsfeast.routine_execution.runtime_class',return_value=SensorActor), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(),0)
        result=json.loads(output.getvalue())
        self.assertEqual(result['retention']['status'],'stored')
        raw=json.loads(Path(result['children'][0]['result_path']).read_text())
        self.assertEqual([c['property'] for g in raw['groups'] for c in g['coverage']],['sensors.fans'])
        self.assertTrue(any('fan*_input' in command for command in actor.commands))
        self.assertFalse(any('/thermal_zone' in command or 'df -Pk' in command for command in actor.commands))
        self.assertFalse((self.profile.root/'inventory.yaml').exists())
        from opsfeast.profiling import inspect_host
        self.profile.reload()
        saved=inspect_host(self.profile,'node',domain='hardware')
        fans=next(i for i in saved['items'] if i['property_id']=='sensors.fans')
        self.assertTrue(fans['evidence'])
        spec['inventory_selection']={'properties':['sensors.temperatures']}
        with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(spec).encode()))),patch.object(inventory_jobs,'connected',side_effect=AssertionError()):
            with self.assertRaisesRegex(ConfigError,'changed'):main()


class ReportReadTests(unittest.TestCase):
    setUp=run_fixtures.RecipeRunTests.setUp
    selection=run_fixtures.RecipeRunTests.selection
    wait=run_fixtures.RecipeRunTests.wait

    def generate(self):
        plan=self.service.preview(self.selection('feast/report/retention-summary',hosts=[]))
        run=self.wait(self.service.start(plan['preview_id'],True)['id'])
        self.assertEqual(run['state'],'completed',run)
        self.identifier=run['tasks'][0]['result']['result_id']
        return report_view.show_report(self.profile,self.identifier)

    def test_saved_report_list_and_all_artifacts_share_original_integrity(self):
        report=self.generate()
        listing=report_view.list_reports(self.profile)
        self.assertEqual(listing['total'],1)
        self.assertEqual(listing['items'][0]['result_id'],self.identifier)
        before={str(p):p.read_bytes() for p in self.profile.root.rglob('*') if p.is_file()}
        for artifact in report['artifacts']:
            info,content=report_view.read_artifact(self.profile,self.identifier,artifact['path'])
            self.assertEqual(info['sha256'],hashlib.sha256(content).hexdigest())
            self.assertEqual(info['size_bytes'],len(content))
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.profile.root.rglob('*') if p.is_file()})

    def test_changed_missing_undeclared_escape_symlink_and_size_limit_are_refused(self):
        report=self.generate();name=report['artifacts'][0]['path']
        for invalid in ('../hosts.yaml','/etc/passwd','not-declared.txt'):
            with self.assertRaises(report_view.ArtifactError):report_view.read_artifact(self.profile,self.identifier,invalid)
        with patch.object(report_view,'MAX_BYTES',1):
            with self.assertRaises(report_view.ArtifactError):report_view.read_artifact(self.profile,self.identifier,name)
        path=self.profile.root/self.identifier;artifact=path.parent/'artifacts'/name
        original=artifact.read_bytes();artifact.write_bytes(b'changed')
        with self.assertRaises(report_view.ArtifactError):report_view.read_artifact(self.profile,self.identifier,name)
        artifact.unlink();artifact.symlink_to(self.profile.root/'hosts.yaml')
        with self.assertRaises(report_view.ArtifactError):report_view.read_artifact(self.profile,self.identifier,name)
        artifact.unlink()
        with self.assertRaises(report_view.ArtifactError):report_view.read_artifact(self.profile,self.identifier,name)
        with self.assertRaises(report_view.ArtifactError):report_view.show_report(self.profile,'../hosts.yaml')

    def test_static_html_keeps_tables_but_removes_active_navigation_and_urls(self):
        source=b'''<meta http-equiv="refresh" content="0;url=https://invalid.example"><base href="https://invalid.example"><script>window.parent.alert('bad')</script><iframe src="/hosts"></iframe><form action="/settings"><input></form><a href="https://invalid.example">label</a><img src="https://invalid.example/x"><style>td {color:green}</style><table><tr><td onclick="bad()">1200 RPM</td></tr></table>'''
        rendered=report_view.static_html(source)
        self.assertIn('1200 RPM',rendered);self.assertIn('<table>',rendered)
        for forbidden in ('<script','<meta http-equiv','<base','<iframe','<form','href=','onclick=','https://invalid.example'):
            self.assertNotIn(forbidden,rendered)
        with self.assertRaises(report_view.ArtifactError):report_view.static_html(b'\xff')


@unittest.skipUnless(web.WEB_AVAILABLE,'optional Web requirements absent')
class ReportHTTPTests(unittest.IsolatedAsyncioTestCase):
    setUp=web.WebPreviewTests.setUp
    request=web.WebPreviewTests.request

    async def test_authenticated_report_text_static_preview_and_attachment(self):
        from opsfeast.web.app import create_app
        from opsfeast.recipe_runs import RecipeRuns
        with contextlib.redirect_stdout(io.StringIO()):profile=Instance.open(self.root).init_profile()
        service=RecipeRuns(self.root,self.root);self.addCleanup(service.close)
        plan=service.preview({'profile':'main','hosts':[],'recipes':[{'reference':'feast/report/retention-summary','vars':{},'inputs':[]}],'timeout':30})
        run=service.start(plan['preview_id'],True);service.thread.join(10)
        identifier=service.show(run['id'],'main')['tasks'][0]['result']['result_id']
        app=create_app(self.root,agent_token='v'*32)
        auth=[(b'authorization',b'Bearer '+b'v'*32)]
        from urllib.parse import urlencode
        path='/api/v1/reports/artifact?'+urlencode({'profile':'main','result_id':identifier,'name':'retention.html'})
        for route in ('/api/v1/reports?profile=main','/api/v1/reports/result?'+urlencode({'profile':'main','result_id':identifier}),path):
            self.assertEqual((await self.request(route,app=app))[0],401)
            self.assertEqual((await self.request(route,headers=auth+[(b'origin',b'https://outside.invalid')],app=app))[0],403)
        status,headers,body=await self.request(path+'&mode=preview',headers=auth,app=app)
        self.assertEqual(status,200)
        self.assertIn(b'sandbox',headers[b'content-security-policy'])
        self.assertIn(b"default-src 'none'",headers[b'content-security-policy'])
        self.assertNotIn(b'<script',body)
        self.assertEqual((await self.request(path+'&mode=text',headers=auth,app=app))[0],200)
        status,headers,body=await self.request(path+'&mode=download',headers=auth,app=app)
        self.assertEqual(status,200);self.assertIn(b'attachment;',headers[b'content-disposition'])
        self.assertEqual((await self.request(path+'&mode=bad',headers=auth,app=app))[0],422)
        self.assertEqual((await self.request(path.replace('retention.html','../hosts.yaml'),headers=auth,app=app))[0],422)
        other=Instance.open(self.root).init_profile('other')
        self.assertEqual((await self.request(path.replace('profile=main','profile=other'),headers=auth,app=app))[0],422)
        self.assertEqual((await self.request('/api/v1/reports?profile=main&limit=101',headers=auth,app=app))[0],422)
