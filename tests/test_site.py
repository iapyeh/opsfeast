"""Installation presentation: identity independence, revision and asset evidence."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from opsfeast import ConfigError, site
from opsfeast.identity import initialize_identity, read_identity


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')

    def test_reads_do_not_initialize(self):
        self.assertEqual(site.read_site(self.root), site.DEFAULT)
        self.assertIsNone(site.public_site(self.root)['site_name'])
        self.assertEqual([p.name for p in self.root.iterdir()], ['.opsfeast-data.json'])

    def test_inherits_name_and_override_preserves_identity(self):
        initialize_identity(self.root, name='Synthetic lab')
        original = (self.root / '.opsfeast-instance.json').read_bytes()
        namespace = self.root / 'feast.yaml'
        namespace.write_text('namespace: private-test\n')
        self.assertEqual(site.public_site(self.root)['site_name'], 'Synthetic lab')
        value = dict(site.DEFAULT, site_name='合成維運基地', slogan='合成測試')
        saved = site.save_site(self.root, value, expected_revision=0)
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(site.public_site(self.root)['site_name'], '合成維運基地')
        self.assertEqual((self.root / '.opsfeast-instance.json').read_bytes(), original)
        self.assertEqual(namespace.read_text(), 'namespace: private-test\n')
        self.assertNotIn('id', site.public_site(self.root))
        self.assertNotIn('installation_path', site.public_site(self.root))
        site.save_site(self.root, dict(saved, site_name=None), expected_revision=1)
        self.assertEqual(site.public_site(self.root)['site_name'], 'Synthetic lab')

    def test_revision_conflict_does_not_overwrite(self):
        site.save_site(self.root, dict(site.DEFAULT, slogan='first'), expected_revision=0)
        with self.assertRaises(site.SiteConflict):
            site.save_site(self.root, dict(site.DEFAULT, slogan='second'), expected_revision=0)
        self.assertEqual(site.read_site(self.root)['slogan'], 'first')

    def test_reject_invalid_fields_and_missing_assets(self):
        for changes in ({'site_name':''}, {'slogan':'x\ny'}, {'revision':True}, {'logo':'../private.png'},
                        {'schema_version':'9'}, {'avatar':'0'*64+'.png'}, {'slogan':'x'*161}):
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                site.save_site(self.root, dict(site.DEFAULT, **changes), expected_revision=0)
        self.assertFalse((self.root / site.FILENAME).exists())

    def test_malformed_storage_and_symlinks_fail_without_replacement(self):
        path = self.root / site.FILENAME
        path.write_text('{"schema_version":"0.1.0","schema_version":"0.1.0"}')
        with self.assertRaises(ConfigError): site.read_site(self.root)
        path.unlink()
        target = self.root / 'private'
        target.write_text('preserve')
        path.symlink_to(target)
        with self.assertRaises(ConfigError): site.read_site(self.root)
        self.assertEqual(target.read_text(), 'preserve')

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'optional Pillow is absent')
    def test_images_normalized_metadata_removed_and_visibility_revoked(self):
        from PIL import Image, PngImagePlugin
        buf = io.BytesIO()
        metadata = PngImagePlugin.PngInfo(); metadata.add_text('private', 'synthetic secret')
        Image.new('RGBA', (1400, 800), '#88aa66').save(buf, format='PNG', pnginfo=metadata)
        asset = site.upload_image(self.root, buf.getvalue())
        self.assertEqual(asset['width'], 1024)
        with self.assertRaises(ConfigError): site.image_path(self.root, asset['asset_id'])
        saved = site.save_site(self.root, dict(site.DEFAULT, avatar=asset['asset_id']), expected_revision=0)
        path = site.image_path(self.root, asset['asset_id'])
        with Image.open(path) as image:
            self.assertEqual(image.info, {})
            self.assertEqual(image.format, 'PNG')
        site.save_site(self.root, dict(saved, avatar=None), expected_revision=1)
        with self.assertRaises(ConfigError): site.image_path(self.root, asset['asset_id'])
        self.assertTrue(path.exists(), 'clearing a reference must preserve the original image file')

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'optional Pillow is absent')
    def test_reject_fake_executable_oversized_and_symlink_assets(self):
        from PIL import Image
        for payload in (b'<svg onload="evil()"/>', b'not an image', b'x'*(site.MAX_UPLOAD+1)):
            with self.assertRaises(ConfigError): site.upload_image(self.root, payload)
        buf=io.BytesIO(); Image.new('RGB',(4097,1)).save(buf,format='PNG')
        with self.assertRaises(ConfigError): site.upload_image(self.root,buf.getvalue())
        destination = self.root / 'elsewhere'; destination.mkdir()
        (self.root / site.ASSET_DIRECTORY).symlink_to(destination)
        buf=io.BytesIO(); Image.new('RGB',(2,2)).save(buf,format='PNG')
        with self.assertRaises(ConfigError): site.upload_image(self.root,buf.getvalue())
        self.assertEqual(list(destination.iterdir()), [])


if __name__ == '__main__': unittest.main()
