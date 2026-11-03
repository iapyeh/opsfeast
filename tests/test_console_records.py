import concurrent.futures
import json
import tempfile
import unittest
import uuid
from unittest.mock import patch
from opsfeast.console_records import Records,RecordError

def uid():return str(uuid.uuid4())
def block(text='',kind='stdout',form=None):return {'event_id':uid(),'block_id':uid(),'kind':kind,'title':'synthetic','text':text,'form':form}
def form():return {'fields':[{'name':'note','label':'Note','type':'text','required':False,'options':[]}],'choices':[{'id':'yes','label':'Yes'},{'id':'no','label':'No'}],'expires_at':None}

class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.records=Records(self.tmp.name);self.sid=uid()
        self.body={'session_id':self.sid,'title':'synthetic','host_id':'test','work_id':None};self.records.create(self.body)
    def add(self,text='',kind='stdout',schema=None):
        body=block(text,kind,schema);self.records.add_block(self.sid,body);return body['block_id']
    def test_history_exact_scope_stable_pagination_and_bounded_summaries(self):
        ids=[str(uuid.UUID(int=i)) for i in range(1,5)]
        with patch('opsfeast.console_records.now',return_value='2000-01-01T00:00:00.000+00:00'):
            for sid in ids:
                self.records.create({'session_id':sid,'title':'saved','host_id':'lab / web-01','work_id':None})
        for scope in ('other / web-01','lab / web-010','lab / web-01 / suffix','web-01'):
            self.records.create({'session_id':uid(),'title':'not this host','host_id':scope,'work_id':None})
        raw=block('private output '*1000)
        with patch('opsfeast.console_records.now',return_value='2001-01-01T00:00:00.000+00:00'):
            self.records.add_block(ids[-1],raw)
        first=self.records.list_sessions('lab / web-01',limit=2)
        self.assertEqual([s['session_id'] for s in first['sessions']],list(reversed(ids[2:])))
        self.assertEqual(first['next_cursor'],ids[2])
        item=first['sessions'][0]
        self.assertEqual(item['block_states'],{'streaming':1})
        self.assertEqual(item['block_count'],1)
        self.assertGreater(item['updated_at'],item['created_at'])
        self.assertNotIn('private output',json.dumps(first))
        self.assertEqual(item['reader_url'],'/console/'+ids[-1])
        with patch('opsfeast.console_records.now',return_value='2002-01-01T00:00:00.000+00:00'):
            self.records.create({'session_id':uid(),'title':'new arrival','host_id':'lab / web-01','work_id':None})
        second=self.records.list_sessions('lab / web-01',limit=2,before=first['next_cursor'])
        self.assertEqual([s['session_id'] for s in second['sessions']],list(reversed(ids[:2])))
        self.assertIsNone(second['next_cursor'])
        self.assertEqual(self.records.snapshot(ids[-1])['seq'],1)
        self.assertEqual(self.records.list_sessions('absent')['sessions'],[])
    def test_history_preserves_block_states_empty_records_and_invalid_cursors(self):
        self.assertEqual(self.records.list_sessions('test')['sessions'][0]['block_states'],{})
        for status in ('completed','failed','interrupted','cancelled'):
            bid=self.add('saved');self.records.finish(self.sid,bid,{'event_id':uid(),'status':status})
        self.add('form','form',form())
        item=self.records.list_sessions('test')['sessions'][0]
        self.assertEqual(item['block_count'],5)
        self.assertEqual(item['block_states'],dict.fromkeys(('completed','failed','interrupted','cancelled','waiting'),1))
        for limit in (0,101,True,'25'):
            with self.assertRaisesRegex(RecordError,'invalid_limit'):self.records.list_sessions('test',limit=limit)
        with self.assertRaisesRegex(RecordError,'invalid_cursor'):self.records.list_sessions('other',before=self.sid)
        with self.assertRaisesRegex(RecordError,'invalid_id'):self.records.list_sessions('test',before='bad')
        with self.assertRaisesRegex(RecordError,'unknown_session'):self.records.list_sessions('test',before=uid())
    def test_empty_stream_can_be_read_and_then_appended(self):
        bid=self.add()
        summary=self.records.snapshot(self.sid)['blocks'][0]
        self.assertEqual((summary['size'],summary['head'],summary['tail']),(0,'',''))
        self.assertEqual(self.records.content(self.sid,bid)['next_offset'],0)
        self.records.append(self.sid,bid,{'event_id':uid(),'offset':0,'text':'first'})
        self.assertEqual(self.records.content(self.sid,bid)['text'],'first')
        self.records.append(self.sid,bid,{'event_id':uid(),'offset':5,'text':'\r\n \t'})
        self.assertEqual(self.records.content(self.sid,bid)['text'],'first\r\n \t')
        self.assertEqual(self.records.content(self.sid,bid,9)['text'],'')
        with self.assertRaisesRegex(RecordError,'invalid_text'):
            self.records.append(self.sid,bid,{'event_id':uid(),'offset':9,'text':''})
    def test_agent_activity_lease_restore_idempotency_and_command_handoff(self):
        body={'event_id':uid(),'state':'thinking','lease_seconds':120}
        with patch('opsfeast.console_records.now',return_value='2026-01-01T00:00:00.000+00:00'):
            result=self.records.activity(self.sid,body)
        self.assertEqual(result['activity']['expires_at'],'2026-01-01T00:02:00.000+00:00')
        self.assertEqual(self.records.activity(self.sid,body),result)
        snapshot=Records(self.tmp.name).snapshot(self.sid)
        self.assertEqual(snapshot['session']['activity'],result['activity'])
        self.assertEqual(snapshot['blocks'],[])
        event=self.records.events(self.sid,0)[0]
        self.assertEqual(event['type'],'activity.updated');self.assertNotIn('block',event)
        # Incoming stdout cannot imply that the agent stopped thinking.
        self.add('tail output');self.assertEqual(self.records.snapshot(self.sid)['session']['activity']['state'],'thinking')
        # Actual input/communication ends the lease in that same durable event.
        self.add('next command','command')
        self.assertEqual(self.records.snapshot(self.sid)['session']['activity']['state'],'idle')
        self.assertEqual(self.records.events(self.sid,2)[0]['activity']['state'],'idle')
        self.records.activity(self.sid,{'event_id':uid(),'state':'thinking','lease_seconds':1})
        idle=self.records.activity(self.sid,{'event_id':uid(),'state':'idle','lease_seconds':0})
        self.assertIsNone(idle['activity']['expires_at'])
    def test_agent_activity_validation_and_event_conflicts_do_not_change_state(self):
        before=self.records.snapshot(self.sid)
        for state,seconds in [('unknown',120),('idle',1),('thinking',0),('thinking',301),('thinking',True),('thinking','120')]:
            with self.subTest(state=state,seconds=seconds),self.assertRaisesRegex(RecordError,'invalid_activity'):
                self.records.activity(self.sid,{'event_id':uid(),'state':state,'lease_seconds':seconds})
        self.assertEqual(self.records.snapshot(self.sid),before)
        body={'event_id':uid(),'state':'thinking','lease_seconds':60};self.records.activity(self.sid,body)
        with self.assertRaisesRegex(RecordError,'event_conflict'):self.records.activity(self.sid,{**body,'lease_seconds':120})
    def test_bounded_snapshot_range_utf8_and_restore(self):
        bid=self.add('前言\n');raw=('繁體中文一行\n'*1000).encode();offset=len('前言\n'.encode())
        self.records.append(self.sid,bid,{'event_id':uid(),'offset':offset,'text':raw.decode()})
        snap=Records(self.tmp.name).snapshot(self.sid)
        self.assertLess(len(json.dumps(snap)),7000)
        self.assertEqual(snap['blocks'][0]['size'],len(raw)+offset)
        self.assertNotIn('content',snap['blocks'][0])
        recovered='';cursor=0
        while cursor<snap['blocks'][0]['size']:
            page=self.records.content(self.sid,bid,cursor,257)
            self.assertGreater(page['next_offset'],cursor);cursor=page['next_offset'];recovered+=page['text']
        self.assertEqual(recovered,'前言\n'+raw.decode())
        with self.assertRaisesRegex(RecordError,'invalid_utf8_offset'):self.records.content(self.sid,bid,1)
        self.assertEqual(self.records.create(self.body)['seq'],2)
    def test_exact_retries_offset_conflict_and_finish(self):
        body=block('a');bid=body['block_id'];first=self.records.add_block(self.sid,body)
        self.assertEqual(self.records.add_block(self.sid,body),first)
        request={'event_id':uid(),'offset':1,'text':'b'}
        accepted=self.records.append(self.sid,bid,request)
        self.assertEqual(self.records.append(self.sid,bid,request),accepted)
        with self.assertRaisesRegex(RecordError,'event_conflict'):self.records.append(self.sid,bid,{**request,'text':'changed'})
        with self.assertRaisesRegex(RecordError,'offset_conflict'):self.records.append(self.sid,bid,{**request,'event_id':uid()})
        finish={'event_id':uid(),'status':'completed'};result=self.records.finish(self.sid,bid,finish)
        self.assertEqual(self.records.finish(self.sid,bid,finish),result)
        with self.assertRaisesRegex(RecordError,'block_not_streaming'):self.records.append(self.sid,bid,{'event_id':uid(),'offset':2,'text':'c'})
        self.assertEqual(self.records.content(self.sid,bid)['text'],'ab')
    def test_reply_idempotency_stale_expired_and_cancelled(self):
        bid=self.add('Inspect the action','form',form())
        body={'event_id':uid(),'revision':1,'choice':'yes','values':{'note':'Go'}}
        with self.assertRaisesRegex(RecordError,'stale_form'):self.records.respond(self.sid,bid,{**body,'revision':0},'tester')
        result=self.records.respond(self.sid,bid,body,'tester')
        self.assertEqual(self.records.respond(self.sid,bid,body,'tester'),result)
        with self.assertRaisesRegex(RecordError,'form_not_waiting'):self.records.respond(self.sid,bid,{**body,'event_id':uid()},'tester')
        event=self.records.events(self.sid,1)[0]
        self.assertEqual(event['response']['authority'],'administrator_cookie')
        expired=form();expired['expires_at']='2000-01-01T00:00:00+00:00'
        bid2=self.add('expired','form',expired)
        with self.assertRaisesRegex(RecordError,'form_expired'):self.records.respond(self.sid,bid2,{**body,'event_id':uid()},'tester')
        bid3=self.add('cancel','form',form());self.records.finish(self.sid,bid3,{'event_id':uid(),'status':'cancelled'})
        with self.assertRaisesRegex(RecordError,'form_not_waiting'):self.records.respond(self.sid,bid3,{**body,'event_id':uid()},'tester')
    def test_limits_invalid_form_and_no_partial_write(self):
        bid=self.add('a')
        before=self.records.snapshot(self.sid)
        with patch('opsfeast.console_records.BLOCK_LIMIT',2):
            with self.assertRaisesRegex(RecordError,'block_limit_reached'):self.records.append(self.sid,bid,{'event_id':uid(),'offset':1,'text':'too big'})
        self.assertEqual(self.records.snapshot(self.sid),before)
        invalid=form();invalid['fields'][0]['name']='__proto__'
        with self.assertRaises(RecordError):self.add('bad','form',invalid)
        for value in (-1,99):
            with self.assertRaises(RecordError):self.records.events(self.sid,value)
    def test_concurrent_blocks_and_event_recovery(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda i:self.add(str(i)),range(12)))
        snapshot=self.records.snapshot(self.sid)
        self.assertEqual(snapshot['seq'],12)
        recovered={}
        for event in self.records.events(self.sid,0):recovered[event['block']['id']]=event['block']
        self.assertEqual(list(recovered.values()),snapshot['blocks'])
