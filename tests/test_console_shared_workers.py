"""Two independent local Bash workers share a synthetic river; no SSH hosts."""
import importlib.util
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from opsfeast.console_records import Records

@unittest.skipUnless(importlib.util.find_spec('sshscript'),'requires execution extra')
class SharedWorkerProcessTests(unittest.TestCase):
    def test_two_workers_stream_and_close_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);records=Records(root/'records');sid=str(uuid.uuid4())
            records.create(dict(session_id=sid,title='Synthetic two-worker test',host_id='Shared task',work_id=None,
                targets=[dict(profile='lab',host_id=h,icon='🖥') for h in ('guest','hypervisor')]))
            class Handler(BaseHTTPRequestHandler):
                def reply(self,value):
                    raw=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
                def do_GET(self):self.reply(records.snapshot(self.path.rsplit('/',1)[-1]))
                def do_POST(self):
                    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));session=self.path.split('/')[4];parts=self.path.split('/')[5:]
                    if parts==['blocks']:value=records.add_block(session,body)
                    elif parts==['activity']:value=records.activity(session,body)
                    else:value=(records.append if parts[-1]=='append' else records.finish)(session,parts[1],body)
                    self.reply(value)
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            token=root/'token';token.write_text('synthetic-test-only')
            script=root/'local_workers.py'
            script.write_text('import sys; sys.path.insert(0, '+repr(str(Path(__file__).resolve().parents[1]))+')\n'+'''import contextlib,sys
from pathlib import Path
from types import SimpleNamespace
import opsfeast
from sshscript import Session,Console
from opsfeast.console_agent import main
@contextlib.contextmanager
def local_console(*args,**kwargs):
    with Session() as s:
        with Console(s,stdout=kwargs['stdout'],stderr=kwargs['stderr']) as c:yield c
profile=SimpleNamespace(name='lab',root=Path('.'),sessions=SimpleNamespace(console_target=lambda host:{'fingerprint':'synthetic'},console=local_console))
opsfeast.Instance.open=lambda:SimpleNamespace(profile=lambda name:profile)
sys.exit(main(sys.argv[1:]))
''')
            processes=[];queues=[]
            try:
                for host in ('guest','hypervisor'):
                    p=subprocess.Popen([sys.executable,'-B','-u',str(script),'--host',host,'--session',sid,'--url','http://127.0.0.1:'+str(server.server_port),'--token-file',str(token)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    processes.append(p);q=queue.Queue();queues.append(q)
                    def pump(process=p,events=q):
                        for line in process.stdout:events.put(json.loads(line))
                    threading.Thread(target=pump,daemon=True).start()
                def event(i,kind,rid=None):
                    while True:
                        value=queues[i].get(timeout=15);self.assertNotEqual(value['type'],'failed',value)
                        if value['type']==kind and (rid is None or value.get('request_id')==rid):return value
                def send(i,**body):processes[i].stdin.write(json.dumps(body)+'\n');processes[i].stdin.flush()
                for i in range(2):
                    self.assertEqual(event(i,'created')['session_id'],sid)
                    send(i,op='connect',request_id='connect');self.assertEqual(event(i,'result','connect')['state'],'ready')
                for i in range(2):send(i,op='run',request_id='read',command='printf first; sleep .3; printf second',timeout=5)
                for i in range(2):self.assertEqual(event(i,'result','read')['state'],'completed')
                send(0,op='close',request_id='close');self.assertEqual(event(0,'result','close')['state'],'closed')
                send(1,op='run',request_id='retained',command='printf retained',timeout=5);self.assertEqual(event(1,'result','retained')['state'],'completed')
                send(1,op='close',request_id='close');self.assertEqual(event(1,'result','close')['state'],'closed')
                snap=records.snapshot(sid);self.assertEqual([b['position'] for b in snap['blocks']],list(range(1,len(snap['blocks'])+1)))
                for target in ('lab / guest','lab / hypervisor'):
                    output=''.join(records.content(sid,b['id'])['text'] for b in snap['blocks'] if b.get('target_id')==target and b['kind']=='stdout')
                    self.assertIn('firstsecond',output);self.assertEqual('retained' in output,target=='lab / hypervisor')
                    self.assertEqual(snap['session']['target_activities'][target]['state'],'idle')
            finally:
                for p in processes:
                    if p.poll() is None:p.kill()
                    p.communicate()
