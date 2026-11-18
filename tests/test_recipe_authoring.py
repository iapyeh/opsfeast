"""One descriptor and detail contract throughout incremental authoring."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from opsfeast import ConfigError, Instance
from opsfeast.recipe_authoring import new_definition, save, inspect
from opsfeast.site import SiteConflict


class RecipeAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.product=Path(self.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()):self.profile=Instance.open(self.product).init_profile()
        self.ref=':finance/monthly-rate'
        self.definition=new_definition(self.ref)

    def create(self):
        return save(self.profile,self.ref,expected_revision=None,definition=self.definition,summary='Initial purpose')

    def test_empty_fields_share_catalog_detail_and_inert_resource_contract(self):
        from recipe_catalog import choose,catalog
        from opsfeast.recipe_detail import inspect as detail
        from opsfeast.recipe_runs import prepare_pair,RecipeRunError
        with patch('subprocess.Popen',side_effect=AssertionError('must not execute')):
            first=self.create()
            self.assertFalse(first['runnable']);self.assertEqual(first['change_number'],1)
            self.assertIn('runner.entrypoint',first['missing_fields'])
            self.assertEqual(first['resources'],{})
            self.assertEqual({b['code'] for b in first['execution_blockers']},{'runner_contract_missing','entrypoint_missing','version_missing','output_schema_missing'})
            roles={c['id']:c for c in first['components']}
            self.assertTrue(roles['execution']['required_for_execution'])
            self.assertFalse(roles['plan']['required_for_execution'])
            self.assertEqual(roles['plan']['state'],'missing')
            item=choose(self.profile.root,self.ref)
            self.assertEqual(item['status'],'success');self.assertEqual(item['contract'],'not-configured')
            self.assertFalse(item['runnable']);self.assertEqual(catalog(self.profile.root)['status'],'success')
            with self.assertRaises(RecipeRunError):prepare_pair(self.profile.root,self.ref,'synthetic',{},[])
            data=detail(self.product,profile='main',reference=self.ref)
            self.assertEqual(data['content'],first)
            self.assertNotIn('draft',data)
            self.assertTrue({'recipe','declarations','defaults','preferences','saved','reports','attempts','content'}<=data.keys())
            updated=save(self.profile,self.ref,expected_revision=first['revision'],
                         definition={**self.definition,'description':'Purpose','resources':{'flow.plan.md':'# 01\nstop("review")'}},summary='Added purpose')
            self.assertEqual(updated['change_number'],2)
            self.assertEqual(updated['resources']['flow.plan.md'],'# 01\nstop("review")')

    def test_real_entrypoint_enables_same_recipe_without_modes_or_placeholder(self):
        first=self.create();directory=self.profile.root/'recipes/finance/monthly-rate'
        self.assertFalse(list(directory.glob('*.py')))
        definition={**self.definition,'version':'1.0.0','runner':{'contract':'python-session','version':'0.1.0','entrypoint':'main.py'},'output':{'schema_version':'1.0.0'}}
        missing=save(self.profile,self.ref,expected_revision=first['revision'],definition=definition)
        self.assertFalse(missing['runnable'])
        code='VERSION = "1.0.0"\nraise AssertionError("candidate must not be imported")\ndef execute(session, *, context, timeout):\n    raise AssertionError("must not run")\n'
        (directory/'main.py').write_text(code)
        with patch('subprocess.Popen',side_effect=AssertionError('no execution')):
            ready=inspect(self.profile,self.ref)
            self.assertTrue(ready['runnable'])
            self.assertEqual(ready['execution_blockers'],[])
            self.assertEqual(ready['revision'],missing['revision'])
            self.assertNotEqual(ready['view_revision'],missing['view_revision'])
            renamed=save(self.profile,self.ref,expected_revision=ready['revision'],definition={**ready['definition'],'title':'Monthly rate'})
        self.assertTrue(renamed['runnable']);self.assertEqual((directory/'main.py').read_text(),code)
        (directory/'main.py').write_text(code.replace('1.0.0','2.0.0'))
        self.assertFalse(inspect(self.profile,self.ref)['runnable'])

    def test_digest_conflicts_and_unauthorized_source_preserve_files(self):
        first=self.create();path=self.profile.root/'recipes/finance/monthly-rate/recipe.yaml'
        with self.assertRaises(SiteConflict):self.create()
        path.write_text(path.read_text()+'\n')
        before=path.read_bytes()
        with self.assertRaises(SiteConflict):save(self.profile,self.ref,expected_revision=first['revision'],definition=self.definition)
        self.assertEqual(path.read_bytes(),before)
        with self.assertRaises(ConfigError):save(self.profile,'system/network/check/port',expected_revision=None,definition=self.definition)

    def test_invalid_paths_resources_and_obsolete_fields_fail_without_writes(self):
        for reference in (':../escape',':finance//rate',':finance/./rate'):
            with self.subTest(reference=reference),self.assertRaises(ConfigError):save(self.profile,reference,expected_revision=None,definition=self.definition)
        for extra in ({'resources':{'../secret':'x'}},{'resources':{'x':'\x00'}},{'resources':{'x':'a'*1048576}}, {'lifecycle':'draft'}, {'draft':{}}, {'runner':None},{'resource_titles':{'missing.md':'Title'}},{'resources':{'plan.md':''},'resource_titles':{'plan.md':''}}):
            with self.subTest(extra=list(extra)),self.assertRaises(ConfigError):save(self.profile,self.ref,expected_revision=None,definition={**self.definition,**extra})
        outside=self.product/'outside';outside.mkdir()
        base=self.profile.root/'recipes';base.mkdir(exist_ok=True)
        (base/'linked').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ConfigError):save(self.profile,':linked/rate',expected_revision=None,definition=self.definition)
        self.assertEqual(list(outside.iterdir()),[])

    def test_composition_groups_named_resources_and_keeps_readiness_separate(self):
        definition={**self.definition,'version':'1.0.0','resources':{
            'flow.plan.md':'Plan','contracts/steps.md':'Steps','routines/select_quote.py':'Routine',
            'conformance/cases.json':'{}','README.md':'Guide','resources/image-notes.md':'Asset'},
            'resource_titles':{'routines/select_quote.py':'Monthly quote selection'}}
        state=save(self.profile,self.ref,expected_revision=None,definition=definition)
        roles={c['id']:c for c in state['components']}
        for key in ('plan','step_contracts','utilities','verification','guide','assets'):
            self.assertEqual(roles[key]['state'],'provided')
        self.assertEqual(roles['utilities']['resources'][0]['title'],'Monthly quote selection')
        self.assertEqual(roles['execution']['state'],'missing')
        self.assertFalse(state['runnable'])
        self.assertEqual({b['code'] for b in state['execution_blockers']},{'runner_contract_missing','entrypoint_missing','output_schema_missing'})
        directory=self.profile.root/'recipes/finance/monthly-rate'
        (directory/'contracts').mkdir();(directory/'contracts/extra.yaml').write_text('schema_version: 1\n')
        (directory/'README.md').write_text('Real guide\n')
        (directory/'contracts/private-link.yaml').symlink_to(self.product/'missing')
        after=inspect(self.profile,self.ref);roles={c['id']:c for c in after['components']}
        self.assertIn('contracts/extra.yaml',roles['step_contracts']['files'])
        self.assertNotIn('contracts/private-link.yaml',roles['step_contracts']['files'])
        # An embedded README is already represented once, rather than falsely absent or duplicated.
        self.assertNotIn('README.md',roles['guide']['files'])
        self.assertNotEqual(state['view_revision'],after['view_revision'])
        builtin=inspect(self.profile,'system/network/check/port')
        roles={c['id']:c for c in builtin['components']}
        self.assertEqual(roles['guide']['state'],'file_present')
        self.assertIn('README.md',roles['guide']['files'])
        self.assertEqual(builtin['execution_blockers'],[])
        routine=inspect(self.profile,'system/inventory/hardware')
        self.assertTrue(next(c for c in routine['components'] if c['id']=='utilities')['required_for_execution'])
        self.assertTrue(next(c for c in routine['components'] if c['id']=='permissions')['required_for_execution'])

    def test_shared_reader_supports_builtin_and_canonical_cli(self):
        self.assertTrue(inspect(self.profile,'system/network/check/port')['runnable'])
        snapshot=self.product/'snapshot.json'
        snapshot.write_text(json.dumps({'expected_revision':None,'definition':self.definition,'summary':''}))
        command=[sys.executable,'-B','-m','opsfeast.recipe_authoring','--product',str(self.product),'--profile','main','--reference',self.ref]
        created=subprocess.run(command+['--snapshot',str(snapshot)],capture_output=True,text=True)
        self.assertEqual(created.returncode,0,created.stderr)
        self.assertFalse(json.loads(created.stdout)['runnable'])
        loaded=subprocess.run(command,capture_output=True,text=True);self.assertEqual(loaded.returncode,0,loaded.stderr)
        conflict=subprocess.run(command+['--snapshot',str(snapshot)],capture_output=True,text=True)
        self.assertEqual(conflict.returncode,1)


import test_web_preview as web


@unittest.skipUnless(web.WEB_AVAILABLE,'optional Web requirements absent')
class RecipeContentHTTPTests(unittest.IsolatedAsyncioTestCase):
    request=web.WebPreviewTests.request

    async def test_uniform_detail_and_content_are_authenticated_and_current(self):
        fixture=RecipeAuthoringTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        extra=tempfile.TemporaryDirectory();self.addCleanup(extra.cleanup);data=Path(extra.name)
        (data/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')
        from opsfeast.web.app import create_app
        app=create_app(fixture.product,data_root=data,agent_token='a'*32)
        auth=[(b'authorization',b'Bearer '+b'a'*32)]
        path='/api/v1/recipe-content?profile=main&reference=%3Afinance%2Fmonthly-rate'
        self.assertEqual((await self.request(path,app=app))[0],401)
        first=fixture.create()
        status,_,body=await self.request(path,headers=auth,app=app)
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['revision'],first['revision'])
        status,_,body=await self.request(path.replace('recipe-content','recipe-detail'),headers=auth,app=app)
        self.assertEqual(status,200);self.assertIn('content',json.loads(body));self.assertNotIn('draft',json.loads(body))
        saved=save(fixture.profile,fixture.ref,expected_revision=first['revision'],definition={**fixture.definition,'inputs':{'variables':{'api_token':{'type':'string','default':'SYNTHETIC_SECRET_VALUE'}}}})
        for endpoint in (path,path.replace('recipe-content','recipe-detail')):
            status,_,body=await self.request(endpoint,headers=auth,app=app)
            self.assertEqual(status,200);self.assertNotIn(b'SYNTHETIC_SECRET_VALUE',body)
        self.assertEqual((await self.request(path.replace('%3Afinance%2Fmonthly-rate','%3A..%2Fescape'),headers=auth,app=app))[0],422)
