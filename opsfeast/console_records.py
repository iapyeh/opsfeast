"""Console blocks 0.2.0: bounded previews, byte-range content and human replies.

This stores evidence and decisions; it never executes commands or wakes a model.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

VERSION = '0.2.0'
BLOCK_LIMIT = 32 * 1024 * 1024
SESSION_LIMIT = 64 * 1024 * 1024
PREVIEW = 1024
KINDS = {'command', 'stdout', 'stderr', 'identity', 'analysis', 'authorization', 'error', 'status', 'form'}
FINISH = {'completed', 'failed', 'interrupted', 'cancelled'}

class RecordError(ValueError): pass

def now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

def identifier(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value: raise ValueError
    except (ValueError, AttributeError): raise RecordError('invalid_id') from None
    return value

def string(value, limit, empty=False):
    if not isinstance(value,str) or (not empty and not value.strip()) or '\x00' in value: raise RecordError('invalid_text')
    try:
        if len(value.encode())>limit: raise RecordError('text_too_large')
    except UnicodeError: raise RecordError('invalid_text') from None
    return value

def exact(body, keys):
    if not isinstance(body,dict) or set(body)!=set(keys.split()): raise RecordError('invalid_fields')

def time_value(value):
    try:
        dt=datetime.fromisoformat(value)
        if dt.tzinfo is None: raise ValueError
        return dt
    except (ValueError,TypeError): raise RecordError('invalid_time') from None

def form_schema(value):
    exact(value,'fields choices expires_at')
    if value['expires_at'] is not None: time_value(value['expires_at'])
    fields=value['fields']; choices=value['choices']
    if not isinstance(fields,list) or len(fields)>10 or not isinstance(choices,list) or not 1<=len(choices)<=4: raise RecordError('invalid_form')
    names=set()
    for field in fields:
        exact(field,'name label type required options')
        name=string(field['name'],50)
        if not name.isascii() or not name.replace('_','').isalnum() or name in names or name in ('__proto__','constructor','prototype'): raise RecordError('invalid_form')
        names.add(name); string(field['label'],200)
        if not isinstance(field['type'],str) or field['type'] not in ('text','textarea','select','checkbox') or type(field['required']) is not bool: raise RecordError('invalid_form')
        opts=field['options']
        if not isinstance(opts,list) or len(opts)>20: raise RecordError('invalid_form')
        for option in opts: string(option,200)
        if (field['type']=='select' and (not opts or len(set(opts))!=len(opts))) or (field['type']!='select' and opts): raise RecordError('invalid_form')
    ids=set()
    for choice in choices:
        exact(choice,'id label')
        cid=string(choice['id'],50); string(choice['label'],100)
        if cid in ids: raise RecordError('invalid_form')
        ids.add(cid)
    return value

class Records:
    def __init__(self,root):
        root=Path(root)
        if root.is_symlink(): raise RecordError('invalid_storage')
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
        # 0.1 data stays untouched; no compatibility reader or destructive migration.
        self.path=root/'console-blocks.sqlite3'
        if self.path.is_symlink(): raise RecordError('invalid_storage')
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS session(id TEXT PRIMARY KEY,metadata TEXT NOT NULL,seq INTEGER NOT NULL,bytes INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS block(session TEXT, id TEXT, position INTEGER, kind TEXT,title TEXT,status TEXT,revision INTEGER,content BLOB,lines INTEGER,form TEXT,response TEXT,created_at TEXT, PRIMARY KEY(session,id));
            CREATE TABLE IF NOT EXISTS event(session TEXT,seq INTEGER,stored TEXT,PRIMARY KEY(session,seq));
            CREATE TABLE IF NOT EXISTS request(session TEXT,id TEXT,digest TEXT,result TEXT,PRIMARY KEY(session,id));
            ''')
        os.chmod(self.path,0o600)
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            with db: yield db
        finally: db.close()
    def _session(self,db,sid):
        identifier(sid)
        row=db.execute('SELECT * FROM session WHERE id=?',(sid,)).fetchone()
        if not row: raise RecordError('unknown_session')
        return row
    def _block(self,db,sid,bid):
        identifier(bid)
        row=db.execute('SELECT kind,status,revision,form,length(content) AS size FROM block WHERE session=? AND id=?',(sid,bid)).fetchone()
        if not row: raise RecordError('unknown_block')
        return row
    def _summary(self,db,sid,bid):
        # Never load whole content while building a river snapshot/SSE event.
        row=db.execute('SELECT id,position,kind,title,status,revision,length(content) AS size,lines,form,response,created_at,substr(content,1,?) AS head,substr(content,max(?,length(content)-?+1),?) AS tail FROM block WHERE session=? AND id=?',(PREVIEW,PREVIEW+1,PREVIEW,PREVIEW,sid,bid)).fetchone()
        if not row: raise RecordError('unknown_block')
        result={key:row[key] for key in ('id','position','kind','title','status','revision','size','lines','created_at')}
        result.update(head=bytes(row['head'] or b'').decode(errors='ignore'),tail=bytes(row['tail'] or b'').decode(errors='ignore') if row['size']>PREVIEW else '',form=json.loads(row['form']) if row['form'] else None,response=json.loads(row['response']) if row['response'] else None)
        if result['form'] and result['form']['expires_at']:
            result['expired']=time_value(result['form']['expires_at'])<=datetime.now(timezone.utc)
        return result
    def create(self,body):
        exact(body,'session_id title host_id work_id')
        sid=identifier(body['session_id']);string(body['title'],500);string(body['host_id'],200)
        if body['work_id'] is not None:identifier(body['work_id'])
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT metadata FROM session WHERE id=?',(sid,)).fetchone()
            if prior:
                if any(json.loads(prior[0])[k]!=v for k,v in body.items()): raise RecordError('session_conflict')
            else:db.execute('INSERT INTO session VALUES(?,?,0,0)',(sid,json.dumps({**body,'created_at':now(),'evidence_source':'agent_reported'})))
        return self.snapshot(sid)
    def snapshot(self,sid):
        with self.db() as db:
            db.execute('BEGIN');row=self._session(db,sid)
            ids=db.execute('SELECT id FROM block WHERE session=? ORDER BY position',(sid,)).fetchall()
            blocks=[self._summary(db,sid,r[0]) for r in ids]
            return {'protocol_version':VERSION,'session':{**json.loads(row['metadata']),'bytes':row['bytes']},'seq':row['seq'],'blocks':blocks}
    def events(self,sid,after):
        with self.db() as db:
            row=self._session(db,sid)
            if type(after) is not int or not 0<=after<=row['seq']:raise RecordError('invalid_cursor')
            # Page all event types first; advance only over returned rows to avoid skipping responses.
            rows=db.execute('SELECT stored FROM event WHERE session=? AND seq>? ORDER BY seq LIMIT 100',(sid,after)).fetchall()
            return [json.loads(r[0]) for r in rows]
    def _emit(self,db,sid,kind,bid,extra=None):
        seq=self._session(db,sid)['seq']+1
        event={'seq':seq,'session_id':sid,'type':kind,'received_at':now(),'block':self._summary(db,sid,bid),**(extra or {})}
        db.execute('UPDATE session SET seq=? WHERE id=?',(seq,sid))
        db.execute('INSERT INTO event VALUES(?,?,?)',(sid,seq,json.dumps(event,ensure_ascii=False)))
        return {'accepted':True,'seq':seq,'block':event['block']}
    def _action(self,sid,request_id,action,body,callback,actor='writer'):
        identifier(request_id)
        try:digest=hashlib.sha256(json.dumps([action,body,actor],sort_keys=True,allow_nan=False).encode()).hexdigest()
        except (TypeError,ValueError,UnicodeError):raise RecordError('invalid_json') from None
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');self._session(db,sid)
            prior=db.execute('SELECT digest,result FROM request WHERE session=? AND id=?',(sid,request_id)).fetchone()
            if prior:
                if prior['digest']!=digest:raise RecordError('event_conflict')
                return json.loads(prior['result'])
            if self._session(db,sid)['seq']>=100000:raise RecordError('session_event_limit')
            result=callback(db)
            db.execute('INSERT INTO request VALUES(?,?,?,?)',(sid,request_id,digest,json.dumps(result)))
            return result
    def add_block(self,sid,body):
        exact(body,'event_id block_id kind title text form')
        bid=identifier(body['block_id']);kind=body['kind'];string(body['title'],500);string(body['text'],32768,True)
        if not isinstance(kind,str) or kind not in KINDS:raise RecordError('invalid_kind')
        form=body['form']
        if kind=='form':form_schema(form)
        elif form is not None:raise RecordError('unexpected_form')
        raw=body['text'].encode()
        def apply(db):
            if db.execute('SELECT 1 FROM block WHERE session=? AND id=?',(sid,bid)).fetchone():raise RecordError('block_exists')
            count=db.execute('SELECT count(*) FROM block WHERE session=?',(sid,)).fetchone()[0]
            if count>=2000:raise RecordError('block_count_limit')
            if self._session(db,sid)['bytes']+len(raw)>SESSION_LIMIT:raise RecordError('session_limit_reached')
            db.execute('INSERT INTO block VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(sid,bid,count+1,kind,body['title'],'waiting' if form else 'streaming',1,raw,raw.count(b'\n'),json.dumps(form) if form else None,None,now()))
            db.execute('UPDATE session SET bytes=bytes+? WHERE id=?',(len(raw),sid))
            return self._emit(db,sid,'block.created',bid)
        return self._action(sid,body['event_id'],'create_block',body,apply)
    def append(self,sid,bid,body):
        exact(body,'event_id offset text');string(body['text'],32768,True)
        if not body['text']:raise RecordError('invalid_text')
        if type(body['offset']) is not int or body['offset']<0:raise RecordError('invalid_offset')
        raw=body['text'].encode()
        def apply(db):
            row=self._block(db,sid,bid)
            if row['status']!='streaming':raise RecordError('block_not_streaming')
            if body['offset']!=row['size']:raise RecordError('offset_conflict')
            if row['size']+len(raw)>BLOCK_LIMIT:raise RecordError('block_limit_reached')
            if self._session(db,sid)['bytes']+len(raw)>SESSION_LIMIT:raise RecordError('session_limit_reached')
            db.execute('UPDATE block SET content=CAST(content || ? AS BLOB),lines=lines+?,revision=revision+1 WHERE session=? AND id=?',(raw,raw.count(b'\n'),sid,bid))
            db.execute('UPDATE session SET bytes=bytes+? WHERE id=?',(len(raw),sid))
            return self._emit(db,sid,'block.updated',bid,{'offset':body['offset'],'added_bytes':len(raw)})
        return self._action(sid,body['event_id'],'append:'+bid,body,apply)
    def finish(self,sid,bid,body):
        exact(body,'event_id status')
        if not isinstance(body['status'],str) or body['status'] not in FINISH:raise RecordError('invalid_status')
        def apply(db):
            row=self._block(db,sid,bid)
            if row['kind']=='form' and body['status']!='cancelled':raise RecordError('form_requires_response')
            if row['status'] not in ('streaming','waiting'):raise RecordError('block_already_finished')
            db.execute('UPDATE block SET status=?,revision=revision+1 WHERE session=? AND id=?',(body['status'],sid,bid))
            return self._emit(db,sid,'block.finished',bid)
        return self._action(sid,body['event_id'],'finish:'+bid,body,apply)
    def content(self,sid,bid,offset=0,limit=16384):
        if type(offset) is not int or offset<0 or type(limit) is not int or not 256<=limit<=32768:raise RecordError('invalid_range')
        with self.db() as db:
            db.execute('BEGIN');self._session(db,sid)
            row=db.execute('SELECT length(content) size,revision,status,substr(content,?,?) chunk FROM block WHERE session=? AND id=?',(offset+1,limit,sid,identifier(bid))).fetchone()
            if not row:raise RecordError('unknown_block')
            if offset>row['size']:raise RecordError('invalid_range')
            raw=bytes(row['chunk'] or b'')
            if raw and raw[0]&0xc0==0x80:raise RecordError('invalid_utf8_offset')
            text=raw.decode(errors='ignore');next_offset=offset+len(text.encode())
            return {'text':text,'offset':offset,'next_offset':next_offset,'total_bytes':row['size'],'revision':row['revision'],'status':row['status']}
    def respond(self,sid,bid,body,actor):
        exact(body,'event_id revision choice values');string(actor,100)
        if type(body['revision']) is not int or not isinstance(body['values'],dict):raise RecordError('invalid_response')
        def apply(db):
            row=self._block(db,sid,bid)
            if row['kind']!='form' or row['status']!='waiting':raise RecordError('form_not_waiting')
            if body['revision']!=row['revision']:raise RecordError('stale_form')
            form=json.loads(row['form'])
            if form['expires_at'] and time_value(form['expires_at'])<=datetime.now(timezone.utc):raise RecordError('form_expired')
            if body['choice'] not in [c['id'] for c in form['choices']]:raise RecordError('invalid_choice')
            values=body['values']
            if set(values)!=set(f['name'] for f in form['fields']):raise RecordError('invalid_response_fields')
            for field in form['fields']:
                v=values[field['name']]
                if field['type']=='checkbox':
                    if type(v) is not bool or (field['required'] and not v):raise RecordError('invalid_field_value')
                else:
                    string(v,2000,not field['required'])
                    if field['type']=='select' and v not in field['options']:raise RecordError('invalid_field_value')
            response={'response_id':body['event_id'],'choice':body['choice'],'values':values,'actor':actor,'authority':'administrator_cookie','received_at':now(),'request_revision':body['revision']}
            db.execute('UPDATE block SET response=?,status=?,revision=revision+1 WHERE session=? AND id=?',(json.dumps(response),'answered',sid,bid))
            return self._emit(db,sid,'response.created',bid,{'response':response})
        return self._action(sid,body['event_id'],'respond:'+bid,body,apply,actor='human:'+actor)
