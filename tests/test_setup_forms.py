"""Private browser-only administrator setup grants and HTTP boundaries."""
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from opsfeast.web.setup_forms import SetupForms,InvalidSetupGrant,LIFETIME
from opsfeast import admin
from opsfeast.web.app import create_app
import test_web_preview


class SetupGrantTests(unittest.TestCase):
    def test_expiry_reissue_replay_and_browser_binding(self):
        now=[0];forms=SetupForms(clock=lambda:now[0]);old=forms.issue();token=forms.issue()
        with self.assertRaises(InvalidSetupGrant):forms.claim(old)
        browser,csrf,_=forms.claim(token)
        with self.assertRaises(InvalidSetupGrant):forms.claim(token)
        with self.assertRaises(InvalidSetupGrant):forms.complete('other',csrf,lambda:None)
        with self.assertRaises(InvalidSetupGrant):forms.complete(browser,'other',lambda:None)
        now[0]=LIFETIME
        with self.assertRaises(InvalidSetupGrant):forms.complete(browser,csrf,lambda:None)
        token=forms.issue();browser,csrf,_=forms.claim(token)
        calls=[]
        def submit():
            try:forms.complete(browser,csrf,lambda:calls.append(True));return True
            except InvalidSetupGrant:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:submit(),range(2)))
        self.assertEqual(sum(results),1);self.assertEqual(len(calls),1)

    def test_validation_failure_allows_correction_and_restart_discards_grants(self):
        forms=SetupForms();browser,csrf,_=forms.claim(forms.issue())
        with self.assertRaises(ValueError):forms.complete(browser,csrf,lambda:(_ for _ in ()).throw(ValueError()))
        forms.complete(browser,csrf,lambda:None)
        other=SetupForms()
        with self.assertRaises(InvalidSetupGrant):other.complete(browser,csrf,lambda:None)


class SetupFormHTTPTests(unittest.IsolatedAsyncioTestCase):
    setUp=test_web_preview.WebPreviewTests.setUp
    request=test_web_preview.WebPreviewTests.request

    async def call(self,app,path,body,headers=()):
        return await self.request(path,'POST',app=app,body=json.dumps(body).encode(),headers=[(b'content-type',b'application/json'),*headers])

    async def test_private_form_creates_once_without_credential_echo(self):
        app=create_app(self.root,agent_token='synthetic-owner-with-at-least-32-characters')
        owner=[(b'authorization',b'Bearer synthetic-owner-with-at-least-32-characters')]
        origin=[(b'origin',b'http://127.0.0.1')]
        path='/api/v1/agent/setup-form'
        self.assertEqual((await self.call(app,path,{}))[0],401)
        code,_,raw=await self.call(app,path,{},owner);self.assertEqual(code,200)
        issued=json.loads(raw);self.assertNotIn('synthetic-owner-with-at-least-32-characters',issued['url'])
        self.assertIn('/setup#setup-token=',issued['url'])
        token=issued['url'].split('setup-token=')[1]
        self.assertEqual((await self.call(app,'/api/v1/setup/claim',{'token':token}))[0],403)
        self.assertEqual((await self.call(app,'/api/v1/setup/claim',{'token':token},[(b'origin',b'http://evil.invalid')]))[0],403)
        code,headers,raw=await self.call(app,'/api/v1/setup/claim',{'token':token},origin)
        self.assertEqual(code,200);claim=json.loads(raw)
        cookie=headers[b'set-cookie'];self.assertIn(b'HttpOnly',cookie);self.assertIn(b'SameSite=strict',cookie)
        browser=origin+[(b'cookie',cookie.split(b';')[0])]
        self.assertEqual((await self.call(app,'/api/v1/setup/claim',{'token':token},origin))[0],401)
        payload={'username':'browser-owner','password':'synthetic-private-secret','csrf':claim['csrf']}
        self.assertEqual((await self.call(app,'/api/v1/setup/administrator',payload,origin))[0],401)
        self.assertEqual((await self.call(app,'/api/v1/setup/administrator',{**payload,'csrf':'wrong'},browser))[0],401)
        self.assertEqual((await self.call(app,'/api/v1/setup/administrator',{**payload,'username':'bad space'},browser))[0],422)
        code,_,raw=await self.call(app,'/api/v1/setup/administrator',payload,browser)
        self.assertEqual(code,200);self.assertEqual(json.loads(raw),{'configured':True})
        self.assertTrue(admin.verify(self.root,'browser-owner','synthetic-private-secret'))
        self.assertNotIn('synthetic-private-secret',(self.root/admin.FILENAME).read_text())
        self.assertEqual((await self.call(app,path,{},owner))[0],409)
        self.assertEqual((await self.call(app,'/api/v1/setup/administrator',payload,browser))[0],409)
        code,_,raw=await self.request('/api/v1/setup',app=app,headers=owner)
        self.assertTrue(json.loads(raw)['admin_configured'])
        self.assertNotIn(b'browser-owner',raw);self.assertNotIn(b'synthetic-private-secret',raw)

    async def test_reissue_and_restart_invalidate_links(self):
        app=create_app(self.root,agent_token='owner-with-at-least-32-characters');headers=[(b'authorization',b'Bearer owner-with-at-least-32-characters')]
        async def issue():return json.loads((await self.call(app,'/api/v1/agent/setup-form',{},headers))[2])['url'].split('setup-token=')[1]
        old=await issue();new=await issue();origin=[(b'origin',b'http://127.0.0.1')]
        self.assertEqual((await self.call(app,'/api/v1/setup/claim',{'token':old},origin))[0],401)
        replacement=create_app(self.root,agent_token='replacement-with-at-least-32-characters')
        self.assertEqual((await self.call(replacement,'/api/v1/setup/claim',{'token':new},origin))[0],401)
        self.assertFalse(admin.status(self.root)['configured'])
