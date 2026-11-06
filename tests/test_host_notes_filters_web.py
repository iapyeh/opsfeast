"""Authenticated structured note relations and filters, with synthetic storage."""
import json
import unittest
from urllib.parse import urlencode
import test_web_preview as fixtures
from opsfeast import Instance,admin,host_notes
from opsfeast.web.app import create_app

@unittest.skipUnless(fixtures.WEB_AVAILABLE,'optional Web dependencies not installed')
class HostNoteFilterWebTests(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.WebPreviewTests.setUp
    request=fixtures.WebPreviewTests.request
    async def test_metadata_write_exact_filters_auth_origin_and_conflict(self):
        p=Instance.open(self.root).init_profile()
        (p.root/'hosts.yaml').write_text('hosts: {sample: {connection: {local: true}}}\n')
        admin.configure(self.root,username='synthetic',password='fixture',expected_revision=0)
        app=create_app(self.root,agent_token='a'*32)
        headers=[(b'authorization',b'Bearer '+b'a'*32),(b'content-type',b'application/json')]
        path='/api/v1/host-notes?profile=main&host_id=sample'
        state=host_notes.inspect(self.root,profile='main',host_id='sample')
        body={'profile':'main','host_id':'sample','expected_revision':state['revision'],
              'changes':{'title':'Test','content':'Experience','source':'user','recipe_references':['bundle:system/check'],'tags':['LINUX','network']}}
        async def write(data,extra=()):
            return await self.request('/api/v1/host-notes','POST',body=json.dumps(data).encode(),headers=headers+list(extra),app=app)
        self.assertEqual((await self.request(path,app=app))[0],401)
        self.assertEqual((await write(body,[(b'origin',b'https://elsewhere.invalid')]))[0],403)
        status,_,raw=await write(body);self.assertEqual(status,200,raw)
        created=json.loads(raw);self.assertEqual(created['note']['source'],'agent')
        self.assertEqual(created['note']['recipe_references'],['system/check'])
        self.assertEqual((await write(body))[0],409)
        async def read(**filters):
            status,_,raw=await self.request(path+'&'+urlencode(filters,doseq=True),headers=headers,app=app)
            return status,json.loads(raw)
        self.assertEqual(len((await read(recipe_reference='bundle:system/check',tag=['LINUX','network']))[1]['notes']),1)
        self.assertEqual((await read(recipe_reference='system/check-more'))[1]['notes'],[])
        self.assertEqual((await read(recipe_reference=':system/check'))[1]['notes'],[])
        self.assertEqual((await read(recipe_reference='../bad'))[0],422)
        self.assertEqual((await read(include_general='true'))[0],422)
        body['expected_revision']=created['revision'];body['changes']['recipe_references']=None
        self.assertEqual((await write(body))[0],422)
