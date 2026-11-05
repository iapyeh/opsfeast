"""Owner capability, reset authorization, actor provenance and memory-only launch."""
import json
from pathlib import Path
import socket
from unittest.mock import Mock
import subprocess
import sys
import tempfile
import unittest
import uuid

from opsfeast import admin
from opsfeast.web.app import create_app
from opsfeast.web.security import AgentCapability
import test_web_preview


class OwnerTests(unittest.IsolatedAsyncioTestCase):
    setUp=test_web_preview.WebPreviewTests.setUp
    request=test_web_preview.WebPreviewTests.request

    def application(self, token=None):
        return create_app(self.root,agent_token=token or 'synthetic-owner-token-with-32-characters',edit_token='presentation-token')

    def headers(self, token='synthetic-owner-token-with-32-characters'):
        return [(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json')]

    async def test_only_owner_can_set_without_old_password_and_sessions_are_revoked(self):
        app=self.application()
        body=json.dumps(dict(username='synthetic',password='x',expected_revision=0)).encode()
        path='/api/v1/agent/administrator'
        for headers in [[],[(b'authorization',b'Bearer wrong')],[(b'authorization',b'Bearer presentation-token')]]:
            self.assertEqual((await self.request(path,'PUT',body=body,headers=headers,app=app))[0],401)
        status,headers,data=await self.request(path,'PUT',body=body,headers=self.headers(),app=app)
        self.assertEqual(status,200);self.assertEqual(headers[b'x-opsfeast-actor'],b'agent')
        self.assertNotIn(b'"password"',data);self.assertTrue(admin.verify(self.root,'synthetic','x'))
        login=await self.request('/api/v1/auth/login','POST',body=json.dumps(dict(username='synthetic',password='x')).encode(),headers=[(b'content-type',b'application/json')],app=app)
        cookie=login[1][b'set-cookie'].split(b';')[0]
        # A human administrator cannot call the agent-only reset endpoint.
        self.assertEqual((await self.request(path,'PUT',body=body,headers=[(b'cookie',cookie),(b'content-type',b'application/json')],app=app))[0],401)
        body=json.dumps(dict(username='synthetic',password='新',expected_revision=1)).encode()
        self.assertEqual((await self.request(path,'PUT',body=body,headers=self.headers(),app=app))[0],200)
        state=await self.request('/api/v1/auth/status',headers=[(b'cookie',cookie)],app=app)
        self.assertFalse(json.loads(state[2])['authenticated'])
        self.assertTrue(admin.verify(self.root,'synthetic','新'))
        self.assertEqual((await self.request(path,'PUT',body=body,headers=self.headers(),app=app))[0],409)
        self.assertEqual((await self.request(path,'PUT',body=body,headers=self.headers()+[(b'origin',b'https://elsewhere.invalid')],app=app))[0],403)

    async def test_owner_is_not_a_human_login_and_old_capability_fails_on_replacement(self):
        app=self.application()
        value=await self.request('/api/v1/auth/status',headers=self.headers(),app=app)
        self.assertEqual(json.loads(value[2]),dict(configured=False,authenticated=False,username=None,agent_authorized=True))
        replacement=self.application('different-owner-token-with-32-characters')
        self.assertEqual((await self.request('/api/v1/admin',headers=self.headers(),app=replacement))[0],401)
        self.assertEqual((await self.request('/api/v1/admin',headers=self.headers(),app=app))[0],200)
        capability=AgentCapability('synthetic-owner-token-with-32-characters')
        self.assertNotIn('synthetic-owner-token-with-32-characters',repr(vars(capability)))

    async def test_owner_private_input_transport_can_cancel_with_claim(self):
        app=self.application();sid=str(uuid.uuid4());rid=str(uuid.uuid4())
        app.state.console_records.create(dict(session_id=sid,title='Synthetic',host_id='fixture',work_id=None))
        base='/api/v1/console-sessions/'+sid+'/secret-requests'
        status,_,raw=await self.request(base,'POST',body=json.dumps(dict(request_id=rid,label='Synthetic secret',timeout=30)).encode(),headers=self.headers(),app=app)
        self.assertEqual(status,200);claim=json.loads(raw)['claim']
        status,_,_=await self.request(base+'/'+rid+'/cancel','POST',body=json.dumps(dict(claim=claim)).encode(),headers=self.headers(),app=app)
        self.assertEqual(status,200)
        app.state.console_secrets.close()

    async def test_owner_note_writes_use_agent_source(self):
        from opsfeast import profile_settings
        profile_settings.create(self.root,self.root,name='main',expected_revision=profile_settings.inspect(self.root)['revision'])
        (self.root/'profiles/main/hosts.yaml').write_text('hosts: {sample: {connection: {local: true}}}\n')
        app=self.application()
        status,_,raw=await self.request('/api/v1/host-notes?profile=main&host_id=sample',headers=self.headers(),app=app)
        self.assertEqual(status,200)
        body=dict(profile='main',host_id='sample',expected_revision=json.loads(raw)['revision'],changes=dict(title='Synthetic',content='Owner request',source='user'))
        status,_,raw=await self.request('/api/v1/host-notes','POST',body=json.dumps(body).encode(),headers=self.headers(),app=app)
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['note']['source'],'agent')

    async def test_owner_can_publish_and_respond_with_agent_provenance(self):
        app=self.application();sid=str(uuid.uuid4());bid=str(uuid.uuid4())
        async def call(path,body):
            status,_,data=await self.request(path,'POST',body=json.dumps(body).encode(),headers=self.headers(),app=app)
            self.assertEqual(status,200,data);return json.loads(data)
        await call('/api/v1/console-sessions',dict(session_id=sid,title='Synthetic',host_id='fixture',work_id=None))
        await call('/api/v1/console-sessions/'+sid+'/blocks',dict(event_id=str(uuid.uuid4()),block_id=bid,kind='form',title='Review',text='',form=dict(fields=[],choices=[dict(id='yes',label='Yes')],expires_at=None)))
        value=await call('/api/v1/console-sessions/'+sid+'/blocks/'+bid+'/responses',dict(event_id=str(uuid.uuid4()),revision=1,choice='yes',values={}))
        response=value['response'] if 'response' in value else app.state.console_records.snapshot(sid)['blocks'][0]['response']
        self.assertEqual(response['actor'],'agent');self.assertEqual(response['authority'],'agent_capability')


class ControllerBoundaryTests(unittest.TestCase):
    def test_invalid_target_missing_grant_and_duplicate_never_replay(self):
        from opsfeast.web.agent_control import Controller
        controller=Controller('http://127.0.0.1:8740','synthetic-owner-token-with-32-characters',lambda event:None)
        # Loopback credentials must not inherit ambient HTTP proxies.
        from urllib.request import ProxyHandler
        self.assertFalse(any(isinstance(handler,ProxyHandler) for handler in controller.http.handlers))
        controller.http=Mock()
        for path in ['https://elsewhere.invalid/api/v1/admin','//elsewhere.invalid/api/v1/admin','/login']:
            with self.assertRaises(ValueError):controller.request('GET',path)
        with self.assertRaises(ValueError):controller.dispatch(dict(op='request',request_id='missing',method='PUT',path='/api/v1/admin',body={}))
        controller.http.open.assert_not_called()
        controller.request=Mock(return_value={'status':200,'body':{}})
        body=dict(op='request',request_id='once',path='/api/v1/admin')
        controller.dispatch(body)
        with self.assertRaises(ValueError):controller.dispatch(body)
        controller.request.assert_called_once()

    def test_owner_exact_plan_actor_stays_distinct(self):
        from opsfeast.interactive import Service,InteractiveError
        with tempfile.TemporaryDirectory() as directory:
            service=Service(Path(directory)/'work',directory,targets=[('lab','sample')],connector=Mock())
            try:
                work=service.create('lab','sample','Synthetic inspection',role='agent_owner')
                self.assertEqual(service.store.events(work,0)[0]['actor'],'agent_owner')
                plan=dict(request_id='plan-0001',title='Synthetic',steps=[dict(command='true',purpose='Synthetic',checkpoint=False,timeout=1)],approval_mode='plan')
                service.action(work,'plan',plan,role='agent_owner')
                with self.assertRaises(InteractiveError):service.action(work,'reject',dict(request_id='reject-001'),role='agent')
                service.action(work,'reject',dict(request_id='reject-002'),role='agent_owner')
                self.assertEqual(service.store.events(work,0)[-1]['actor'],'agent_owner')
            finally:service.shutdown()


class MemoryLaunchTests(unittest.TestCase):
    def test_controller_keeps_capability_out_of_output_and_files_and_eof_stops_server(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            process=subprocess.Popen([sys.executable,'-B','-u','-m','opsfeast.web','--agent-control','--data-root',directory,'--port',str(port)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                ready=json.loads(process.stdout.readline());self.assertEqual(ready['type'],'ready')
                process.stdin.write(json.dumps(dict(op='admin.password',request_id='set-1',username='synthetic',password='1',authorization='Synthetic owner requested reset'))+'\n');process.stdin.flush()
                result=json.loads(process.stdout.readline());self.assertEqual(result['status'],200,result)
                self.assertNotIn('password',result['body']);self.assertTrue(admin.verify(root,'synthetic','1'))
                process.stdin.write(json.dumps(dict(op='admin.password',request_id='generate-2',generate=True,authorization='Synthetic owner requested generation'))+'\n');process.stdin.flush()
                generated=json.loads(process.stdout.readline());self.assertEqual(generated['status'],200)
                self.assertTrue(admin.verify(root,'synthetic',generated['generated_password']))
                process.stdin.write(json.dumps(dict(op='worker.start',request_id='worker-start',worker_id='local',local=True))+'\n');process.stdin.flush()
                created=False;ack=False
                while not (created and ack):
                    event=json.loads(process.stdout.readline())
                    if event.get('request_id')=='worker-start':ack=True
                    if event.get('type')=='worker_event' and event['event']['type']=='created':created=True
                process.stdin.write(json.dumps(dict(op='worker.send',request_id='worker-close',worker_id='local',control=dict(op='close',request_id='close-local')))+'\n');process.stdin.flush()
                exited=False
                while not exited:
                    event=json.loads(process.stdout.readline())
                    exited=event.get('type')=='worker_exit'
                self.assertEqual(list(root.glob('*.token')),[])
                self.assertEqual(list(root.glob('.*.token')),[])
                process.stdin.close();process.wait(timeout=15)
                self.assertEqual(process.returncode,0,process.stderr.read())
                self.assertTrue(json.loads(process.stdout.readline())['server_stopped'])
            finally:
                if process.poll() is None:process.kill();process.wait()
                for stream in (process.stdout,process.stderr):stream.close()
