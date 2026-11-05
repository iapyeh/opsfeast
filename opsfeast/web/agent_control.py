"""Memory-only owner capability and JSON-lines agent control, protocol 0.1.0."""
import base64
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from opsfeast.console_agent import Controls


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Controller:
    def __init__(self, origin, token, emit):
        self.origin, self.token, self.emit = origin, token, emit
        self.workers = {}
        self.seen = set()
        self.http = build_opener(ProxyHandler({}),NoRedirect)

    def request(self, method, path, body=None, *, raw=None):
        parsed = urlsplit(path)
        if (method not in ('GET','POST','PUT','PATCH','DELETE') or not path.startswith('/api/v1/')
                or parsed.scheme or parsed.netloc or parsed.fragment or '\\' in path
                or any(c in path for c in '\r\n')):
            raise ValueError('invalid_request_target')
        data = raw if raw is not None else (json.dumps(body,ensure_ascii=False).encode() if body is not None else None)
        payload, mime = data if isinstance(data,tuple) else (data,'application/json')
        request = Request(self.origin+path, data=payload, method=method,
                          headers={'Authorization':'Bearer '+self.token,'Content-Type':mime})
        try:
            response = self.http.open(request,timeout=30)
        except HTTPError as error:
            response = error
        with response:
            value = response.read(4*1024*1024+1)
            if len(value)>4*1024*1024:raise ValueError('response_too_large')
            try:result=json.loads(value)
            except (ValueError,UnicodeError):result={'base64':base64.b64encode(value).decode()}
            return {'status':response.code,'body':result}

    def start_worker(self, body):
        allowed={'op','request_id','worker_id','host','profile','title','local','session'}
        if set(body)-allowed:raise ValueError('invalid_worker_fields')
        key=body['worker_id']
        if not isinstance(key,str) or not key or len(key)>100 or key in self.workers:raise ValueError('invalid_worker_id')
        local=body.get('local',False)
        if type(local) is not bool or (local == ('host' in body)):raise ValueError('select_host_or_local')
        argv=[sys.executable,'-B','-u','-m','opsfeast.console_agent','--url',self.origin]
        argv+=['--local'] if local else ['--host',body['host']]
        for name in ('profile','title','session'):
            if name in body:
                if not isinstance(body[name],str):raise ValueError('invalid_worker_field')
                argv+=['--'+name,body[name]]
        if 'session' in body:
            from opsfeast.console_records import identifier
            identifier(body['session'])
            if local:raise ValueError('shared_session_requires_host')
        read_fd,write_fd=os.pipe()
        try:
            process=subprocess.Popen(argv+['--token-fd',str(read_fd)],stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                     text=True,bufsize=1,pass_fds=(read_fd,))
            self.workers[key]=process
            os.close(read_fd);read_fd=None
            with os.fdopen(write_fd,'w') as stream:
                write_fd=None;stream.write(self.token+'\n')
        finally:
            for fd in (read_fd,write_fd):
                if fd is not None:os.close(fd)
        def pump():
            for line in process.stdout:
                try:event=json.loads(line)
                except ValueError:event={'type':'invalid_worker_output'}
                self.emit({'type':'worker_event','worker_id':key,'event':event})
            self.emit({'type':'worker_exit','worker_id':key,'exitcode':process.wait()})
        threading.Thread(target=pump,daemon=True).start()
        return {'worker_id':key,'state':'starting'}

    @staticmethod
    def authorization(body):
        value=body.get('authorization')
        if not isinstance(value,str) or not value.strip() or len(value)>1000:
            raise ValueError('authorization_description_required')

    def dispatch(self, body):
        if not isinstance(body,dict):raise ValueError('object_required')
        rid=body.get('request_id')
        if not isinstance(rid,str) or not rid or len(rid)>100 or rid in self.seen:raise ValueError('invalid_or_duplicate_request_id')
        if len(self.seen)>=100000:raise ValueError('controller_request_limit')
        self.seen.add(rid)
        op=body.get('op')
        if op=='request':
            if set(body)-{'op','request_id','method','path','body','body_base64','content_type','authorization'}:raise ValueError('invalid_request_fields')
            if body.get('method','GET')!='GET':self.authorization(body)
            if 'body' in body and 'body_base64' in body:raise ValueError('ambiguous_body')
            raw=None
            if 'body_base64' in body:raw=(base64.b64decode(body['body_base64'],validate=True),body.get('content_type','application/octet-stream'))
            return self.request(body.get('method','GET'),body['path'],body.get('body'),raw=raw)
        if op=='admin.password':
            if set(body)-{'op','request_id','username','password','generate','authorization'}:raise ValueError('invalid_password_fields')
            self.authorization(body)
            generated=body.get('generate',False)
            if type(generated) is not bool or generated==('password' in body):raise ValueError('select_password_or_generate')
            state=self.request('GET','/api/v1/admin')
            if state['status']!=200:return state
            username=body.get('username',state['body']['username'])
            password=secrets.token_urlsafe(18) if generated else body['password']
            result=self.request('PUT','/api/v1/agent/administrator',dict(username=username,password=password,expected_revision=state['body']['revision']))
            if generated and result['status']==200:result['generated_password']=password
            return result
        if op=='worker.start':return self.start_worker(body)
        if op=='worker.send':
            if set(body)!={'op','request_id','worker_id','control'}:raise ValueError('invalid_worker_fields')
            worker=self.workers[body['worker_id']]
            if worker.poll() is not None:raise ValueError('worker_closed')
            worker.stdin.write(json.dumps(body['control'],ensure_ascii=False)+'\n');worker.stdin.flush()
            return {'state':'sent'}
        if op=='shutdown':
            if set(body)!={'op','request_id'}:raise ValueError('invalid_shutdown_fields')
            return {'state':'stopping'}
        raise ValueError('unsupported_operation')

    def close(self):
        # EOF asks each worker to perform its normal owned-scope cleanup.
        for worker in self.workers.values():
            if worker.poll() is None:
                try:worker.stdin.close()
                except (BrokenPipeError,OSError):pass
        deadline=time.monotonic()+30
        states={}
        for key,worker in self.workers.items():
            try:worker.wait(timeout=max(0,deadline-time.monotonic()));states[key]='exited'
            except subprocess.TimeoutExpired:
                states[key]='cleanup_unknown'
        return states


