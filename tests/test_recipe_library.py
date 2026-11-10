"""Recipe pages, real option overrides and Profile-local category/meal CRUD."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from opsfeast import Instance,ConfigError,read_yaml,REPOSITORY_RECIPES
from opsfeast import menu_preferences as preferences,recipe_defaults as defaults,recipe_detail
from opsfeast.site import SiteConflict


class RecipeLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.product=Path(self.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()):self.profile=Instance.open(self.product).init_profile()
        self.root=self.profile.root
        (self.root/'hosts').mkdir(exist_ok=True)
        self.entry=self.root/'hosts.yaml'
        self.entry.write_text('''# Keep this human note.
include: [hosts/extra.yaml]
default:
  recipes:
    bundle:system/network/check/port:
      enabled: true
      vars: {port: 80}
groups:
  web:
    recipes:
      system/network/check/port: {vars: {port: 8080}}
    hosts:
      node:
        connection: {local: true}
        users:
          operator: {password: "SYNTHETIC_PRIVATE_NEVER_EDIT"}
''')
        (self.root/'hosts/extra.yaml').write_text('hosts: {other: {connection: {local: true}}}\n')
        directory=self.root/'recipes/system/network/check/local-port'
        shutil.copytree(REPOSITORY_RECIPES/'system/network/check/port',directory)
        p=directory/'recipe.yaml';p.write_text(p.read_text().replace('author: {name: Bundle, contacts: [Bundle]}','author: {name: Synthetic owner, contacts: [synthetic@example.invalid]}').replace('id: check-port','id: test-local-port'))
        self.reference=':system/network/check/local-port'
        self.profile.reload()

    def change(self,action,changes,revision=None):
        return preferences.mutate(self.product,profile='main',expected_revision=revision or preferences.inspect(self.profile)['revision'],action=action,changes=changes)

    def test_preferences_reads_are_no_write_and_categories_are_editable_for_users_only(self):
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('subprocess.Popen',side_effect=AssertionError('no execution')):
            state=preferences.inspect(self.profile)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        state=self.change('category.create',{'title':'自訂監控','description':'Synthetic scope'})
        category=state['categories'][0]
        state=self.change('recipe.categories',{'reference':self.reference,'categories':['network',category['id']]})
        from opsfeast.recipe_menu import menu
        card=next(i for i in menu(self.profile)['items'] if i['reference']==self.reference)
        self.assertEqual(card['category_ids'],['network',category['id']])
        self.change('category.update',{**category,'title':'自訂監控新版'})
        self.assertEqual(preferences.inspect(self.profile)['categories'][0]['id'],category['id'])
        self.change('recipe.categories',{'reference':self.reference,'categories':[]})
        self.assertEqual(preferences.inspect(self.profile)['assignments'][self.reference],[])
        self.change('recipe.categories',{'reference':self.reference,'categories':None})
        self.assertNotIn(self.reference,preferences.inspect(self.profile)['assignments'])
        with self.assertRaises(preferences.MenuError):self.change('recipe.categories',{'reference':'system/network/check/port','categories':['hardware']})
        with self.assertRaises(preferences.MenuError):self.change('category.create',{'title':'硬體與環境','description':''})

    def test_user_meals_save_exact_plate_edit_delete_and_do_not_schedule(self):
        snapshot={'title':'我的檢查套餐','description':'Synthetic only','recipes':[self.reference,'system/account/inventory/local-users'],'hosts':['node','other']}
        before_hosts=self.entry.read_bytes()
        state=self.change('set.create',snapshot);saved=state['sets'][0]
        reloaded=preferences.inspect(Instance.open(self.product).profile('main'))
        self.assertEqual(reloaded['sets'][0]['hosts'],['node','other'])
        state=self.change('set.update',{**saved,'title':'修改後套餐','hosts':['other'],'recipes':[self.reference]})
        self.assertEqual(state['sets'][0]['hosts'],['other'])
        self.change('set.delete',{'id':saved['id']})
        self.assertFalse(preferences.inspect(self.profile)['sets'])
        self.assertEqual(before_hosts,self.entry.read_bytes())
        self.assertFalse((self.root/'inventory.yaml').exists())
        self.assertTrue(list((self.root/'.recipe-menu-backups').glob('*.json')))

    def test_user_meal_roundtrips_validated_inventory_scopes_and_rejects_unknown_fields(self):
        reference='system/inventory/hardware-sensors'
        meal={'title':'Fan only','description':'Synthetic','recipes':[reference],'hosts':['node'],'selections':{reference:{'properties':['sensors.fans']}}}
        state=self.change('set.create',meal)
        saved=state['sets'][0]
        self.assertEqual(preferences.inspect(self.profile)['sets'][0]['selections'],meal['selections'])
        for selection in ({'properties':[]},{'properties':['sensors.absent']},{'jobs':['missing']},{'properties':['system.hostname']}):
            with self.assertRaises(ConfigError):self.change('set.update',{**saved,'selections':{reference:selection}})
        self.assertEqual(preferences.inspect(self.profile)['sets'][0]['selections'],meal['selections'])
        self.change('set.update',{**saved,'selections':{reference:{'properties':['sensors.temperatures']}}})
        self.assertEqual(preferences.inspect(self.profile)['sets'][0]['selections'][reference]['properties'],['sensors.temperatures'])
        self.assertFalse((self.root/'inventory.yaml').exists())

    def test_stale_revision_malformed_assignments_and_unknown_meal_targets_fail_closed(self):
        old=preferences.inspect(self.profile)['revision']
        self.change('category.create',{'title':'A','description':''})
        with self.assertRaises(SiteConflict):self.change('category.create',{'title':'B','description':''},old)
        for changes in ({'reference':self.reference,'categories':['absent']},{'reference':self.reference,'categories':['network','network']}):
            with self.assertRaises(ConfigError):self.change('recipe.categories',changes)
        for changes in ({'title':'Bad','description':'','recipes':[self.reference],'hosts':['absent']},{'title':'Bad','description':'','recipes':[':missing'],'hosts':[]}):
            with self.assertRaises(ConfigError):self.change('set.create',changes)
        self.assertEqual(len(preferences.inspect(self.profile)['categories']),1)

    def test_options_write_real_defaults_preserve_notes_credentials_alias_and_host_precedence(self):
        reference='system/network/check/port'
        state=defaults.inspect(self.product,profile='main',reference=reference)
        after=defaults.update(self.product,profile='main',reference=reference,expected_revision=state['revision'],changes={'port':443},remove=[])
        document=read_yaml(self.entry)
        self.assertEqual(document['default']['recipes']['bundle:'+reference]['vars']['port'],443)
        self.assertTrue(document['default']['recipes']['bundle:'+reference]['enabled'])
        self.assertIn('# Keep this human note.',self.entry.read_text())
        self.assertIn('"SYNTHETIC_PRIVATE_NEVER_EDIT"',self.entry.read_text())
        self.assertNotIn('SYNTHETIC_PRIVATE_NEVER_EDIT',json.dumps(after))
        from recipe_runner import preflight
        config,*_=preflight(self.root,'node',reference)
        self.assertEqual(config.execution_recipe['effective_vars']['port'],8080)
        config,*_=preflight(self.root,'other',reference)
        self.assertEqual(config.execution_recipe['effective_vars']['port'],443)
        self.assertTrue(list((self.root/'.recipe-default-backups').glob('*.yaml')))
        with self.assertRaises(SiteConflict):defaults.update(self.product,profile='main',reference=reference,expected_revision=state['revision'],changes={'port':80},remove=[])
        before=self.entry.read_bytes()
        with self.assertRaises(ConfigError):defaults.update(self.product,profile='main',reference=reference,expected_revision=after['revision'],changes={'port':'bad'},remove=[])
        self.assertEqual(before,self.entry.read_bytes())

    def test_defaults_do_not_rewrite_bundle_and_reject_new_nested_secrets(self):
        reference='system/account/inventory/local-users';descriptor=REPOSITORY_RECIPES/reference/'recipe.yaml';original=descriptor.read_bytes()
        state=defaults.inspect(self.product,profile='main',reference=reference)
        state=defaults.update(self.product,profile='main',reference=reference,expected_revision=state['revision'],changes={'max_items':321},remove=[])
        state=defaults.update(self.product,profile='main',reference=reference,expected_revision=state['revision'],changes={},remove=['max_items'])
        self.assertFalse(next(v for v in state['variables'] if v['name']=='max_items')['configured'])
        self.assertEqual(descriptor.read_bytes(),original)
        reference='database/mysql/check/replication';state=defaults.inspect(self.product,profile='main',reference=reference)
        before=self.entry.read_bytes()
        with self.assertRaises(ConfigError):defaults.update(self.product,profile='main',reference=reference,expected_revision=state['revision'],changes={'instances':[{'password':'NEVER_PUT_IN_WEB'}]},remove=[])
        self.assertEqual(before,self.entry.read_bytes())

    def test_detail_reads_declared_and_actual_retention_with_exact_reference_and_no_execution(self):
        from test_linux_profile import files,probe,Actor,Result
        import recipe_runner
        target=self.product/'synthetic-target';target.mkdir();files(target)
        class SavedActor(Actor):
            def exec_command(actor,argv,**kwargs):
                if argv[:3]==['python3','-B','-']:return Result(json.dumps(probe.snapshot(argv[3],1000,5,root=target)),'',0)
                return super().exec_command(argv,**kwargs)
        reference='system/account/inventory/local-users'
        report,_=recipe_runner.run(self.root,'node',recipe=reference,session_class=SavedActor,runtime={'verification':'synthetic-only'})
        self.assertEqual(report['retention']['status'],'stored')
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('subprocess.Popen',side_effect=AssertionError('detail must not collect')):
            detail=recipe_detail.inspect(self.product,profile='main',reference=reference)
            self.assertTrue(detail['declarations']['retention'])
            self.assertEqual(detail['saved']['total'],1)
            row=detail['saved']['items'][0]
            self.assertIn('users',row['data_preview'])
            content=recipe_detail.record(self.product,profile='main',reference=reference,record_id=row['record_id'])
            self.assertEqual(json.loads(content)['recipe_reference'],reference)
            with self.assertRaises(ConfigError):recipe_detail.record(self.product,profile='main',reference='system/network/check/port',record_id=row['record_id'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertNotIn('SYNTHETIC_HASH_NEVER_EMIT',json.dumps(detail))

    def test_preferences_symlink_and_corrupt_state_are_not_overwritten(self):
        path=self.root/preferences.FILENAME
        path.symlink_to(self.entry)
        with self.assertRaises(ConfigError):preferences.inspect(self.profile)
        path.unlink();path.write_text('bad json')
        with self.assertRaises(ConfigError):preferences.inspect(self.profile)


import test_web_preview as web

@unittest.skipUnless(web.WEB_AVAILABLE,'optional Web requirements absent')
class RecipeLibraryHTTPTests(unittest.IsolatedAsyncioTestCase):
    request=web.WebPreviewTests.request
    def setUp(self):
        self.fixture=RecipeLibraryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.product
        self.data_tmp=tempfile.TemporaryDirectory();self.addCleanup(self.data_tmp.cleanup)
        self.web_data=Path(self.data_tmp.name)
        (self.web_data/".opsfeast-data.json").write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')

    async def test_auth_origin_body_revisions_crud_and_defaults(self):
        from opsfeast.web.app import create_app
        from urllib.parse import urlencode
        app=create_app(self.root,data_root=self.web_data,agent_token='l'*32)
        # The synthetic installation marker is the same read-only binding used by Web tests.
        auth=[(b'authorization',b'Bearer '+b'l'*32)];json_headers=auth+[(b'content-type',b'application/json')]
        query=urlencode({'profile':'main','reference':'system/account/inventory/local-users'})
        path='/api/v1/recipe-detail?'+query
        self.assertEqual((await self.request(path,app=app))[0],401)
        status,_,body=await self.request(path,headers=auth,app=app)
        self.assertEqual(status,200);data=json.loads(body)
        status,_,catalog=await self.request('/api/v1/recipe-menu?profile=main',headers=auth,app=app)
        self.assertEqual({h['host_id'] for h in json.loads(catalog)['hosts']},{'node','other'})
        mutation={'profile':'main','expected_revision':data['preferences']['revision'],'action':'category.create','changes':{'title':'HTTP category','description':''}}
        for headers,expected in (([(b'content-type',b'application/json')],401),(json_headers+[(b'origin',b'https://outside.invalid')],403)):
            self.assertEqual((await self.request('/api/v1/recipe-menu/preferences','POST',body=json.dumps(mutation).encode(),headers=headers,app=app))[0],expected)
        status,_,_=await self.request('/api/v1/recipe-menu/preferences','POST',body=json.dumps(mutation).encode(),headers=json_headers,app=app)
        self.assertEqual(status,200)
        self.assertEqual((await self.request('/api/v1/recipe-menu/preferences','POST',body=json.dumps(mutation).encode(),headers=json_headers,app=app))[0],409)
        update={'profile':'main','reference':'system/account/inventory/local-users','expected_revision':data['defaults']['revision'],'changes':{'max_items':123},'remove':[]}
        status,_,body=await self.request('/api/v1/recipe-detail/defaults','POST',body=json.dumps(update).encode(),headers=json_headers,app=app)
        self.assertEqual(status,200);self.assertEqual(next(v for v in json.loads(body)['variables'] if v['name']=='max_items')['value'],123)
        self.assertEqual((await self.request(path+'&limit=21',headers=auth,app=app))[0],422)
