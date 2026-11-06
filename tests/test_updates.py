"""Official version metadata checks; all remote responses are synthetic."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opsfeast import ConfigError
from opsfeast.updates import check, current, CheckError, NoRedirect, release_version


class UpdateChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'VERSION').write_text('0.1.dev0')
        self.installed={'opsfeast':{'version':'0.1.dev0','commit':'a'*40,'branch':'main','local_changes':True},
                        'sshscript':{'version':'7.0.1','supported_version':'7.0.1'}}

    def ssh(self, releases):
        with patch('opsfeast.updates.current',return_value=self.installed), patch('opsfeast.updates.fetch',return_value={'releases':releases}):
            return check(self.root,'sshscript')

    def test_stable_non_yanked_pep440_releases_and_unsupported_target(self):
        data=self.ssh({'7.0.1':[{}], '7.0.2.post1':[{}], '8.0rc1':[{}], '9.0':[{'yanked':True}]})
        self.assertTrue(data['update_available'])
        self.assertEqual(data['latest']['version'],'7.0.2.post1')
        self.assertFalse(data['compatible'])
        self.assertEqual(data['update_method'],'agent_review')
        self.assertEqual(self.ssh({'7.0.1':[{}]})['comparison'],'up_to_date')
        self.assertEqual(self.ssh({'7.0.0':[{}]})['comparison'],'local_newer')
        self.assertIsNone(release_version('8.0.dev1'))

    def test_no_stable_release_invalid_local_and_missing_package(self):
        data=self.ssh({'8.0rc1':[{}]})
        self.assertEqual(data['status'],'failed');self.assertIsNone(data['update_available'])
        self.installed['sshscript']['version']=None
        self.assertEqual(self.ssh({'7.0.1':[{}]})['comparison'],'comparison_unknown')

    def test_failed_sources_and_malformed_metadata_never_claim_current(self):
        with patch('opsfeast.updates.fetch',side_effect=CheckError('source_unavailable')):
            data=check(self.root,'sshscript')
        self.assertEqual(data['status'],'failed');self.assertIsNone(data['update_available'])
        with patch('opsfeast.updates.fetch',return_value={'bad':'metadata'}):
            self.assertEqual(check(self.root,'opsfeast')['reason_code'],'invalid_source_metadata')
        with self.assertRaises(ConfigError):check(self.root,'external-url')
        with self.assertRaises(CheckError):NoRedirect().redirect_request(None,None,302,'',{},'https://foreign.invalid/')

    def test_git_relationship_and_unknown_comparison_preserve_local_changes(self):
        remote='b'*40
        for relation,expected in [('ahead','update_available'),('behind','local_newer'),('diverged','diverged')]:
            with self.subTest(relation=relation), patch('opsfeast.updates.current',return_value=self.installed), patch('opsfeast.updates.git',return_value=SimpleNamespace(returncode=1)), patch('opsfeast.updates.fetch',side_effect=[{'sha':remote},'0.2.0',{'status':relation}]) as fetch:
                data=check(self.root,'opsfeast')
                self.assertEqual(data['comparison'],expected)
                self.assertTrue(data['current']['local_changes'])
                self.assertEqual(data['latest']['commit'],remote)
                self.assertTrue(all(call.args[0].startswith(('https://api.github.com/repos/iapyeh/opsfeast/','https://raw.githubusercontent.com/iapyeh/opsfeast/')) for call in fetch.call_args_list))
        with patch('opsfeast.updates.current',return_value=self.installed), patch('opsfeast.updates.git',return_value=SimpleNamespace(returncode=0)), patch('opsfeast.updates.fetch',side_effect=[{'sha':remote},'0.1.dev0']):
            self.assertEqual(check(self.root,'opsfeast')['comparison'],'local_newer')

    def test_local_version_inspection_does_not_contact_sources_or_write(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        with patch('opsfeast.updates.fetch',side_effect=AssertionError('network')):
            data=current(self.root)
        self.assertEqual(data['opsfeast']['version'],'0.1.dev0')
        self.assertIsNone(data['opsfeast']['commit'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})


import test_workspace_web as fixtures

@unittest.skipUnless(fixtures.fixtures.WEB_AVAILABLE,'optional Web dependencies not installed')
class UpdateApiTests(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.WorkspaceWebTests.setUp
    request=fixtures.WorkspaceWebTests.request
    initialize=fixtures.WorkspaceWebTests.initialize
    get=fixtures.WorkspaceWebTests.get

    async def test_checks_require_auth_origin_and_explicit_product(self):
        _,app=self.initialize()
        self.assertEqual((await self.get(app,'/api/v1/updates',False))[0],401)
        self.assertEqual((await self.get(app,'/api/v1/updates'))[0],200)
        async def post(data,authorized=True,origin=None):
            headers=[(b'content-type',b'application/json')]
            if authorized:headers.append((b'authorization',b'Bearer '+b'a'*32))
            if origin:headers.append((b'origin',origin.encode()))
            return await self.request('/api/v1/updates/check','POST',body=json.dumps(data).encode(),headers=headers,app=app)
        with patch('opsfeast.updates.check',return_value={'status':'success','update_available':True}) as checked:
            self.assertEqual((await post({'product':'sshscript'},False))[0],401)
            self.assertEqual((await post({'product':'sshscript'},origin='https://foreign.invalid'))[0],403)
            for value in ({'product':'untrusted'},{'product':'sshscript','install':True},{'product':[]}):
                self.assertEqual((await post(value))[0],422)
            self.assertFalse(checked.called)
            self.assertEqual((await post({'product':'sshscript'}))[0],200)
            checked.assert_called_once_with(self.root.resolve(),'sshscript')
