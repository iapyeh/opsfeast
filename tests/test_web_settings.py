"""Installation-data endpoints and preservation across checkout replacement."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from opsfeast import ConfigError,load_profiles,save_profiles
from opsfeast.web_settings import FILENAME,read_port,configure_port,bind_server,migrate_port
from opsfeast.storage import initialize_data_root,bind_data_root
from opsfeast.core import Instance


class WebSettingsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name).resolve();self.root=self.base/'product';self.root.mkdir()
        self.data=self.base/'installation-data';initialize_data_root(self.root,self.data)

    def test_first_allocation_is_external_reserved_and_independent(self):
        self.assertIsNone(read_port(self.root))
        a=bind_server(self.root);self.addCleanup(a.close)
        first=a.getsockname()[1]
        self.assertEqual(read_port(self.root),first)
        self.assertFalse((self.root/FILENAME).exists())
        self.assertFalse((self.root/'.opsfeast.yaml').exists())
        other=self.base/'other';other.mkdir();other_data=self.base/'other-data';initialize_data_root(other,other_data)
        b=bind_server(other);self.addCleanup(b.close)
        self.assertNotEqual(first,b.getsockname()[1])
        with self.assertRaises(OSError):bind_server(self.root)
        self.assertEqual(read_port(self.root),first)
        a.close()
        again=bind_server(self.root);self.addCleanup(again.close)
        self.assertEqual(again.getsockname()[1],first)

    def test_explicit_setting_and_profile_updates_do_not_touch_each_other(self):
        save_profiles(dict(schema_version=2,default_profile='lab',profiles={'lab':{'root':'feasts/lab'}}),self.root)
        (self.root/'feasts/lab').mkdir(parents=True)
        (self.root/'feasts/lab/hosts.yaml').write_text('hosts: {}\n')
        registry=(self.root/'.opsfeast.yaml').read_bytes()
        configure_port(self.root,18741)
        self.assertEqual((self.root/'.opsfeast.yaml').read_bytes(),registry)
        before=(self.data/FILENAME).read_bytes()
        Instance.open(self.root).profiles.use('lab')
        self.assertEqual((self.data/FILENAME).read_bytes(),before)

    def test_invalid_values_and_files_fail_without_repair(self):
        for value in (True,None,0,80,65536,'8741'):
            with self.assertRaises(ConfigError):configure_port(self.root,value)
        path=self.data/FILENAME
        for value in ({},{'schema_version':'0.1.0','port':18741},{'schema_version':'0.2.0','port':True},{'schema_version':'0.2.0','port':18741,'extra':1}):
            path.write_text(json.dumps(value));before=path.read_bytes()
            with self.assertRaises(ConfigError):read_port(self.root)
            with self.assertRaises(ConfigError):configure_port(self.root,18742)
            self.assertEqual(path.read_bytes(),before)
        path.unlink();target=self.data/'private';target.write_text('preserve');path.symlink_to(target)
        with self.assertRaises(ConfigError):read_port(self.root)
        self.assertEqual(target.read_text(),'preserve')

    def test_occupied_explicit_port_preserves_saved_port(self):
        configure_port(self.root,18741)
        other=self.base/'other';other.mkdir();data=self.base/'other-data';initialize_data_root(other,data)
        busy=bind_server(other);self.addCleanup(busy.close)
        with self.assertRaises(OSError):bind_server(self.root,busy.getsockname()[1])
        self.assertEqual(read_port(self.root),18741)

    def test_explicit_transfer_keeps_comments_profiles_and_original_backup(self):
        registry=self.root/'.opsfeast.yaml'
        registry.write_text('# Owner comment\nschema_version: 2\ndefault_profile: null\nprofiles: {} # Preserve profile metadata\nweb:\n  port: 18741\n')
        before=registry.read_bytes()
        with self.assertRaisesRegex(ConfigError,'migrate-port'):read_port(self.root)
        with self.assertRaises(ConfigError):bind_server(self.root)
        self.assertFalse((self.data/FILENAME).exists())
        result=migrate_port(self.root)
        self.assertEqual(result['port'],18741)
        self.assertEqual(Path(result['backup']).read_bytes(),before)
        self.assertIn('# Owner comment',registry.read_text())
        self.assertIn('# Preserve profile metadata',registry.read_text())
        self.assertNotIn('web',load_profiles(self.root))
        self.assertEqual(read_port(self.root),18741)
        self.assertEqual(migrate_port(self.root)['status'],'already_external')

    def test_conflicting_transfer_is_refused_without_overwrite(self):
        configure_port(self.root,18742)
        save_profiles({'schema_version':2,'default_profile':None,'profiles':{},'web':{'port':18741}},self.root)
        before={p:p.read_bytes() for p in (self.root/'.opsfeast.yaml',self.data/FILENAME)}
        with self.assertRaisesRegex(ConfigError,'conflict'):migrate_port(self.root)
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_checkout_replacement_preserves_credentials_profiles_and_menu_bytes(self):
        from opsfeast import admin,menu_preferences,execution_settings,recipe_defaults,REPOSITORY_RECIPES
        import shutil
        from opsfeast.identity import read_identity
        profile_root=self.base/'profile-data'
        with contextlib.redirect_stdout(io.StringIO()):profile=Instance.open(self.root).init_profile(root=profile_root)
        profile_name=profile.name
        reference='system/inventory/hardware'
        state=menu_preferences.inspect(profile)
        state=menu_preferences.mutate(self.root,profile=profile_name,expected_revision=state['revision'],action='category.create',changes={'title':'Synthetic category','description':'Keep unchanged'})
        custom=profile.root/'recipes/system/network/check/local'
        shutil.copytree(REPOSITORY_RECIPES/'system/network/check/port',custom)
        descriptor=custom/'recipe.yaml'
        descriptor.write_text(descriptor.read_text().replace('id: check-port','id: synthetic-local').replace('author: {name: Bundle, contacts: [Bundle]}','author: {name: Synthetic, contacts: [synthetic@example.invalid]}'))
        user_reference=':system/network/check/local'
        state=menu_preferences.mutate(self.root,profile=profile_name,expected_revision=state['revision'],action='recipe.categories',changes={'reference':user_reference,'categories':[state['categories'][0]['id']]})
        defaults=recipe_defaults.inspect(self.root,profile=profile_name,reference='system/account/inventory/local-users')
        recipe_defaults.update(self.root,profile=profile_name,reference='system/account/inventory/local-users',expected_revision=defaults['revision'],changes={'max_items':808},remove=[])
        menu_preferences.mutate(self.root,profile=profile_name,expected_revision=state['revision'],action='set.create',changes={'title':'Synthetic meal','description':'Keep unchanged','recipes':[reference,user_reference],'meals':['bundle:inventory-overview'],'selections':{reference:{'properties':['hardware.vendor']}}})
        admin.configure(self.data,username='owner',password='synthetic password',expected_revision=0)
        execution_settings.save(self.data,threads=3,expected_revision=execution_settings.inspect(self.data)['revision'])
        configure_port(self.root,18741)
        protected=[self.data/FILENAME,self.data/admin.FILENAME,self.data/execution_settings.FILENAME,self.data/'.opsfeast-instance.json',profile.root/'recipe-menu.json',profile.root/'hosts.yaml',profile.root/'feast.yaml',custom/'recipe.yaml',custom/'main.py']
        before={p:p.read_bytes() for p in protected}
        identity=read_identity(self.data)['id'];registry=load_profiles(self.root)
        replacement=self.base/'product-v2';replacement.mkdir()
        bind_data_root(replacement,self.data)
        save_profiles(registry,replacement)
        restored=Instance.open(replacement).profile(profile_name)
        self.assertEqual(restored.root,profile.root)
        self.assertEqual(menu_preferences.inspect(restored)['scope_id'],menu_preferences.inspect(profile)['scope_id'])
        self.assertEqual(read_port(replacement),18741)
        self.assertTrue(admin.verify(self.data,'owner','synthetic password'))
        self.assertEqual(read_identity(self.data)['id'],identity)
        self.assertEqual(menu_preferences.inspect(restored)['sets'][0]['title'],'Synthetic meal')
        self.assertEqual(before,{p:p.read_bytes() for p in protected})

    def test_existing_credentials_without_port_require_explicit_recovery(self):
        from opsfeast import admin
        admin.configure(self.data,username='owner',password='synthetic password',expected_revision=0)
        before=(self.data/admin.FILENAME).read_bytes()
        with self.assertRaisesRegex(ConfigError,'recover the original port'):bind_server(self.root)
        self.assertFalse((self.data/FILENAME).exists())
        self.assertEqual((self.data/admin.FILENAME).read_bytes(),before)
        configure_port(self.root,18741)
        self.assertEqual(read_port(self.root),18741)

    def test_explicit_data_root_selects_both_endpoint_and_credentials_location(self):
        other=self.base/'other-data';other.mkdir()
        (other/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')
        configure_port(self.root,18742,data_root=other)
        self.assertEqual(read_port(self.root,data_root=other),18742)
        self.assertIsNone(read_port(self.root))
