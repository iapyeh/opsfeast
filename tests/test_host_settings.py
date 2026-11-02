"""Synthetic local configuration tests; no real profiles or hosts are changed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from opsfeast import host_settings as service,ConfigError,read_yaml
from opsfeast.profile_settings import create,inspect
from opsfeast.site import SiteConflict
from opsfeast.storage import initialize_data_root

try:HAVE_WRITER=importlib.util.find_spec('ruamel.yaml') is not None
except ModuleNotFoundError:HAVE_WRITER=False

@unittest.skipUnless(HAVE_WRITER,'optional requirements-host-settings.txt not installed')
class HostSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name);self.code=base/'product';self.code.mkdir();self.data=base/'data'
        initialize_data_root(self.code,self.data)
        create(self.code,self.data,name='main',expected_revision=inspect(self.code)['revision'])
        self.root=self.data/'profiles/main';self.entry=self.root/'hosts.yaml'
        self.entry.write_text('''# Preserve this human note.
include: [hosts/extra.yaml]
groups:
  prod: {label: Production}
hosts:
  jump:
    connection: {hostname: jump.example.invalid, user: operator}
    group: prod
    vars: {quoted: "yes"} # Keep quotes and inline notes.
''')
        self.extra=self.root/'hosts/extra.yaml'
        self.extra.write_text('''# Included source, not the entry file.
groups:
  linux:
    hosts:
      target:
        connection:
          hostname: target.example.invalid
          user: operator
          via: {host: jump}
        users:
          operator: {password: "Synthetic-private-password"}
        recipes: {}
''')
    def state(self):return service.inspect(self.code,profile='main')
    def change(self,action,host,**kwargs):
        return service.mutate(self.code,profile='main',action=action,host_id=host,expected_revision=self.state()['revision'],**kwargs)
    def test_read_only_snapshot_and_create_with_existing_and_new_groups(self):
        before=set(self.root.iterdir());state=self.state()
        self.assertEqual(before,set(self.root.iterdir()))
        self.assertNotIn('Synthetic-private-password',json.dumps(state))
        self.assertEqual(state['hosts'][1]['reference_ips']['ipv4_addresses'],[])
        result=self.change('create','new-host',changes={'connection':{'hostname':'new.example.invalid','user':'operator'},'group':['prod','new-group'],'enabled':False})
        self.assertTrue(result['configuration_changed']);self.assertFalse(result['remote_effects'])
        self.assertTrue((self.root/'.host-settings-backups'/result['backup_id']/'original.yaml').is_file())
        self.assertIn('new-group',[item['id'] for item in self.state()['groups']])
        self.assertIn('# Preserve this human note.',self.entry.read_text())
        self.assertIn('"yes"',self.entry.read_text())
        self.assertEqual(self.extra.read_text().count('Synthetic-private-password'),1)
    def test_update_actual_included_source_preserves_secrets_and_recipe_settings(self):
        original=self.entry.read_bytes()
        result=self.change('update','target',changes={'group':['prod','new-group'],'connection':{'port':2222}})
        self.assertEqual(self.entry.read_bytes(),original)
        raw=read_yaml(self.extra)['groups']['linux']['hosts']['target']
        self.assertEqual(raw['users']['operator']['password'],'Synthetic-private-password')
        self.assertEqual(raw['recipes'],{})
        self.assertEqual(raw['connection']['via'],{'host':'jump'})
        target=next(row for row in self.state()['hosts'] if row['host_id']=='target')
        self.assertEqual(target['groups'],['linux','prod','new-group'])
        self.assertEqual(result['source'],'hosts/extra.yaml')
        self.assertIn('# Included source',self.extra.read_text())
        self.change('update','target',changes={'connection':{'via':None,'user':None}})
        connection=read_yaml(self.extra)['groups']['linux']['hosts']['target']['connection']
        self.assertNotIn('via',connection);self.assertNotIn('user',connection)
    def test_stale_revision_invalid_candidate_and_duplicate_do_not_overwrite(self):
        state=self.state();before=self.entry.read_bytes()
        with self.assertRaises(service.HostSettingsError):self.change('create','jump',changes={'connection':{'local':True}})
        with self.assertRaises(service.HostSettingsError):self.change('create','invalid',changes={'connection':{'hostname':'a','port':99999}})
        with self.assertRaises(service.HostSettingsError):self.change('update','jump',changes={'users':{'operator':{}}})
        self.assertEqual(self.entry.read_bytes(),before)
        self.entry.write_bytes(before+b'\n# External edit\n')
        with self.assertRaises(SiteConflict):service.mutate(self.code,profile='main',action='delete',host_id='target',expected_revision=state['revision'],confirmation='target')
        self.assertIn('target',read_yaml(self.extra)['groups']['linux']['hosts'])
    def test_delete_requires_confirmation_rejects_jump_dependency_and_preserves_history(self):
        original=self.extra.read_bytes()
        with self.assertRaisesRegex(service.HostSettingsError,'host_confirmation_required'):self.change('delete','target',confirmation='wrong')
        with self.assertRaisesRegex(service.HostSettingsError,'host_is_jump_dependency'):self.change('delete','jump',confirmation='jump')
        self.assertEqual(self.extra.read_bytes(),original)
        (self.root/'retention/keep.txt').write_text('historical evidence')
        result=self.change('delete','target',confirmation='target')
        self.assertNotIn('target',[row['host_id'] for row in self.state()['hosts']])
        self.assertEqual((self.root/'retention/keep.txt').read_text(),'historical evidence')
        self.assertEqual((self.root/'.host-settings-backups'/result['backup_id']/'original.yaml').read_bytes(),original)
    def test_proxy_values_are_not_returned_and_alias_sources_are_not_modified(self):
        self.extra.write_text('hosts: {}\n')
        self.entry.write_text('''hosts:
  a:
    connection: &shared {hostname: a.example.invalid, proxy_command: "proxy --header Synthetic-secret"}
  b:
    connection: *shared
''')
        before=self.entry.read_bytes();state=self.state()
        self.assertNotIn('Synthetic-secret',json.dumps(state))
        with self.assertRaisesRegex(service.HostSettingsError,'yaml_alias_edit_unsupported'):self.change('update','a',changes={'group':['prod']})
        self.assertEqual(self.entry.read_bytes(),before)

    def test_json_cli_uses_same_revisions_and_confirmation(self):
        import subprocess,sys
        prefix=[sys.executable,'-B','-m','opsfeast.host_settings','--installation',str(self.code),'--profile','main']
        result=subprocess.run(prefix+['list'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        revision=json.loads(result.stdout)['revision']
        result=subprocess.run(prefix+['create','cli-test','--expected-revision',revision],input=json.dumps({'connection':{'local':True},'group':['prod']}),capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads(result.stdout)
        result=subprocess.run(prefix+['delete','cli-test','--expected-revision',receipt['revision'],'--confirm-host','wrong'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads(result.stdout)['error'],'host_confirmation_required')
        result=subprocess.run(prefix+['delete','cli-test','--expected-revision',receipt['revision'],'--confirm-host','cli-test'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('cli-test',[row['host_id'] for row in self.state()['hosts']])

if __name__=='__main__':unittest.main()
