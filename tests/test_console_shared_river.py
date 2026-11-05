"""Shared task sources, concurrent writers and independent host activity; synthetic only."""
import concurrent.futures
import tempfile
import unittest
import uuid
from opsfeast.console_records import Records,RecordError
from opsfeast.console_agent import Publisher,ControlError


def uid():return str(uuid.uuid4())
def participant(host,profile='lab',icon='🖥'):
    return {'profile':profile,'host_id':host,'icon':icon}

class Transport:
    def __init__(self,records):self.records=records
    def get(self,path):return self.records.snapshot(path.strip('/'))
    def post(self,path,body):
        if not path:return self.records.create(body)
        parts=path.strip('/').split('/')
        if parts[1]=='activity':return self.records.activity(parts[0],body)
        if len(parts)==2:return self.records.add_block(parts[0],body)
        return (self.records.append if parts[-1]=='append' else self.records.finish)(parts[0],parts[2],body)

class SharedRiverTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.records=Records(tmp.name);self.sid=uid()
        self.body={'session_id':self.sid,'title':'One investigation','host_id':'Shared task','work_id':None,
                   'targets':[participant('guest'),participant('hypervisor')]}
        self.records.create(self.body)
        self.transport=Transport(self.records)
    def publisher(self,host):return Publisher(self.transport,title='unused',host_id='lab / '+host,session_id=self.sid)
    def test_attach_does_not_create_session_or_connect_and_rejects_wrong_scope(self):
        before=self.records.snapshot(self.sid)
        for host in ('guest','hypervisor'):self.assertEqual(self.publisher(host).sid,self.sid)
        self.assertEqual(self.records.snapshot(self.sid),before)
        for host in ('guest-extra','different / guest'):
            with self.assertRaisesRegex(ControlError,'shared_target_not_declared'):self.publisher(host)
        self.assertEqual(self.records.create(self.body),before)
        with self.assertRaisesRegex(RecordError,'session_conflict'):
            self.records.create({**self.body,'targets':list(reversed(self.body['targets']))})
        with self.assertRaisesRegex(RecordError,'session_conflict'):
            self.records.create({k:v for k,v in self.body.items() if k!='targets'})
        plain={k:v for k,v in self.body.items() if k!='targets'}
        plain['session_id']=uid();before_plain=self.records.create(plain)
        with self.assertRaisesRegex(RecordError,'session_conflict'):
            self.records.create({**plain,'targets':self.body['targets']})
        self.assertEqual(self.records.snapshot(plain['session_id']),before_plain)
    def test_concurrent_publishers_keep_sources_and_positions_across_stream_updates(self):
        writers=[self.publisher('guest'),self.publisher('hypervisor')]
        def write(i):
            pub=writers[i%2];bid=pub.block('stdout',str(i));pub.append(bid,' tail');pub.finish(bid);return bid
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:ids=list(pool.map(write,range(12)))
        snapshot=self.records.snapshot(self.sid)
        self.assertEqual([b['position'] for b in snapshot['blocks']],list(range(1,13)))
        for block in snapshot['blocks']:
            value=int(block['head'].split()[0]);self.assertEqual(block['target_id'],writers[value%2].target_id)
            self.assertEqual(block['head'],str(value)+' tail')
        self.assertEqual(len(ids),12)
        for event in self.records.events(self.sid,0):
            if 'block' in event:self.assertIn(event['block']['target_id'],['lab / guest','lab / hypervisor'])
        for host in ('guest','hypervisor'):
            history=self.records.list_sessions('lab / '+host)
            self.assertEqual(history['sessions'][0]['session_id'],self.sid)
        self.assertEqual(self.records.list_sessions('other / guest')['sessions'],[])
    def test_common_analysis_unscoped_and_activity_does_not_clear_other_host(self):
        a,b=self.publisher('guest'),self.publisher('hypervisor')
        a.activity('thinking');b.activity('thinking')
        a.block('command','read only')
        state=self.records.snapshot(self.sid)['session']['target_activities']
        self.assertEqual(state[a.target_id]['state'],'idle');self.assertEqual(state[b.target_id]['state'],'thinking')
        a.activity('idle')
        self.assertEqual(self.records.snapshot(self.sid)['session']['target_activities'][b.target_id]['state'],'thinking')
        body=dict(event_id=uid(),block_id=uid(),kind='analysis',title='Joint conclusion',text='common',form=None)
        self.records.add_block(self.sid,body)
        self.assertNotIn('target_id',self.records.snapshot(self.sid)['blocks'][-1])
        for method,payload in [
            (self.records.add_block,{**body,'event_id':uid(),'block_id':uid(),'target_id':'other / guest'}),
            (self.records.activity,dict(event_id=uid(),state='thinking',lease_seconds=30,target_id='other / guest'))]:
            before=self.records.snapshot(self.sid)
            with self.assertRaisesRegex(RecordError,'unknown_target'):method(self.sid,payload)
            self.assertEqual(self.records.snapshot(self.sid),before)
    def test_participant_validation_and_shared_history_paging(self):
        for value in ([],[participant('a')]*2,[participant('a','bad/profile')],[participant('a')]*17):
            with self.assertRaises(RecordError):self.records.create({**self.body,'session_id':uid(),'targets':value})
        from unittest.mock import patch
        second=uid()
        with patch('opsfeast.console_records.now',return_value='2999-01-01T00:00:00.000+00:00'):
            self.records.create({**self.body,'session_id':second})
        page=self.records.list_sessions('lab / guest',limit=1)
        self.assertEqual(page['sessions'][0]['session_id'],second)
        self.assertEqual(self.records.list_sessions('lab / guest',limit=1,before=page['next_cursor'])['sessions'][0]['session_id'],self.sid)
        with self.assertRaisesRegex(RecordError,'invalid_cursor'):self.records.list_sessions('other / guest',before=second)

class SharedControllerTests(unittest.TestCase):
    def test_controller_forwards_shared_uuid_without_credentials_in_argv(self):
        from unittest.mock import Mock,patch
        from opsfeast.web.agent_control import Controller
        controller=Controller('http://127.0.0.1:8740','synthetic-capability',lambda value:None)
        process=Mock();process.stdout=[];process.stdin=Mock()
        sid=uid()
        import os
        def fake_start(*args,**kwargs):
            held=os.dup(kwargs['pass_fds'][0]);self.addCleanup(os.close,held);return process
        with patch('opsfeast.web.agent_control.subprocess.Popen',side_effect=fake_start) as start:
            controller.start_worker(dict(op='worker.start',request_id='start',worker_id='guest',host='guest',profile='lab',session=sid))
        argv=start.call_args.args[0]
        self.assertEqual(argv[argv.index('--session')+1],sid)
        self.assertNotIn('synthetic-capability',argv)
        with self.assertRaisesRegex(ValueError,'shared_session_requires_host'):
            controller.start_worker(dict(op='worker.start',request_id='bad',worker_id='local',local=True,session=sid))
