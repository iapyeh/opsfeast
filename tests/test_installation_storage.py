"""Persistent site/identity survive disposable product checkouts."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from opsfeast import ConfigError, site
from opsfeast.identity import initialize_identity, read_identity, update_identity
from opsfeast.storage import (BINDING, MARKER, initialize_data_root,
                              bind_data_root, resolve_data_root)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.code = self.base / 'product-v1'; self.code.mkdir()
        self.data = self.base / 'installation-data'

    def test_explicit_initialize_copies_preserves_and_binds_identity(self):
        original = initialize_identity(self.code, name='Synthetic operator')
        source_identity = (self.code / '.opsfeast-instance.json').read_bytes()
        original_site = dict(site.DEFAULT,site_name='合成基地',slogan='合成測試',revision=7)
        (self.code / site.FILENAME).write_text(json.dumps(original_site))
        source_site = (self.code / site.FILENAME).read_bytes()
        self.assertEqual(initialize_data_root(self.code,self.data),self.data)
        self.assertEqual(site.read_site(self.code),original_site)
        self.assertEqual(read_identity(self.code)['id'],original['id'])
        self.assertEqual(read_identity(self.data)['id'],original['id'])
        self.assertEqual((self.code / '.opsfeast-instance.json').read_bytes(),source_identity)
        self.assertEqual((self.code / site.FILENAME).read_bytes(),source_site)
        update_identity(self.code,name='Updated through Core identity')
        self.assertEqual(read_identity(self.data)['name'],'Updated through Core identity')
        self.assertEqual((self.code / '.opsfeast-instance.json').read_bytes(),source_identity)

    def test_replace_product_without_losing_name_slogan_identity(self):
        original=initialize_identity(self.code,name='Synthetic lab')
        initialize_data_root(self.code,self.data)
        site.save_site(self.code,dict(site.DEFAULT,slogan='Keep my configuration'),expected_revision=0)
        shutil.rmtree(self.code)  # Synthetic disposable product replacement.
        fresh=self.base/'product-v2'; fresh.mkdir()
        bind_data_root(fresh,self.data)
        self.assertEqual(read_identity(fresh)['id'],original['id'])
        self.assertEqual(site.public_site(fresh)['site_name'],'Synthetic lab')
        self.assertEqual(site.read_site(fresh)['slogan'],'Keep my configuration')
        self.assertEqual(site.read_site(fresh)['revision'],1)
        self.assertFalse((fresh/site.FILENAME).exists())
        self.assertFalse((fresh/site.ASSET_DIRECTORY).exists())

    @unittest.skipUnless(importlib.util.find_spec('PIL'),'optional Pillow is absent')
    def test_images_preserved_and_published_from_new_product(self):
        from PIL import Image
        initialize_identity(self.code,name='Synthetic lab')
        # Source fixture represents the earlier prototype layout, not a supported fallback.
        buf=io.BytesIO(); Image.new('RGBA',(3,3),'green').save(buf,format='PNG')
        content=buf.getvalue(); asset_id=hashlib.sha256(content).hexdigest()+'.png'
        source_assets=self.code/site.ASSET_DIRECTORY;source_assets.mkdir()
        (source_assets/asset_id).write_bytes(content)
        (self.code/site.FILENAME).write_text(json.dumps(dict(site.DEFAULT,logo=asset_id,avatar=asset_id)))
        initialize_data_root(self.code,self.data)
        fresh=self.base/'product-v2';fresh.mkdir();bind_data_root(fresh,self.data)
        self.assertEqual(site.image_path(fresh,asset_id).read_bytes(),content)
        self.assertTrue((source_assets/asset_id).exists())
        self.assertEqual(site.read_site(fresh)['avatar'],asset_id)

    def test_reject_nonempty_existing_nested_and_invalid_destinations(self):
        existing=self.base/'existing';existing.mkdir();(existing/'keep').write_text('preserve')
        for destination in (existing,self.code/'nested',Path('relative')):
            with self.subTest(destination=destination),self.assertRaises(ConfigError):
                initialize_data_root(self.code,destination)
        self.assertEqual((existing/'keep').read_text(),'preserve')
        self.assertFalse((self.code/BINDING).exists())
        with self.assertRaises(ConfigError): bind_data_root(self.code,existing)

    def test_broken_binding_never_falls_back_to_old_product_data(self):
        initialize_identity(self.code,name='source')
        initialize_data_root(self.code,self.data)
        shutil.rmtree(self.data)
        with self.assertRaises((ConfigError,OSError)): site.read_site(self.code)
        with self.assertRaises((ConfigError,OSError)): read_identity(self.code)

    def test_unconfigured_web_storage_requires_explicit_selection(self):
        with self.assertRaises(ConfigError): resolve_data_root(self.code,required=True)
        self.assertFalse((self.code/MARKER).exists())

    def test_missing_or_corrupt_asset_prevents_binding_and_keeps_sources(self):
        asset_id='0'*64+'.png'
        (self.code/site.FILENAME).write_text(json.dumps(dict(site.DEFAULT,logo=asset_id)))
        with self.assertRaises(ConfigError):initialize_data_root(self.code,self.data)
        self.assertFalse((self.code/BINDING).exists())
        self.assertFalse(self.data.exists())
        self.assertTrue((self.code/site.FILENAME).exists())

    def test_invalid_binding_and_unmarked_site_writes_are_rejected(self):
        with self.assertRaises(ConfigError): site.save_site(self.code,dict(site.DEFAULT),expected_revision=0)
        (self.code/BINDING).write_text('{"schema_version":"0.1.0","data_root":"relative"}')
        with self.assertRaises(ConfigError):resolve_data_root(self.code,required=True)
        self.assertFalse((self.code/site.FILENAME).exists())


    def test_moved_data_identity_requires_explicit_relocation(self):
        initialize_data_root(self.code,self.data)
        moved=self.base/'moved';self.data.rename(moved)
        fresh=self.base/'product-v2';fresh.mkdir()
        with self.assertRaises(ConfigError):bind_data_root(fresh,moved)
        self.assertFalse((fresh/BINDING).exists())


if __name__=='__main__':unittest.main()
