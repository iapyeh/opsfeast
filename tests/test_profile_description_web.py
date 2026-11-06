"""Synthetic administrator-only Profile metadata writes; no host connections."""
import json
import unittest
from opsfeast import profile_settings
from opsfeast.web.app import create_app
import test_web_preview as fixtures

@unittest.skipUnless(fixtures.WEB_AVAILABLE, 'optional Web dependencies not installed')
class ProfileDescriptionWebTests(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.WebPreviewTests.setUp
    request=fixtures.WebPreviewTests.request

    async def test_metadata_auth_validation_revision_and_preservation(self):
        from opsfeast import Instance,admin
        Instance.open(self.root).init_profile()
        admin.configure(self.root,username='synthetic',password='fixture',expected_revision=0)
        app=create_app(self.root,agent_token='a'*32)
        headers=[(b'authorization',b'Bearer '+b'a'*32),(b'content-type',b'application/json')]
        rev=profile_settings.revision(self.root)
        body={'name':'main','description':'Web note\n第二行','expected_revision':rev}
        async def write(value,extra=(),authorized=True,path='/api/v1/profiles',method='PATCH'):
            return await self.request(path,method,body=json.dumps(value).encode(),headers=(headers if authorized else [])+list(extra),app=app)
        self.assertEqual((await write(body,authorized=False))[0],401)
        self.assertEqual((await write(body,[(b'origin',b'https://elsewhere.invalid')]))[0],403)
        self.assertEqual((await write({**body,'root':'/other'}))[0],422)
        self.assertEqual((await write({**body,'description':None}))[0],422)
        self.assertEqual((await write({**body,'expected_revision':None}))[0],409)
        self.assertEqual(profile_settings.revision(self.root),rev)
        status,_,raw=await write(body)
        self.assertEqual(status,200)
        value=json.loads(raw)
        self.assertEqual(value['profiles'][0]['description'],body['description'])
        self.assertEqual((await write(body))[0],409)
        body.update(description='',expected_revision=value['revision'])
        self.assertEqual((await write(body))[0],200)
        self.assertEqual(profile_settings.inspect(self.root)['profiles'][0]['description'],'')
        null_create={'name':'unused','namespace':None,'description':None,'expected_revision':profile_settings.revision(self.root)}
        self.assertEqual((await write(null_create,path='/api/v1/profiles',method='POST'))[0],422)
        self.assertFalse((self.root/'profiles'/'unused').exists())
