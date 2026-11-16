"""Private Profile lifecycle/backup tests; all data synthetic and local."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from opsfeast import ConfigError, profile_settings as settings, profile_transfer as transfer
from opsfeast.site import SiteConflict
from opsfeast.storage import initialize_data_root


class ProfileTransferTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.base=Path(temp.name);self.product=self.base/'product';self.product.mkdir();self.data=self.base/'data'
        initialize_data_root(self.product,self.data)
        with contextlib.redirect_stdout(io.StringIO()):
            for name in ('main','lab'):
                settings.create(self.product,self.data,name=name,expected_revision=settings.revision(self.product))
        self.lab=self.data/'profiles/lab'
        (self.lab/'notes.txt').write_text('Synthetic note\n  indentation\n')
        db=sqlite3.connect(self.lab/'sample.sqlite');db.execute('create table example(value text)');db.execute("insert into example values('fixture')");db.commit();db.close()

    def export(self):return transfer.export(self.product,name='lab',expected_revision=settings.revision(self.product))

    def test_round_trip_new_name_preserves_namespace_files_and_sqlite(self):
        original=(self.lab/'feast.yaml').read_bytes();raw=self.export()
        result=transfer.import_archive(self.product,self.data,raw,name='copy',expected_revision=settings.revision(self.product))
        self.assertEqual(result['default_profile'],'main')
        copy=self.data/'profiles/copy';self.assertEqual((copy/'feast.yaml').read_bytes(),original)
        self.assertEqual((copy/'notes.txt').read_bytes(),(self.lab/'notes.txt').read_bytes())
        with sqlite3.connect(copy/'sample.sqlite') as db:self.assertEqual(db.execute('select value from example').fetchone()[0],'fixture')
        self.assertEqual(copy.stat().st_mode & 0o777,0o700)

    def test_detach_preserves_files_and_requires_current_revision(self):
        revision=settings.revision(self.product)
        result=settings.detach(self.product,name='lab',expected_revision=revision)
        self.assertEqual(result['default_profile'],'main');self.assertTrue((self.lab/'notes.txt').is_file())
        with self.assertRaises(SiteConflict):settings.detach(self.product,name='lab',expected_revision=revision)

    def test_default_detach_falls_back_to_main(self):
        settings.use(self.product,name='lab',expected_revision=settings.revision(self.product))
        result=settings.detach(self.product,name='lab',expected_revision=settings.revision(self.product))
        self.assertEqual(result['default_profile'],'main')

    def test_main_protected(self):
        for function,args in [(settings.detach,{}),(transfer.delete,{'data_root':self.data,'confirm_name':'main'})]:
            with self.assertRaises(ConfigError):function(self.product,name='main',expected_revision=settings.revision(self.product),**args)

    def test_recoverable_delete_and_reattach(self):
        result=transfer.delete(self.product,self.data,name='lab',confirm_name='lab',expected_revision=settings.revision(self.product))
        self.assertFalse(self.lab.exists());recovery=Path(result['deleted']['recovery_root'])
        self.assertEqual((recovery/'notes.txt').read_text(),'Synthetic note\n  indentation\n')
        self.assertFalse(result['deleted']['permanently_removed'])
        settings.attach(self.product,name='restored',root=str(recovery),expected_revision=result['revision'])
        self.assertTrue(any(row['name']=='restored' for row in settings.inspect(self.product)['profiles']))

    def test_delete_wrong_confirmation_default_and_registry_failure(self):
        rev=settings.revision(self.product)
        with self.assertRaises(ConfigError):transfer.delete(self.product,self.data,name='lab',confirm_name='wrong',expected_revision=rev)
        with patch.object(transfer,'save_profiles',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):transfer.delete(self.product,self.data,name='lab',confirm_name='lab',expected_revision=rev)
        self.assertTrue(self.lab.exists());self.assertEqual(settings.revision(self.product),rev)
        settings.use(self.product,name='lab',expected_revision=rev)
        with self.assertRaises(ConfigError):transfer.delete(self.product,self.data,name='lab',confirm_name='lab',expected_revision=settings.revision(self.product))

    def test_no_overwrite_or_revision_guessing(self):
        raw=self.export();rev=settings.revision(self.product)
        with self.assertRaises(ConfigError):transfer.import_archive(self.product,self.data,raw,name='lab',expected_revision=rev)
        (self.data/'profiles/occupied').mkdir()
        with self.assertRaises(ConfigError):transfer.import_archive(self.product,self.data,raw,name='occupied',expected_revision=rev)
        with self.assertRaises(SiteConflict):transfer.import_archive(self.product,self.data,raw,name='copy',expected_revision='stale')

    def test_archive_tamper_traversal_symlink_and_extra_member(self):
        good=self.export()
        for name,payload,attrs in [('profile/../escape',b'x',0),('profile/notes.txt',b'changed',0),('extra',b'x',0),('profile/link',b'target',0o120777<<16)]:
            raw=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(good)) as original,zipfile.ZipFile(raw,'w') as result:
                for member in original.infolist():
                    if member.filename!=name:result.writestr(member,original.read(member))
                member=zipfile.ZipInfo(name);member.external_attr=attrs;result.writestr(member,payload)
            with self.subTest(name=name),self.assertRaises(ConfigError):transfer.import_archive(self.product,self.data,raw.getvalue(),name='copy',expected_revision=settings.revision(self.product))
            self.assertFalse((self.data/'profiles/copy').exists())

    def test_executable_intent_and_ordinary_lock_document_preserved(self):
        script=self.lab/'recipe.sh';script.write_text('#!/bin/sh\nexit 0\n');script.chmod(0o755)
        (self.lab/'human.lock').write_text('ordinary attachment')
        raw=self.export();transfer.import_archive(self.product,self.data,raw,name='copy',expected_revision=settings.revision(self.product))
        copy=self.data/'profiles/copy';self.assertEqual((copy/'recipe.sh').stat().st_mode & 0o777,0o700)
        self.assertEqual((copy/'human.lock').read_text(),'ordinary attachment')

    def test_export_refuses_root_covering_another_profile(self):
        from opsfeast import Instance
        child=self.lab/'nested'
        with contextlib.redirect_stdout(io.StringIO()):Instance.open(self.product).init_profile('nested',root=child)
        with self.assertRaises(ConfigError):self.export()

    def test_export_rejects_symlinks_and_bounds(self):
        (self.lab/'link').symlink_to(self.lab/'notes.txt')
        with self.assertRaises(ConfigError):self.export()
        (self.lab/'link').unlink()
        with patch.object(transfer,'MAX_FILE',1),self.assertRaises(ConfigError):self.export()

    def test_external_files_are_not_embedded(self):
        external=self.base/'private-key';external.write_text('DO_NOT_EXPORT_SYNTHETIC_EXTERNAL_SECRET')
        (self.lab/'reference.txt').write_text(str(external))
        raw=self.export()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertNotIn(external.read_text(),b''.join(archive.read(member) for member in archive.namelist()).decode('utf-8',errors='ignore'))


import test_web_preview as web_fixtures
from opsfeast.web.app import create_app

@unittest.skipUnless(web_fixtures.WEB_AVAILABLE,'optional Web dependencies unavailable')
class ProfileLifecycleWebTests(unittest.IsolatedAsyncioTestCase):
    setUp=web_fixtures.WebPreviewTests.setUp
    request=web_fixtures.WebPreviewTests.request

    async def test_auth_origin_revision_export_import_and_detach(self):
        from opsfeast import Instance
        with contextlib.redirect_stdout(io.StringIO()):Instance.open(self.root).init_profile()
        app=create_app(self.root,agent_token='b'*32)
        auth=[(b'authorization',b'Bearer '+b'b'*32),(b'content-type',b'application/json')]
        body=json.dumps({'name':'main','expected_revision':settings.revision(self.root)}).encode()
        self.assertEqual((await self.request('/api/v1/profiles/export','POST',body=body,app=app))[0],401)
        self.assertEqual((await self.request('/api/v1/profiles/export','POST',body=body,headers=auth+[(b'origin',b'https://bad.invalid')],app=app))[0],403)
        status,headers,raw=await self.request('/api/v1/profiles/export','POST',body=body,headers=auth,app=app)
        self.assertEqual(status,200);self.assertEqual(headers[b'content-type'],b'application/zip');self.assertEqual(headers[b'cache-control'],b'no-store')
        query='/api/v1/profiles/import?name=copy&expected_revision='+settings.revision(self.root)
        status,_,result=await self.request(query,'POST',body=raw,headers=auth,app=app)
        self.assertEqual(status,200,result);self.assertEqual(json.loads(result)['default_profile'],'main')
        body=json.dumps({'name':'copy','expected_revision':settings.revision(self.root)}).encode()
        self.assertEqual((await self.request('/api/v1/profiles/detach','POST',body=body,headers=auth,app=app))[0],200)
        self.assertEqual((await self.request('/api/v1/profiles/detach','POST',body=body,headers=auth,app=app))[0],409)

    async def test_idle_guard_and_pinned_default_conflict(self):
        from opsfeast import Instance
        with contextlib.redirect_stdout(io.StringIO()):Instance.open(self.root).init_profile()
        app=create_app(self.root,agent_token='c'*32)
        auth=[(b'authorization',b'Bearer '+b'c'*32),(b'content-type',b'application/json')]
        self.assertEqual((await self.request('/api/v1/profiles',headers=auth+[(b'x-opsfeast-default-profile',b'other')],app=app))[0],409)
        self.assertEqual((await self.request('/api/v1/profiles',headers=auth+[(b'x-opsfeast-default-profile',b'main')],app=app))[0],200)
        app.state.recipe_runs.active='synthetic-active'
        body=json.dumps({'name':'main','expected_revision':settings.revision(self.root)}).encode()
        self.assertEqual((await self.request('/api/v1/profiles/export','POST',body=body,headers=auth,app=app))[0],409)
