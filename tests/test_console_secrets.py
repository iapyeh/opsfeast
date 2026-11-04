"""Volatile secret lifecycle, HTTP authorization and actual local program tests."""
import contextlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import threading
import time
import unittest
import uuid
from opsfeast.console_secrets import SecretBroker
from opsfeast.console_records import Records, RecordError
from opsfeast.console_agent import Worker, Publisher


def uid(): return str(uuid.uuid4())


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.broker=SecretBroker();self.addCleanup(self.broker.close)
        self.sid,self.rid=uid(),uid()
        self.created=self.broker.create(self.sid,dict(request_id=self.rid,label='Synthetic password',timeout=5))

    def test_single_use_scoped_claim_and_no_value_in_public_metadata(self):
        self.broker.submit(self.sid,self.rid,{'value':'synthetic-secret'})
        public=json.dumps(self.broker.pending(self.sid))
        self.assertNotIn('synthetic-secret',public);self.assertNotIn(self.created['claim'],public)
        for sid,claim in [(uid(),self.created['claim']),(self.sid,'wrong')]:
            with self.assertRaises(RecordError):self.broker.take(sid,self.rid,{'claim':claim})
        self.assertEqual(self.broker.take(self.sid,self.rid,{'claim':self.created['claim']})['value'],'synthetic-secret')
        with self.assertRaises(RecordError):self.broker.take(self.sid,self.rid,{'claim':self.created['claim']})
        self.assertEqual(self.broker.pending(self.sid),[])

    def test_duplicate_submit_cancel_empty_password_and_validation(self):
        for value in ['line\nbreak','a\x00b','x'*4097,12]:
            with self.assertRaises(RecordError):self.broker.submit(self.sid,self.rid,{'value':value})
        self.broker.submit(self.sid,self.rid,{'value':''})
        with self.assertRaises(RecordError):self.broker.submit(self.sid,self.rid,{'value':'new'})
        self.broker.cancel(self.sid,self.rid)
        with self.assertRaises(RecordError):self.broker.take(self.sid,self.rid,{'claim':self.created['claim']})
        self.assertIsNone(self.broker._requests[self.sid,self.rid].value)
        self.broker.cancel(self.sid,self.rid,{'claim':self.created['claim']})
        with self.assertRaises(RecordError):self.broker.create(self.sid,dict(request_id=uid(),label='x',timeout=True))

    def test_timer_erases_without_polling_and_shutdown_discards(self):
        self.broker.close()
        self.broker.create(self.sid,dict(request_id=self.rid,label='Expiry',timeout=1))
        self.broker.submit(self.sid,self.rid,{'value':'temporary'})
        end=time.monotonic()+3
        while self.broker._requests and time.monotonic()<end:time.sleep(.05)
        self.assertFalse(self.broker._requests)
        self.broker.create(self.sid,dict(request_id=uid(),label='Close',timeout=5))
        self.broker.close();self.assertFalse(self.broker._requests)

    def test_concurrent_delivery_has_one_winner(self):
        barrier=threading.Barrier(2);results=[]
        def send():
            barrier.wait()
            try:self.broker.submit(self.sid,self.rid,{'value':'one'});results.append('ok')
            except RecordError:results.append('rejected')
        threads=[threading.Thread(target=send) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertCountEqual(results,['ok','rejected'])


class SecretHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_only_submit_writer_only_take_origin_and_no_persistence(self):
        try:from opsfeast.web.app import create_app
        except ImportError:self.skipTest('optional Web dependencies absent')
        from opsfeast import admin
        from test_web_preview import WebPreviewTests
        with contextlib.ExitStack() as resources:
            tmp = resources.enter_context(tempfile.TemporaryDirectory())
            self.root=Path(tmp)
            (self.root/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')
            app=create_app(self.root,console_options={'writer_token':'writer','reader_token':'reader'})
            self.addCleanup(app.state.console_secrets.close)
            sid,rid=uid(),uid();base='/api/v1/console-sessions/'+sid
            app.state.console_records.create(dict(session_id=sid,title='Local test',host_id='synthetic',work_id=None))
            async def call(path,body=None,token=None,cookie=None,origin=None):
                headers=[(b'content-type',b'application/json')]
                if token:headers.append((b'authorization',('Bearer '+token).encode()))
                if cookie:headers.append((b'cookie',cookie))
                if origin:headers.append((b'origin',origin.encode()))
                return await WebPreviewTests.request(self,path,'POST' if body is not None else 'GET',body=json.dumps(body).encode() if body is not None else b'',headers=headers,app=app)
            admin.configure(self.root,username='test',password='Synthetic-admin-001',expected_revision=0)
            _,headers,_=await call('/api/v1/auth/login',{'username':'test','password':'Synthetic-admin-001'})
            cookie=headers[b'set-cookie'].split(b';')[0]
            request=dict(request_id=rid,label='Synthetic password',timeout=5)
            self.assertEqual((await call(base+'/secret-requests',request,token='reader'))[0],401)
            status,_,raw=await call(base+'/secret-requests',request,token='writer');self.assertEqual(status,200,raw)
            claim=json.loads(raw)['claim']
            endpoint=base+'/secret-requests/'+rid
            self.assertEqual((await call(endpoint+'/submit',{'value':'fixture-secret'},token='writer'))[0],401)
            self.assertEqual((await call(endpoint+'/submit',{'value':'fixture-secret'},cookie=cookie,origin='http://evil.invalid'))[0],403)
            self.assertEqual((await call(endpoint+'/submit',{'value':'fixture-secret'},cookie=cookie))[0],200)
            self.assertEqual((await call(endpoint+'/take',{'claim':claim},cookie=cookie))[0],401)
            self.assertEqual((await call(base+'/secret-requests',token='reader'))[0],401)
            status,_,raw=await call(base+'/secret-requests',cookie=cookie);self.assertNotIn(b'fixture-secret',raw);self.assertNotIn(claim.encode(),raw)
            before=app.state.console_records.snapshot(sid)
            status,headers,raw=await call(endpoint+'/take',{'claim':claim},token='writer')
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['value'],'fixture-secret')
            self.assertEqual(headers[b'cache-control'],b'no-store')
            self.assertEqual(app.state.console_records.snapshot(sid),before)
            for path in self.root.rglob('*'):
                if path.is_file():self.assertNotIn(b'fixture-secret',path.read_bytes(),str(path))
            self.assertEqual((await call(endpoint+'/take',{'claim':claim},token='writer'))[0],409)


class NativeProgramTests(unittest.TestCase):
    def test_actual_prompt_secret_redaction_input_and_leave(self):
        try:from sshscript import Session,Console
        except ImportError:self.skipTest('matching SSHScript required')
        from test_console_agent import StoreTransport
        broker=SecretBroker();self.addCleanup(broker.close)
        with contextlib.ExitStack() as resources:
            tmp = resources.enter_context(tempfile.TemporaryDirectory())
            records=Records(Path(tmp)/'records')
            class Transport(StoreTransport):
                def post(self,path,body):
                    parts=path.strip('/').split('/')
                    if len(parts)>1 and parts[1]=='secret-requests':
                        if len(parts)==2:return broker.create(parts[0],body)
                        if parts[-1]=='take':return broker.take(parts[0],parts[2],body)
                        return broker.cancel(parts[0],parts[2],body)
                    return super().post(path,body)
            publisher=Publisher(Transport(records),title='Native local program',host_id='synthetic')
            events=[]
            @contextlib.contextmanager
            def opener(stdout,stderr):
                with contextlib.closing(Session()) as session:
                    with Console(session,terminal=False,stdout=stdout,stderr=stderr,password_func=lambda p:worker.password(p)) as console:yield console
            worker=Worker(publisher,opener,events.append)
            resources.callback(lambda:worker.close() if not worker.closed else None)
            self.assertEqual(worker.request(dict(op='connect',request_id='connect'))['state'],'ready')
            code='import getpass,time; p=getpass.getpass("Password: "); print("echo:"+p[:3],end="",flush=True); time.sleep(.1); print(p[3:]); x=input("READY> "); print("RESULT:"+x,flush=True); input("READY> ")'
            result=worker.request(dict(op='enter',request_id='enter',command=shlex.join([sys.executable,'-u','-c',code]),prompt='READY> ',secret_prompt='Password:',exit='quit',timeout=5))
            self.assertEqual(result['state'],'waiting_secret',result)
            with self.assertRaisesRegex(Exception,'use_secret_operation'):worker.request(dict(op='input',request_id='bad',text='do not send'))
            secret='native-'+uid()
            def human():
                end=time.monotonic()+5
                while time.monotonic()<end:
                    pending=broker.pending(publisher.sid)
                    if pending:broker.submit(publisher.sid,pending[0]['request_id'],{'value':secret});return
                    time.sleep(.02)
            thread=threading.Thread(target=human);thread.start()
            result=worker.request(dict(op='secret',request_id='secret',timeout=5));thread.join(timeout=5)
            self.assertEqual(result['state'],'waiting_input',result)
            result=worker.request(dict(op='input',request_id='input',text='SELECT 1;',timeout=5))
            self.assertEqual(result['state'],'waiting_input',result)
            snapshot=records.snapshot(publisher.sid)
            text=''.join(records.content(publisher.sid,b['id'],0,16384)['text'] for b in snapshot['blocks'])
            self.assertNotIn(secret,text);self.assertIn('[hidden]',text);self.assertIn('RESULT:SELECT 1;',text)
            self.assertNotIn(secret,json.dumps(events));self.assertNotIn(secret,records.path.read_bytes().decode(errors='ignore'))
            result=worker.request(dict(op='leave',request_id='leave',timeout=5))
            self.assertEqual(result['session_state'],'ready',result)
            self.assertEqual(worker.request(dict(op='close',request_id='close'))['cleanup'],'confirmed')
