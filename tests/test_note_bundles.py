"""Synthetic host-note bundle storage, preservation and archive boundary tests."""
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from opsfeast import host_notes as notes,note_bundles as bundles
import test_host_notes


def archive(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for path,content in files.items():z.writestr(path,content)
    return out.getvalue()


class BundleTests(unittest.TestCase):
    setUp=test_host_notes.HostNotesTests.setUp
    state=test_host_notes.HostNotesTests.state
    change=test_host_notes.HostNotesTests.change
    content=test_host_notes.HostNotesTests.content
    def add(self,note=None,**kw):
        if note is None:note=self.change(changes=self.content())['note']
        scope=dict(profile='main',host_id='sample',note_uuid=note['uuid'])
        defaults=dict(expected_revision=self.state()['revision'],title='Nginx analysis',entry='report.md',files={'report.md':b'# Analysis\n\n![image](images/picture.png)','images/picture.png':b'bytes'})
        defaults.update(kw)
        if 'archive' in kw or 'source' in kw:defaults.pop('files')
        result=bundles.create(self.code,**scope,**defaults)
        return {**scope,'bundle_uuid':result['bundle']['uuid']},result

    def test_private_copy_roundtrip_revision_scope_and_update_merge_preservation(self):
        scope,created=self.add();bundle=created['bundle']
        self.assertEqual(bundle['kind'],'markdown');self.assertEqual(bundle['file_count'],2)
        path=self.root/bundles.DIRECTORY/bundle['uuid']/'files/report.md'
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.assertEqual(bundles.read_file(self.code,**scope,path='report.md'),b'# Analysis\n\n![image](images/picture.png)')
        self.assertEqual(set(bundles.unpack(bundles.export(self.code,**scope))),{'report.md','images/picture.png'})
        note=self.state()['notes'][0]
        self.change('update',note_uuid=note['uuid'],changes=self.content('Edited'))
        self.assertEqual(self.state()['notes'][0]['attachments'],[bundle])
        second=self.change(changes=self.content('Second'))['note'];other,_=self.add(second)
        self.change('merge',note_uuid=note['uuid'],remove=[second['uuid']],confirmation=[second['uuid']],changes=self.content('Merged'))
        self.assertEqual(len(self.state()['notes'][0]['attachments']),2)
        with self.assertRaisesRegex(bundles.BundleError,'bundle_not_found'):
            bundles.inspect(self.code,**{**scope,'host_id':'other','note_uuid':self.change(host='other',changes=self.content())['note']['uuid']})
        deleted=self.change('delete',note_uuid=note['uuid'],confirmation=note['uuid'])
        self.assertEqual(len(deleted['attachment_cleanup']['deleted']),2)
        self.assertFalse(path.exists())
        with self.assertRaisesRegex(bundles.BundleError,'note_not_found'):bundles.inspect(self.code,**scope)

    def test_bad_paths_duplicates_symlinks_expansion_and_missing_entry_leave_notes_unchanged(self):
        note=self.change(changes=self.content())['note'];before=(self.root/notes.FILENAME).read_bytes()
        for path in ['../escape.md','/root.md','a\\b.md','a/../b.md','a/%2e/b.md','.hidden','a//b.md','CON.txt','images/NUL','trailing.','trailing '] :
            with self.subTest(path=path),self.assertRaises(bundles.BundleError):bundles.unpack(archive({path:b'x'}))
        with self.assertRaisesRegex(bundles.BundleError,'duplicate_bundle_path'):bundles.unpack(archive({'A.md':b'a','a.md':b'b'}))
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            link=zipfile.ZipInfo('link');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(link,'/etc/passwd')
        with self.assertRaisesRegex(bundles.BundleError,'invalid_bundle_archive'):bundles.unpack(out.getvalue())
        with self.assertRaisesRegex(bundles.BundleError,'bundle_expansion_limit'):bundles.unpack(archive({'bomb.txt':b'0'*1000000}))
        with self.assertRaisesRegex(bundles.BundleError,'bundle_entry_missing'):self.add(note,entry='missing.md')
        self.assertEqual((self.root/notes.FILENAME).read_bytes(),before)
        self.assertFalse((self.root/bundles.DIRECTORY).exists())

    def test_stale_write_and_failed_commit_roll_back_new_bytes(self):
        note=self.change(changes=self.content())['note'];revision=self.state()['revision']
        self.change('update',note_uuid=note['uuid'],changes=self.content('Changed'))
        with self.assertRaisesRegex(notes.HostNotesError,'note_revision_conflict'):self.add(note,expected_revision=revision)
        with patch('opsfeast.host_notes._save',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):self.add(note)
        self.assertEqual(self.state()['notes'][0]['attachments'],[])
        self.assertEqual(list((self.root/bundles.DIRECTORY).iterdir()),[])

    def test_directory_copy_detects_tampering_and_delete_confirmation(self):
        source=self.root/'report-source';source.mkdir();(source/'index.html').write_text('<h1>HTML</h1>')
        scope,state=self.add(source=source,entry='index.html');(source/'index.html').write_text('changed')
        self.assertEqual(bundles.read_file(self.code,**scope,path='index.html'),b'<h1>HTML</h1>')
        before=self.state()['revision']
        with self.assertRaisesRegex(bundles.BundleError,'bundle_confirmation_required'):bundles.delete(self.code,**scope,expected_revision=before,confirmation='wrong')
        stored=self.root/bundles.DIRECTORY/state['bundle']['uuid']/'files/index.html';stored.write_bytes(b'tampered')
        with self.assertRaisesRegex(bundles.BundleError,'bundle_digest_mismatch'):bundles.read_file(self.code,**scope,path='index.html')
        result=bundles.delete(self.code,**scope,expected_revision=before,confirmation=scope['bundle_uuid'])
        self.assertEqual(result['cleanup']['failed'],[])
        self.assertEqual(self.state()['notes'][0]['attachments'],[])

    def test_relative_references_stay_inside_package(self):
        self.assertEqual(bundles.relative_path('reports/index.md','../images/a.png'),('images/a.png',''))
        self.assertEqual(bundles.relative_path('reports/index.md','?version=1'),('reports/index.md',''))
        for value in ['../../secret','https://example.invalid/image.png','//localhost:8741/api','file:///etc/passwd','%252e%252e/x']:
            with self.subTest(value=value),self.assertRaises(bundles.BundleError):bundles.relative_path('index.md',value)

    def test_static_hints_report_missing_external_and_malformed_references(self):
        source=b'''<script type="importmap">{"imports":{"three":"./vendor/three.mjs"}}</script><script type="module">import x from 'three';fetch('missing.json');</script><img src="https://example.invalid/image.png"><script src="http://[bad"></script>'''
        scope,state=self.add(entry='index.html',files={'index.html':source,'vendor/three.mjs':b'export default 1;'})
        reasons={warning['reason'] for warning in state['warnings']}
        self.assertIn('missing_file',reasons);self.assertIn('external_or_embedded',reasons);self.assertIn('invalid_reference',reasons)
        self.assertFalse(any(item['reference']=='three' for item in state['warnings']))

    def test_uncertain_post_commit_error_does_not_delete_linked_attachment_bytes(self):
        note=self.change(changes=self.content())['note'];original_save=notes._save
        def committed_then_failed(*args):
            original_save(*args);raise OSError('synthetic failure after commit')
        with patch('opsfeast.host_notes._save',side_effect=committed_then_failed):
            with self.assertRaises(OSError):self.add(note)
        attachment=self.state()['notes'][0]['attachments'][0]
        raw=bundles.read_file(self.code,profile='main',host_id='sample',note_uuid=note['uuid'],bundle_uuid=attachment['uuid'],path='report.md')
        self.assertIn(b'# Analysis',raw)
