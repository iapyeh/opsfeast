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
