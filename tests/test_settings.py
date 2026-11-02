"""Settings discovery and CLI share the site service without operational effects."""
import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from opsfeast import site
from opsfeast.settings import catalog, update_site


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')

    def test_catalog_marks_unsupported_config_writes_as_planned(self):
        value=catalog()
        self.assertEqual([x['id'] for x in value['categories']],['site','profiles','hosts','recipes','parameters','retention'])
        self.assertEqual([x['id'] for x in value['categories'] if x['status']=='available'],['site','profiles','hosts'])
        for category in value['categories'][3:]:
            self.assertEqual(category['apis'],[])
            self.assertEqual(category['cli'],[])
            self.assertEqual(category['scope'],'profile')
        value['categories'][0]['status']='corrupted'
        self.assertEqual(catalog()['categories'][0]['status'],'available')

    def test_updates_preserve_other_fields_and_reject_stale_revision(self):
        value=update_site(self.root,expected_revision=0,changes={'site_name':'Synthetic site','slogan':'Keep'})
        next_value=update_site(self.root,expected_revision=value['revision'],changes={'site_name':None,'avatar':None})
        self.assertEqual(next_value['slogan'],'Keep')
        with self.assertRaises(site.SiteConflict):update_site(self.root,expected_revision=0,changes={'slogan':'overwrite'})
        self.assertEqual(site.read_site(self.root)['slogan'],'Keep')

    def test_cli_discovery_and_site_update(self):
        run=lambda *args:subprocess.run([sys.executable,'-B','-m','opsfeast.settings',*args],capture_output=True,text=True)
        result=run('catalog');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),catalog())
        result=run('site','show','--data-root',str(self.root));self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['revision'],0)
        result=run('site','update','--data-root',str(self.root),'--expected-revision','0','--name','Synthetic site','--slogan','Keep','--default-logo','--default-avatar')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(site.read_site(self.root)['site_name'],'Synthetic site')
        result=run('site','update','--data-root',str(self.root),'--expected-revision','0','--name','Stale')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(site.read_site(self.root)['site_name'],'Synthetic site')

    @unittest.skipUnless(importlib.util.find_spec('PIL'),'optional Pillow is absent')
    def test_cli_image_upload_uses_normalized_persistent_assets(self):
        from PIL import Image
        image=self.root/'synthetic-avatar.png'
        Image.new('RGB',(3,3),'green').save(image,format='PNG')
        result=subprocess.run([sys.executable,'-B','-m','opsfeast.settings','site','update',
                               '--data-root',str(self.root),'--expected-revision','0','--avatar',str(image)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertTrue(site.image_path(self.root,value['avatar']).is_file())
        self.assertEqual(value['revision'],1)


    def test_invalid_changes_and_conflicting_images_leave_settings_unchanged(self):
        from opsfeast import ConfigError
        for changes,images in [({'scope':'root'},{}),({'site_name':'x\ny'},{}),({'logo':None},{'logo':b'bad'})]:
            with self.assertRaises(ConfigError):update_site(self.root,expected_revision=0,changes=changes,images=images)
        self.assertEqual(site.read_site(self.root),site.DEFAULT)


if __name__=='__main__':unittest.main()
