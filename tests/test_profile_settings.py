import tempfile
from pathlib import Path
import unittest
from opsfeast import ConfigError,profile_settings
from opsfeast.storage import initialize_data_root
from opsfeast.site import SiteConflict


class ProfileSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.code=base/'product';self.code.mkdir()
        self.data=base/'data';initialize_data_root(self.code,self.data)

    def test_status_read_create_use_and_attach_without_connections(self):
        initial=set(self.code.iterdir())
        value=profile_settings.inspect(self.code)
        self.assertEqual(set(self.code.iterdir()),initial)
        self.assertIsNone(value['default_profile'])
        main=profile_settings.create(self.code,self.data,name='main',expected_revision=value['revision'])
        self.assertEqual(main['default_profile'],'main')
        other=profile_settings.create(self.code,self.data,name='secondary',namespace='synthetic',expected_revision=main['revision'])
        self.assertEqual(other['default_profile'],'main')
        self.assertTrue((self.data/'profiles'/'secondary'/'hosts.yaml').is_file())
        active=profile_settings.use(self.code,name='secondary',expected_revision=other['revision'])
        self.assertEqual(active['default_profile'],'secondary')
        self.assertFalse(active['connectivity_verified'])
        root=self.data/'profiles'/'secondary'
        raw=(root/'hosts.yaml').read_bytes()
        same=profile_settings.attach(self.code,root=str(root),name='secondary',expected_revision=active['revision'])
        self.assertEqual((root/'hosts.yaml').read_bytes(),raw)
        self.assertEqual(same['default_profile'],'secondary')

    def test_conflicts_and_existing_directories_are_not_overwritten(self):
        empty=profile_settings.inspect(self.code)
        value=profile_settings.create(self.code,self.data,name='main',expected_revision=empty['revision'])
        with self.assertRaises(SiteConflict):profile_settings.use(self.code,name='main',expected_revision=empty['revision'])
        with self.assertRaises(ConfigError):profile_settings.create(self.code,self.data,name='main',expected_revision=value['revision'])
        target=self.data/'profiles'/'occupied';target.mkdir();(target/'keep').write_text('preserve')
        with self.assertRaises(ConfigError):profile_settings.create(self.code,self.data,name='occupied',expected_revision=value['revision'])
        self.assertEqual((target/'keep').read_text(),'preserve')
        self.assertEqual(profile_settings.inspect(self.code)['default_profile'],'main')

    def test_description_create_edit_clear_and_preserve_on_attach(self):
        from opsfeast.core import Instance
        value=profile_settings.create(self.code,self.data,name='main',description='Production\n正式環境',expected_revision=profile_settings.revision(self.code))
        root=self.data/'profiles'/'main'
        files={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(value['profiles'][0]['description'],'Production\n正式環境')
        value=profile_settings.attach(self.code,root=str(root),name='main',expected_revision=value['revision'])
        self.assertEqual(value['profiles'][0]['description'],'Production\n正式環境')
        old=value['revision']
        value=profile_settings.update(self.code,name='main',description='New description',expected_revision=old)
        with self.assertRaises(SiteConflict):
            profile_settings.update(self.code,name='main',description='Lost update',expected_revision=old)
        self.assertEqual(Instance.open(self.code).profiles.list()['main']['description'],'New description')
        value=profile_settings.update(self.code,name='main',description='',expected_revision=value['revision'])
        self.assertEqual(value['profiles'][0]['description'],'')
        self.assertEqual(value['default_profile'],'main')
        self.assertEqual(files,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_invalid_description_preserves_registry_and_missing_root_is_editable(self):
        value=profile_settings.create(self.code,self.data,name='main',expected_revision=profile_settings.revision(self.code))
        pointer=self.code/'.opsfeast.yaml';before=pointer.read_bytes()
        for text in (None,12,'a'*1001,'bad\x00','bad\x7f','bad\ud800'):
            with self.subTest(text=repr(text)),self.assertRaises(ConfigError):
                profile_settings.update(self.code,name='main',description=text,expected_revision=value['revision'])
            self.assertEqual(pointer.read_bytes(),before)
        with self.assertRaises(ConfigError):
            profile_settings.update(self.code,name='absent',description='No',expected_revision=value['revision'])
        root=self.data/'profiles'/'main';root.rename(root.with_name('moved'))
        value=profile_settings.update(self.code,name='main',description='Offline archive',expected_revision=value['revision'])
        self.assertEqual(value['profiles'][0]['description'],'Offline archive')
        self.assertEqual(value['profiles'][0]['status'],'unavailable')

    def test_cli_revision_and_description_update(self):
        import contextlib,io,json
        from unittest.mock import patch
        import opsfeast
        profile_settings.create(self.code,self.data,name='main',expected_revision=profile_settings.revision(self.code))
        with patch.object(opsfeast,'REPOSITORY_ROOT',self.code):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):self.assertEqual(opsfeast.main(['profiles','show','--json']),0)
            revision=json.loads(output.getvalue())['revision']
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(opsfeast.main(['profiles','set-description','main','--description','CLI note','--expected-revision',revision,'--json']),0)
        self.assertEqual(profile_settings.inspect(self.code)['profiles'][0]['description'],'CLI note')


if __name__=='__main__':unittest.main()
