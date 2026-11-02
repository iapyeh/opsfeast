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


if __name__=='__main__':unittest.main()
