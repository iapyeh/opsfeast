"""Console block HTTP/SSE and administrator-authenticated response transport."""
import asyncio
import hmac
import json
import time
from urllib.parse import quote
from fastapi import Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from opsfeast import admin
from opsfeast.console_records import Records, RecordError

def install(app, *, root, web_root, options, check_origin, authenticated, json_body):
    records=Records(root/'console-records');app.state.console_records=records
    def authorize(request,write=False):
        check_origin(request)
        if authenticated(request):return
        supplied=request.headers.get('authorization','').encode()
        for role in (('writer',) if write else ('writer','reader')):
            expected=('Bearer '+options[role+'_token']).encode() if options else b''
            if expected and hmac.compare_digest(supplied,expected):return
        raise HTTPException(401,'console_writer_required' if write else 'administrator_login_required')
    def page(request,filename):
        check_origin(request)
        if not authenticated(request):return RedirectResponse('/login?next='+quote(request.url.path,safe=''),status_code=303)
        return FileResponse(web_root/filename)
    @app.exception_handler(RecordError)
    async def error(request,exc):
        return JSONResponse({'detail':str(exc)},status_code=404 if str(exc) in ('unknown_session','unknown_block') else 409)
    @app.get('/console/{session_id}')
    def reader(session_id:str,request:Request):return page(request,'console.html')
    @app.get('/console/{session_id}/blocks/{block_id}')
    def block_page(session_id:str,block_id:str,request:Request):return page(request,'console-block.html')
    @app.post('/api/v1/console-sessions')
    async def create(request:Request):
        authorize(request,True)
        result=await run_in_threadpool(records.create,await json_body(request,4096))
        return {**result,'reader_url':'/console/'+result['session']['session_id']}
    @app.get('/api/v1/console-sessions/{session_id}')
    async def snapshot(session_id:str,request:Request):
        authorize(request);return await run_in_threadpool(records.snapshot,session_id)
    @app.post('/api/v1/console-sessions/{session_id}/blocks')
    async def add(session_id:str,request:Request):
        authorize(request,True);return await run_in_threadpool(records.add_block,session_id,await json_body(request,65536))
    @app.post('/api/v1/console-sessions/{session_id}/blocks/{block_id}/append')
    async def append(session_id:str,block_id:str,request:Request):
        authorize(request,True);return await run_in_threadpool(records.append,session_id,block_id,await json_body(request,65536))
    @app.post('/api/v1/console-sessions/{session_id}/blocks/{block_id}/finish')
    async def finish(session_id:str,block_id:str,request:Request):
        authorize(request,True);return await run_in_threadpool(records.finish,session_id,block_id,await json_body(request,4096))
    @app.get('/api/v1/console-sessions/{session_id}/blocks/{block_id}/content')
    async def content(session_id:str,block_id:str,request:Request,offset:int=0,limit:int=16384):
        authorize(request);return await run_in_threadpool(records.content,session_id,block_id,offset,limit)
    @app.post('/api/v1/console-sessions/{session_id}/blocks/{block_id}/responses')
    async def respond(session_id:str,block_id:str,request:Request):
        check_origin(request)
        if not authenticated(request):raise HTTPException(401,'administrator_login_required')
        actor=admin.status(root)['username']
        return await run_in_threadpool(records.respond,session_id,block_id,await json_body(request,32768),actor)
    @app.get('/api/v1/console-sessions/{session_id}/responses')
    async def responses(session_id:str,request:Request,after:int=0,wait:int=0):
        authorize(request)
        if not 0<=wait<=25:raise HTTPException(422,'invalid_wait')
        cursor=after;deadline=time.monotonic()+wait
        while True:
            authorize(request)
            batch=await run_in_threadpool(records.events,session_id,cursor)
            if batch:cursor=batch[-1]['seq']
            replies=[event for event in batch if event['type']=='response.created']
            if replies or (time.monotonic()>=deadline and len(batch)<100):return {'seq':cursor,'responses':replies}
            if await request.is_disconnected():return {'seq':cursor,'responses':[]}
            if len(batch)<100:await asyncio.sleep(.2)
    @app.get('/api/v1/console-sessions/{session_id}/stream')
    async def stream(session_id:str,request:Request,after:int=0):
        authorize(request);await run_in_threadpool(records.events,session_id,after)
        async def generate():
            cursor=after;heartbeat=0
            while not await request.is_disconnected():
                try:authorize(request)
                except HTTPException:return
                batch=await run_in_threadpool(records.events,session_id,cursor)
                for event in batch:
                    cursor=event['seq']
                    yield f'id: {cursor}\ndata: '+json.dumps(event,ensure_ascii=False)+'\n\n'
                heartbeat+=1
                if heartbeat>=40:yield ': heartbeat\n\n';heartbeat=0
                if len(batch)<100:await asyncio.sleep(.25)
        return StreamingResponse(generate(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})
