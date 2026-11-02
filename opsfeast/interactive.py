"""Interactive work protocol 0.1.0: durable events and a single threaded Console.

No agent code evaluation. Host connections are opt-in and begin only after an
operator approves a finite exact plan. Restart never replays executable input.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import threading
import time
import uuid

VERSION='0.1.0'
OUTPUT_LIMIT=2*1024*1024
TERMINAL={'closed','interrupted','failed'}

class InteractiveError(ValueError):
    def __init__(self,code): self.code=code;super().__init__(code)

def timestamp():return datetime.now(timezone.utc).isoformat(timespec='milliseconds')
def text(value,limit=8192):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or '\x00' in value:
        raise InteractiveError('invalid_text')
    try:value.encode('utf-8')
    except UnicodeError:raise InteractiveError('invalid_text') from None
    return value

def apply_delta(state,delta):
    state=deepcopy(state)
    for op in delta:
        path=op['path']
        if not isinstance(path,list) or not path or len(path)>8 or any(not isinstance(key,str) or key in ('__proto__','prototype','constructor') for key in path):
            raise InteractiveError('invalid_delta_path')
        target=state
        for key in path[:-1]:target=target[key]
        key=path[-1]
        if op['op']=='set':target[key]=deepcopy(op['value'])
        elif op['op']=='append_text':target[key]+=op['value']
        elif op['op']=='append':target[key].append(deepcopy(op['value']))
        else:raise InteractiveError('invalid_delta_operation')
    return state

def set_value(key,value):return {'op':'set','path':[key],'value':value}

class Store:
    def __init__(self,root):
        root=Path(root)
        if root.is_symlink():raise InteractiveError('invalid_storage')
        root.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.path=root/'interactive.sqlite3'
        if self.path.is_symlink():raise InteractiveError('invalid_storage')
        self.lock=threading.RLock()
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS work(id TEXT PRIMARY KEY,seq INTEGER NOT NULL,state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS event(work_id TEXT,seq INTEGER,event TEXT,PRIMARY KEY(work_id,seq));
            CREATE TABLE IF NOT EXISTS request(work_id TEXT,id TEXT,digest TEXT,response TEXT,PRIMARY KEY(work_id,id));
            ''')
        os.chmod(self.path,0o600)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            with db:yield db
        finally:db.close()
    def snapshot(self,work_id):
        with self.lock,self.connect() as db:
            row=db.execute('SELECT seq,state FROM work WHERE id=?',(work_id,)).fetchone()
            if not row:raise InteractiveError('unknown_work')
            return {'protocol_version':VERSION,'seq':row[0],'state':json.loads(row[1])}
    def events(self,work_id,after=0):
        with self.lock,self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT event FROM event WHERE work_id=? AND seq>? ORDER BY seq LIMIT 128',(work_id,after))]
    def list(self):
        with self.lock,self.connect() as db:
            return [dict(work_id=row[0],**{key:json.loads(row[1])[key] for key in ('host_id','profile','status','created_at','goal')}) for row in db.execute('SELECT id,state FROM work ORDER BY rowid DESC LIMIT 100')]
    def _emit(self,db,work_id,kind,actor,delta,payload=None):
        row=db.execute('SELECT seq,state FROM work WHERE id=?',(work_id,)).fetchone()
        seq,state=row[0]+1,json.loads(row[1])
        event={'protocol_version':VERSION,'work_id':work_id,'event_id':str(uuid.uuid4()),'seq':seq,'received_at':timestamp(),'actor':actor,'type':kind,'delta':delta,'payload':payload or {}}
        state=apply_delta(state,delta)
        db.execute('UPDATE work SET seq=?,state=? WHERE id=?',(seq,json.dumps(state),work_id))
        db.execute('INSERT INTO event VALUES(?,?,?)',(work_id,seq,json.dumps(event)))
        return event
    def emit(self,work_id,kind,actor,delta,payload=None):
        with self.lock,self.connect() as db:return self._emit(db,work_id,kind,actor,delta,payload)
    def create(self,profile,host,goal,*,target=None):
        work_id=str(uuid.uuid4())
        state={'work_id':work_id,'profile':profile,'host_id':host,'goal':goal,'created_at':timestamp(),'status':'draft','plan':None,'current':None,'history':[],'feedback':[],'analyses':[],'identity':None,'output_bytes':0,'cleanup':'not_started','last_error':None,'target':target or {}}
        with self.lock,self.connect() as db:
            db.execute('INSERT INTO work VALUES(?,?,?)',(work_id,0,'{}'))
            self._emit(db,work_id,'work.created','operator',[set_value(key,value) for key,value in state.items()])
        return work_id

class Service:
    def __init__(self,root,installation,*,targets=(),connector=None,idle_seconds=900):
        self.store=Store(root);self.installation=Path(installation)
        import fcntl
        self.owner_fd=os.open(Path(root)/'.executor.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:fcntl.flock(self.owner_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.owner_fd);self.owner_fd=None
            raise InteractiveError('interactive_service_already_running') from None
        self.targets=set(tuple(target) for target in targets);self.custom_connector=connector is not None;self.connector=connector or self._connect
        self.lock=threading.RLock();self.worker=None;self.work_id=None;self.controls=queue.Queue();self.idle_seconds=idle_seconds;self.shutting_down=False
        self.stop_flag=threading.Event();self.close_flag=threading.Event()
        # No surviving in-memory worker is assumed after process restart.
        with self.store.connect() as db:
            existing=[{'work_id':row[0],'status':json.loads(row[1])['status']} for row in db.execute('SELECT id,state FROM work')]
        for item in existing:
            if item['status'] not in TERMINAL:
                delta=[set_value('status','interrupted'),set_value('cleanup','unknown')]
                current=self.store.snapshot(item['work_id'])['state'].get('current')
                if current:delta.append({'op':'set','path':['current','status'],'value':'interrupted'})
                self.store.emit(item['work_id'],'server.recovered','server',delta,{'reason':'execution_not_resumed'})
    @contextmanager
    def _connect(self,profile,host):
        from opsfeast import Instance
        expected=self.store.snapshot(self.work_id)['state']['target'].get('fingerprint')
        with Instance.open(self.installation).profile(profile).sessions.console(host,timeout=15,expected_fingerprint=expected) as console:yield console
    def create(self,profile,host,goal):
        text(profile,100);text(host,200)
        if (profile,host) not in self.targets:raise InteractiveError('target_not_enabled')
        return self.store.create(profile,host,text(goal,2000),target=self.target(profile,host))
    def target(self,profile,host):
        if self.custom_connector:return {'namespace':'synthetic','fingerprint':'synthetic'}
        from opsfeast import Instance
        return Instance.open(self.installation).profile(profile).sessions.console_target(host)
    def action(self,work_id,action,body,*,role):
        if self.shutting_down:raise InteractiveError('server_stopping')
        if not isinstance(body,dict):raise InteractiveError('object_required')
        request_id=body.get('request_id');text(request_id,100)
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{8,100}',request_id):raise InteractiveError('invalid_request_id')
        if role not in ('operator','agent'):raise InteractiveError('invalid_actor')
        try:digest=hashlib.sha256(json.dumps([action,body,role],sort_keys=True,allow_nan=False).encode()).hexdigest()
        except (ValueError,TypeError,UnicodeError):raise InteractiveError('invalid_json_value') from None
        with self.lock,self.store.lock,self.store.connect() as db:
            prior=db.execute('SELECT digest,response FROM request WHERE work_id=? AND id=?',(work_id,request_id)).fetchone()
            if prior:
                if prior[0]!=digest:raise InteractiveError('request_id_conflict')
                return json.loads(prior[1])
            snap=self.store.snapshot(work_id);state=snap['state'];status=state['status']
            if state['profile'] and (state['profile'],state['host_id']) not in self.targets:raise InteractiveError('target_not_enabled')
            if action in ('approve','continue','reject','close') and role!='operator':raise InteractiveError('operator_required')
            command=None
            if action=='plan':
                if status not in ('draft','awaiting_plan','ready','paused','failed_step'):raise InteractiveError('work_busy')
                if set(body)!={'request_id','title','steps','approval_mode'}:raise InteractiveError('invalid_plan')
                title=text(body['title'],2000);steps=body['steps'];mode=body['approval_mode']
                if mode not in ('each','plan') or not isinstance(steps,list) or not 1<=len(steps)<=20:raise InteractiveError('invalid_plan')
                clean=[]
                for item in steps:
                    if not isinstance(item,dict) or set(item)!={'command','purpose','checkpoint','timeout'}:raise InteractiveError('invalid_step')
                    if type(item['checkpoint']) is not bool or type(item['timeout']) is not int or not 1<=item['timeout']<=60:raise InteractiveError('invalid_step')
                    command_text=text(item['command'])
                    if '\n' in command_text or '\r' in command_text:raise InteractiveError('command_must_be_single_line')
                    clean.append(dict(step_id=str(uuid.uuid4()),command=command_text,purpose=text(item['purpose'],1000),checkpoint=item['checkpoint'],timeout=item['timeout']))
                plan={'plan_id':str(uuid.uuid4()),'title':title,'steps':clean,'approval_mode':mode,'next':0,'approved':False}
                delta=[set_value('plan',plan),set_value('status','awaiting_plan')]
            elif action in ('approve','continue'):
                if status not in ('awaiting_plan','paused','awaiting_step'):raise InteractiveError('not_waiting_for_approval')
                if set(body)!={'request_id','plan_id'} or body['plan_id']!=state['plan']['plan_id']:raise InteractiveError('stale_plan')
                if self.target(state['profile'],state['host_id'])['fingerprint']!=state['target']['fingerprint']:
                    raise InteractiveError('target_configuration_changed')
                if self.shutting_down:raise InteractiveError('server_stopping')
                if self.worker and self.worker.is_alive() and self.work_id!=work_id:raise InteractiveError('console_capacity_reached')
                plan=deepcopy(state['plan']);plan['approved']=True
                delta=[set_value('plan',plan),set_value('status','queued')];command='run'
            elif action=='reject':
                if status not in ('awaiting_plan','paused','awaiting_step'):raise InteractiveError('not_waiting_for_approval')
                delta=[set_value('status','draft')]
            elif action=='stop':
                if role not in ('operator','agent'):raise InteractiveError('operator_required')
                if status not in ('running','queued','connecting'):raise InteractiveError('not_running')
                delta=[set_value('status','stop_requested')];command='stop'
            elif action=='close':
                if status in TERMINAL:raise InteractiveError('already_closed')
                delta=[set_value('status','closing')];command='close'
            elif action=='feedback':
                value=text(body.get('text'),8000)
                delta=[{'op':'append','path':['feedback'],'value':{'text':value,'actor':role,'at':timestamp()}}]
            elif action=='analysis':
                value=body.get('content')
                if not isinstance(value,dict) or value.get('kind') not in ('text','table'):raise InteractiveError('invalid_analysis')
                if value['kind']=='text':value={'kind':'text','text':text(value.get('text'),16000)}
                else:
                    columns=value.get('columns');rows=value.get('rows')
                    if not isinstance(columns,list) or not 1<=len(columns)<=12 or not isinstance(rows,list) or len(rows)>200:raise InteractiveError('invalid_analysis')
                    columns=[text(x,100) for x in columns]
                    if any(not isinstance(row,list) or len(row)!=len(columns) or any(not isinstance(cell,(str,int,float,bool,type(None))) for cell in row) for row in rows):raise InteractiveError('invalid_analysis')
                    value={'kind':'table','columns':columns,'rows':rows}
                    if len(json.dumps(value,allow_nan=False))>32000:raise InteractiveError('analysis_too_large')
                delta=[{'op':'append','path':['analyses'],'value':{'content':value,'actor':role,'at':timestamp()}}]
            else:raise InteractiveError('unknown_action')
            if status in TERMINAL and action not in ('feedback','analysis'):raise InteractiveError('work_not_active')
            event=self.store._emit(db,work_id,'action.'+action,role,delta)
            response={'accepted':True,'work_id':work_id,'seq':event['seq']}
            db.execute('INSERT INTO request VALUES(?,?,?,?)',(work_id,request_id,digest,json.dumps(response)))
            db.commit()  # Commit acceptance before executable dispatch, never replay on restart.
            if command=='run':
                self.stop_flag.clear();self.close_flag.clear()
                if not self.worker or not self.worker.is_alive():
                    self.controls=queue.Queue();self.work_id=work_id
                    self.worker=threading.Thread(target=self._run,args=(work_id,),daemon=True,name='opsfeast-console')
                    self.worker.start()
                self.controls.put('run')
            elif command:
                if self.work_id==work_id:
                    self.stop_flag.set()
                    if command=='close':self.close_flag.set()
                if self.worker and self.worker.is_alive() and self.work_id==work_id:self.controls.put(command)
                elif command=='close':self.store.emit(work_id,'session.closed','server',[set_value('status','closed'),set_value('cleanup','not_connected')])
            return response
    def _emit(self,work_id,kind,delta,payload=None):return self.store.emit(work_id,kind,'executor',delta,payload)
    def _run(self,work_id):
        try:
            state=self.store.snapshot(work_id)['state']
            if state['status'] in ('closing','stop_requested') or self.stop_flag.is_set() or self.close_flag.is_set():
                self._emit(work_id,'session.cancelled',[set_value('status','closed'),set_value('cleanup','not_connected')]);return
            self._emit(work_id,'session.connecting',[set_value('status','connecting')])
            with self.connector(state['profile'],state['host_id']) as console:
                from dataclasses import asdict
                identity=asdict(console.environments[-1])
                self._emit(work_id,'session.connected',[set_value('identity',identity),set_value('status','closing' if self.close_flag.is_set() else 'paused' if self.stop_flag.is_set() else 'queued'),set_value('cleanup','pending')])
                while not self.close_flag.is_set():
                    try:control=self.controls.get(timeout=self.idle_seconds)
                    except queue.Empty:
                        with self.lock:
                            if not self.controls.empty():continue
                            self._emit(work_id,'session.idle_expired',[set_value('status','closing')])
                        break
                    if control=='close':break
                    if control=='stop':continue
                    if control!='run':continue
                    if self.stop_flag.is_set():
                        self._emit(work_id,'plan.paused',[set_value('status','paused')]);continue
                    if not self._execute_plan(work_id,console):break
            self._emit(work_id,'session.closed',[set_value('status','closed'),set_value('cleanup','confirmed')],{'scope':'console_and_connection_closed','remote_descendants':'not_certified'})
        except BaseException as exc:
            from opsfeast import connection_error
            error=connection_error(exc)
            if isinstance(exc,BaseExceptionGroup):error['causes']=[type(child).__name__ for child in exc.exceptions]
            delta=[set_value('status','failed'),set_value('cleanup','unknown'),set_value('last_error',error)]
            current=self.store.snapshot(work_id)['state'].get('current')
            if current:
                failed={**current,'status':'failed','finished_at':timestamp(),'error_type':type(exc).__name__,'termination_status':'unknown'}
                delta.extend([{'op':'append','path':['history'],'value':failed},set_value('current',None)])
            self._emit(work_id,'session.error',delta,{'error':error})
    def _execute_plan(self,work_id,console):
        while True:
            with self.lock:
                state=self.store.snapshot(work_id)['state'];plan=state['plan'];index=plan['next']
                if index>=len(plan['steps']):
                    self._emit(work_id,'plan.finished',[set_value('status','ready')]);return True
                if state['status'] in ('stop_requested','closing') or self.stop_flag.is_set():
                    self._emit(work_id,'plan.paused',[set_value('status','closing' if self.close_flag.is_set() else 'paused')]);return not self.close_flag.is_set()
                item=plan['steps'][index]
                current={**item,'index':index+1,'stdout':'','stderr':'','started_at':timestamp(),'status':'running','exitcode':None,'output_truncated':False}
                self._emit(work_id,'step.started',[set_value('current',current),set_value('status','running')])
                update=console.start_command(item['command'],timeout=item['timeout'])
            stopped=False;closing=False;interrupted=False
            while True:
                for field in ('stdout','stderr'):
                    chunk=getattr(update,field)
                    if chunk:
                        snap=self.store.snapshot(work_id)['state'];used=snap['output_bytes'];raw=chunk.encode();remaining=max(0,OUTPUT_LIMIT-used)
                        shown=raw[:remaining].decode('utf-8',errors='ignore')
                        if shown:self._emit(work_id,'output.append',[{'op':'append_text','path':['current',field],'value':shown},set_value('output_bytes',used+len(shown.encode()))],{'stream':field})
                        if len(raw)>remaining:
                            self._emit(work_id,'output.limit',[{'op':'set','path':['current','output_truncated'],'value':True}],{'limit':OUTPUT_LIMIT});stopped=True
                if update.state!='running':break
                try:control=self.controls.get(timeout=.08)
                except queue.Empty:control=None
                if not interrupted and (control in ('stop','close') or stopped or self.stop_flag.is_set()):
                    stopped=True;closing=control=='close' or self.close_flag.is_set();interrupted=True
                    self._emit(work_id,'stop.attempted',[],{'scope':'current_foreground_job'})
                    update=console.interrupt()
                else:update=console.poll()
            state=self.store.snapshot(work_id)['state'];finished=deepcopy(state['current'])
            finished.update(status=update.state,finished_at=timestamp(),exitcode=update.result.exitcode if update.result else None,stop_requested=stopped,error_type=update.error_type,session_reuse=update.session_reuse)
            if update.result:
                finished['result_evidence']={key:getattr(update.result,key) for key in ('termination_status','stop_reason','stdout_truncated','stderr_truncated') if hasattr(update.result,key)}
            plan=deepcopy(state['plan']);plan['next']=index+1
            next_status='paused' if stopped or item['checkpoint'] else 'awaiting_step' if plan['approval_mode']=='each' and plan['next']<len(plan['steps']) else 'running'
            if update.state!='completed':next_status='failed_step'
            if plan['next']>=len(plan['steps']) and next_status=='running':next_status='ready'
            self._emit(work_id,'step.finished',[{'op':'append','path':['history'],'value':finished},set_value('current',None),set_value('plan',plan),set_value('status',next_status)])
            if closing:return False
            if next_status!='running':return True
    def shutdown(self):
        self.shutting_down=True
        with self.lock:
            if self.worker and self.worker.is_alive():
                self.stop_flag.set();self.close_flag.set();self.controls.put('close')
        if self.worker:self.worker.join(timeout=3)
        if (not self.worker or not self.worker.is_alive()) and self.owner_fd is not None:
            os.close(self.owner_fd);self.owner_fd=None
