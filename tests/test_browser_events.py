"""Human reader readiness, private controller delivery and localhost cookie namespaces."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from urllib.parse import quote
from opsfeast import admin
from opsfeast.web.app import create_app
from opsfeast.web.browser_events import BrowserEvents
from opsfeast.web.security import cookie_names
import test_web_preview


class BrowserEventBufferTests(unittest.TestCase):
    def test_bounded_cursor_gap_and_wait_notification(self):
        broker=BrowserEvents(limit=2)
        def publish():return broker.publish(session_id='synthetic',view='live',block_id=None,seen_seq=0)
        self.assertEqual(broker.read()['events'],[])
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending=pool.submit(broker.read,0,1)
            publish();self.assertEqual(pending.result(timeout=2)['next_seq'],1)
        publish();publish()
        batch=broker.read();self.assertTrue(batch['gap'])
        self.assertEqual([e['seq'] for e in batch['events']],[2,3])
        batch['events'][0]['view']='changed'
        self.assertEqual(broker.read(1)['events'][0]['view'],'live')
        for after,wait in [(-1,0),(4,0),(True,0),(0,16),(0,-1)]:
            with self.assertRaises(ValueError):broker.read(after,wait)


class BrowserEventWebTests(unittest.IsolatedAsyncioTestCase):
    setUp=test_web_preview.WebPreviewTests.setUp
    request=test_web_preview.WebPreviewTests.request

    async def signed_in(self,root,app):
        admin.configure(root,username='synthetic',password='1',expected_revision=0)
        status,headers,_=await self.request('/api/v1/auth/login','POST',
            body=b'{"username":"synthetic","password":"1"}',headers=[(b'content-type',b'application/json')],app=app)
        self.assertEqual(status,200)
        return [(b'cookie',headers[b'set-cookie'].split(b';')[0]),(b'content-type',b'application/json')]

    async def test_next_preserves_scope_and_only_authenticated_loaded_readers_publish(self):
        owner='synthetic-owner-with-at-least-32-characters'
        app=create_app(self.root,agent_token=owner)
        sid=str(uuid.uuid4());bid=str(uuid.uuid4());records=app.state.console_records
        records.create(dict(session_id=sid,title='Synthetic',host_id='lab / guest',work_id=None))
        records.add_block(sid,dict(event_id=str(uuid.uuid4()),block_id=bid,kind='stdout',title='Observed',text='already written',form=None))
        seq=records.snapshot(sid)['seq']
        target='/console/'+sid+'?profile=lab&host_id=guest'
        status,headers,_=await self.request(target,app=app)
        self.assertEqual(status,303)
        self.assertEqual(headers[b'location'].decode(),'/login?next='+quote(target,safe=''))
        self.assertEqual(app.state.browser_events.read()['events'],[])
        endpoint='/api/v1/console-sessions/'+sid+'/reader-events'
        body=dict(view='live',block_id=None,seen_seq=seq)
        self.assertEqual((await self.request(endpoint,'POST',body=json.dumps(body).encode(),app=app))[0],401)
        owner_headers=[(b'authorization',('Bearer '+owner).encode()),(b'content-type',b'application/json')]
        self.assertEqual((await self.request(endpoint,'POST',body=json.dumps(body).encode(),headers=owner_headers,app=app))[0],403)
        human=await self.signed_in(self.root,app)
        self.assertEqual((await self.request(target,headers=human,app=app))[0],200)
        for view,block in [('live',None),('history',None),('block',bid),('history_block',bid)]:
            body.update(view=view,block_id=block)
            self.assertEqual((await self.request(endpoint,'POST',body=json.dumps(body).encode(),headers=human,app=app))[0],200)
        self.assertEqual(records.snapshot(sid)['seq'],seq)
        self.assertEqual([e['view'] for e in app.state.browser_events.read()['events']],['live','history','block','history_block'])
        self.assertEqual((await self.request('/api/v1/agent/browser-events',headers=human,app=app))[0],401)
        status,_,raw=await self.request('/api/v1/agent/browser-events',headers=owner_headers,app=app)
        self.assertEqual(status,200);self.assertEqual(len(json.loads(raw)['events']),4)
        self.assertEqual((await self.request('/api/v1/agent/browser-events?after=999',headers=owner_headers,app=app))[0],422)
        for bad in [dict(view='live',block_id=None,seen_seq=True),dict(view='live',block_id=None,seen_seq=seq+1),dict(view='live',block_id=bid,seen_seq=seq),dict(view='block',block_id='missing',seen_seq=seq)]:
            self.assertIn((await self.request(endpoint,'POST',body=json.dumps(bad).encode(),headers=human,app=app))[0],(404,422))
        self.assertEqual((await self.request(endpoint,'POST',body=json.dumps(body).encode(),headers=human+[(b'origin',b'https://elsewhere.invalid')],app=app))[0],403)
        self.assertEqual(app.state.browser_events.read()['next_seq'],4)

    async def test_cookie_names_separate_installations_and_logout_only_deletes_own_names(self):
        with tempfile.TemporaryDirectory() as directory:
            other=Path(directory);(other/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')
            a,b=create_app(self.root),create_app(other)
            ca=await self.signed_in(self.root,a);cb=await self.signed_in(other,b)
            self.assertNotEqual(ca[0][1].split(b'=')[0],cb[0][1].split(b'=')[0])
            combined=[(b'cookie',ca[0][1]+b'; '+cb[0][1])]
            for app in (a,b):
                status,_,raw=await self.request('/api/v1/auth/status',headers=combined,app=app)
                self.assertTrue(json.loads(raw)['authenticated'])
            await self.request('/api/v1/auth/logout','POST',headers=combined,app=a)
            self.assertTrue(json.loads((await self.request('/api/v1/auth/status',headers=combined,app=b))[2])['authenticated'])
            self.assertEqual(cookie_names(self.root),cookie_names(self.root/'.'))
            self.assertNotEqual(cookie_names(self.root),cookie_names(other))