def run(app, token, *, port, listener=None):
    import uvicorn
    lock=threading.Lock()
    def emit(value):
        # Never expose the capability, even if an endpoint echoes submitted input.
        text=json.dumps(value,ensure_ascii=False).replace(token,'[agent capability hidden]')
        with lock:sys.stdout.write(text+'\n');sys.stdout.flush()
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,access_log=False,log_level='error',timeout_graceful_shutdown=5))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener] if listener else None),daemon=True);thread.start()
    controller=Controller('http://127.0.0.1:'+str(port),token,emit)
    controls=Controls(sys.stdin.fileno())
    stop_browser_events=threading.Event()
    def browser_events():
        cursor=0
        while not stop_browser_events.is_set():
            batch=app.state.browser_events.read(cursor,1)
            if batch['gap']:emit({'type':'browser_event_gap','after':cursor,'next_seq':batch['next_seq']})
            for event in batch['events']:emit({'type':'browser_event','event':event})
            cursor=batch['next_seq']
    browser_thread=threading.Thread(target=browser_events,daemon=True)
    try:
        deadline=time.monotonic()+10
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('server_start_failed')
            thread.join(.02)
        emit({'type':'ready','protocol_version':'0.1.0','url':controller.origin,'capability':'memory_only'})
        browser_thread.start()
        while True:
            body=controls.read(1)
            if body is None:
                if not thread.is_alive():break
                continue
            if controls.eof:break
            try:
                result=controller.dispatch(body)
                emit({'type':'result','request_id':body.get('request_id'),**result})
                if body.get('op')=='shutdown':break
            except Exception as error:
                emit({'type':'rejected','request_id':body.get('request_id') if isinstance(body,dict) else None,
                      'error_type':type(error).__name__})
    finally:
        stop_browser_events.set()
        if browser_thread.is_alive():browser_thread.join(2)
        states=controller.close()
        server.should_exit=True;thread.join(10)
        controls.close()
        emit({'type':'closed','workers':states,'server_stopped':not thread.is_alive()})
