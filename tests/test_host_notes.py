"""Public synthetic notes service/CLI tests; never connect to hosts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from opsfeast import host_notes as service
from opsfeast.profile_settings import create, inspect
from opsfeast.storage import initialize_data_root


class HostNotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name);self.code=base/'product';self.code.mkdir();self.data=base/'data'
        initialize_data_root(self.code,self.data)
        create(self.code,self.data,name='main',expected_revision=inspect(self.code)['revision'])
        self.root=self.data/'profiles/main'
        (self.root/'hosts.yaml').write_text('hosts:\n  sample:\n    connection: {local: true}\n  other:\n    connection: {local: true}\n')
    def state(self,host='sample',**kw):return service.inspect(self.code,profile='main',host_id=host,**kw)
    def change(self,action='create',host='sample',**kw):
        return service.mutate(self.code,profile='main',host_id=host,action=action,expected_revision=self.state(host)['revision'],**kw)
    def content(self,title='APNIC',source='console'):return dict(title=title,content='WHOIS registry-api 經驗',source=source)
    def test_read_without_writes_latest_state_and_private_storage(self):
        before=set(self.root.iterdir());self.assertEqual(self.state()['notes'],[]);self.assertEqual(before,set(self.root.iterdir()))
        result=self.change(changes=self.content());note=result['note']
        self.assertEqual(note['source'],'console');self.assertTrue(note['timestamp'].endswith('+00:00'))
        self.assertEqual(len(note['timestamp']),25);self.assertEqual(len(note['uuid']),36)
        self.assertEqual((self.root/service.FILENAME).stat().st_mode&0o777,0o600)
        updated=self.change('update',note_uuid=note['uuid'],changes=self.content('Updated','user'))['note']
        self.assertEqual(updated['uuid'],note['uuid']);self.assertEqual(updated['source'],'user')
        self.assertEqual(len(self.state()['notes']),1);self.assertNotIn('APNIC',(self.root/service.FILENAME).read_text())
        self.assertEqual(len(self.state(query='REGISTRY')['notes']),1)
        self.assertEqual(self.state('other')['notes'],[])
    def test_conflict_no_history_and_atomic_merge_delete(self):
        first=self.change(changes=self.content())['note'];old=self.state()['revision']
        second=self.change(changes=self.content('Second'))['note']
        with self.assertRaisesRegex(service.HostNotesError,'note_revision_conflict'):
            service.mutate(self.code,profile='main',host_id='sample',action='delete',expected_revision=old,note_uuid=first['uuid'],confirmation=first['uuid'])
        with self.assertRaisesRegex(service.HostNotesError,'note_confirmation_required'):
            self.change('merge',note_uuid=first['uuid'],remove=[second['uuid']],confirmation=[],changes=self.content('Merged','agent'))
        result=self.change('merge',note_uuid=first['uuid'],remove=[second['uuid']],confirmation=[second['uuid']],changes=self.content('Merged','agent'))
        self.assertEqual(result['deleted'],[second['uuid']]);self.assertEqual(result['note']['uuid'],first['uuid'])
        self.assertEqual(len(self.state()['notes']),1)
        with self.assertRaisesRegex(service.HostNotesError,'note_confirmation_required'):
            self.change('delete',note_uuid=first['uuid'],confirmation='wrong')
        self.change('delete',note_uuid=first['uuid'],confirmation=first['uuid'])
        self.assertEqual(self.state()['notes'],[])
        self.assertNotEqual(old,self.state()['revision'])
    def test_validation_cross_host_and_missing_profile(self):
        first=self.change(changes=self.content())['note']
        with self.assertRaisesRegex(service.HostNotesError,'note_not_found'):
            self.change('update',host='other',note_uuid=first['uuid'],changes=self.content())
        for changes in [self.content(source='unknown'),dict(self.content(),uuid='chosen'),self.content(title=''),self.content(title='x\0')]:
            with self.assertRaises(service.HostNotesError):self.change(changes=changes)
        with self.assertRaises(Exception):service.inspect(self.code,profile='missing',host_id='sample')
        self.assertEqual(len(self.state()['notes']),1)
    def test_symlink_malformed_and_orphan_preserved(self):
        path=self.root/service.FILENAME;outside=self.root/'outside';outside.write_text('private')
        path.symlink_to(outside)
        with self.assertRaisesRegex(service.HostNotesError,'note_storage_invalid'):self.state()
        path.unlink();path.write_text('{broken')
        with self.assertRaisesRegex(service.HostNotesError,'note_storage_invalid'):self.state()
        path.unlink();self.change(changes=self.content())
        (self.root/'hosts.yaml').write_text('hosts: {}\n')
        state=self.state();self.assertFalse(state['host_present']);self.assertEqual(len(state['notes']),1)
        with self.assertRaisesRegex(service.HostNotesError,'host_not_found'):self.change(changes=self.content())
    def test_concurrent_writers_and_failed_cross_host_merge_preserve_content(self):
        from concurrent.futures import ThreadPoolExecutor
        revision=self.state()['revision']
        def writer(title):
            try:
                return service.mutate(self.code,profile='main',host_id='sample',action='create',expected_revision=revision,changes=self.content(title))
            except service.HostNotesError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(writer,['First','Second']))
        self.assertEqual(sum(isinstance(value,dict) for value in results),1)
        self.assertIn('note_revision_conflict',results)
        first=self.state()['notes'][0]
        other=self.change(host='other',changes=self.content())['note']
        before=(self.root/service.FILENAME).read_bytes()
        with self.assertRaisesRegex(service.HostNotesError,'note_not_found'):
            self.change('merge',note_uuid=first['uuid'],remove=[other['uuid']],confirmation=[other['uuid']],changes=self.content('Merged','agent'))
        self.assertEqual(before,(self.root/service.FILENAME).read_bytes())
        for remove in [[{}],[first['uuid'],first['uuid']],[]]:
            with self.assertRaisesRegex(service.HostNotesError,'invalid_note_merge'):
                self.change('merge',note_uuid=first['uuid'],remove=remove,confirmation=remove,changes=self.content())
        with self.assertRaisesRegex(service.HostNotesError,'invalid_note_input'):
            self.change(changes=dict(self.content(),content='x'*32001))

    def test_cli_json_stdin_and_errors(self):
        prefix=[sys.executable,'-B','-m','opsfeast.host_notes','--installation',str(self.code),'--profile','main','--host','sample']
        result=subprocess.run(prefix+['create','--expected-revision',self.state()['revision']],input=json.dumps(self.content()),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        note=json.loads(result.stdout)['note']
        result=subprocess.run(prefix+['show',note['uuid']],text=True,capture_output=True)
        self.assertEqual(json.loads(result.stdout)['notes'][0]['uuid'],note['uuid'])
        result=subprocess.run(prefix+['create','--expected-revision',self.state()['revision']],input='{bad',text=True,capture_output=True)
        self.assertEqual(result.returncode,1);self.assertEqual(json.loads(result.stdout)['error'],'note_request_failed')

    def test_recipe_and_tag_filters_canonical_scope_and_general_notes(self):
        general=self.change(changes=self.content('General'))['note']
        targeted=self.change(changes=dict(self.content('Target'),recipe_references=['bundle:system/check','system/check',':system/check','vendor:system/check'],tags=['Linux','network','LINUX']))['note']
        self.assertEqual(targeted['recipe_references'],[':system/check','system/check','vendor:system/check'])
        self.assertEqual(targeted['tags'],['linux','network'])
        other=self.change(changes=dict(self.content('Other'),recipe_references=['system/check-more'],tags=['linux']))['note']
        self.assertEqual([n['uuid'] for n in self.state(recipe_reference='bundle:system/check',tags=['LINUX','network'])['notes']],[targeted['uuid']])
        self.assertEqual({n['uuid'] for n in self.state(recipe_reference='system/check',include_general=True)['notes']},{general['uuid'],targeted['uuid']})
        self.assertEqual(self.state(recipe_reference='absent:system/check')['notes'],[])
        self.assertEqual(len(self.state(query='vendor:system/check')['notes']),1)
        self.assertEqual(self.state('other',recipe_reference='system/check')['notes'],[])
        with self.assertRaises(service.HostNotesError):self.state(include_general=True)

    def test_metadata_omission_clear_merge_and_existing_unlabelled_storage(self):
        first=self.change(changes=dict(self.content(),recipe_references=['system/check'],tags=['linux']))['note']
        updated=self.change('update',note_uuid=first['uuid'],changes=self.content('Edited'))['note']
        self.assertEqual(updated['tags'],['linux']);self.assertEqual(updated['recipe_references'],['system/check'])
        second=self.change(changes=dict(self.content('Second'),recipe_references=[':extra/check'],tags=['storage']))['note']
        merged=self.change('merge',note_uuid=first['uuid'],remove=[second['uuid']],confirmation=[second['uuid']],changes=self.content('Merged'))['note']
        self.assertEqual(merged['tags'],['linux','storage'])
        self.assertEqual(merged['recipe_references'],[':extra/check','system/check'])
        clear=self.change('update',note_uuid=first['uuid'],changes=dict(self.content(),tags=[],recipe_references=[]))['note']
        self.assertEqual(clear['tags'],[]);self.assertEqual(clear['recipe_references'],[])
        path=self.root/service.FILENAME;data=json.loads(path.read_text())
        for n in data['notes']:n.pop('tags');n.pop('recipe_references')
        path.write_text(json.dumps(data));before=path.read_bytes()
        self.assertEqual(self.state()['notes'][0]['tags'],[])
        self.assertEqual(path.read_bytes(),before)

    def test_invalid_metadata_and_filters_do_not_write(self):
        self.change(changes=self.content());before=(self.root/service.FILENAME).read_bytes()
        for key,values in [('tags',None),('tags','linux'),('tags',['']),('tags',['x'*65]),('tags',['x']*33),('tags',['bad\n']),('tags',['a,b']),('recipe_references',['../escape']),('recipe_references',['https://example.invalid/r']),('recipe_references',['system/*']),('recipe_references',[False])]:
            with self.subTest(key=key,values=values),self.assertRaises(service.HostNotesError):self.change(changes=dict(self.content(),**{key:values}))
            self.assertEqual((self.root/service.FILENAME).read_bytes(),before)
        with self.assertRaises(service.HostNotesError):self.state(recipe_reference='../escape')

    def test_cli_exact_recipe_tag_and_general_filters(self):
        self.change(changes=self.content('General'))
        note=self.change(changes=dict(self.content(),recipe_references=['system/check'],tags=['linux']))['note']
        prefix=[sys.executable,'-B','-m','opsfeast.host_notes','--installation',str(self.code),'--profile','main','--host','sample','list']
        result=subprocess.run(prefix+['--recipe','bundle:system/check','--tag','LINUX'],text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual([n['uuid'] for n in json.loads(result.stdout)['notes']],[note['uuid']])
        result=subprocess.run(prefix+['--recipe','system/check','--include-general'],text=True,capture_output=True)
        self.assertEqual(len(json.loads(result.stdout)['notes']),2)
