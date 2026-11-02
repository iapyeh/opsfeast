"""Authenticated HTTP/SSE adapter for the versioned interactive work service."""
import asyncio
import hmac
import json
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from opsfeast.interactive import InteractiveError, Service


def install(app,*,root,product,web_root,options,check_origin,authenticated,json_body):
    service=Service(root/'interactive',product,targets=options['targets']) if options else None
    app.state.interactive=service
    def role(request):
        check_origin(request)
        supplied=request.headers.get('authorization','').encode()
        if authenticated(request):return 'operator'
        for name in ('operator','agent'):
            expected=('Bearer '+options[name+'_token']).encode() if options else b''
            if expected and hmac.compare_digest(supplied,expected):return name
        raise HTTPException(401,'interactive_credential_required')
    def available():
        if not service:raise HTTPException(503,'interactive_not_enabled')
    def scoped_snapshot(work_id):
        snap=service.store.snapshot(work_id)
        state=snap['state']
        if (state['profile'],state['host_id']) not in service.targets:raise HTTPException(403,'target_not_enabled')
        return snap
    @app.exception_handler(InteractiveError)
    async def interactive_error(request,exc):return JSONResponse({'detail':exc.code},status_code=404 if exc.code=='unknown_work' else 403 if exc.code=='operator_required' else 409)
    @app.get('/interactive')
    async def page():return FileResponse(web_root/'interactive.html')
    @app.get('/api/v1/interactive')
    def status(request:Request):
        available();actor=role(request)
        return {'protocol_version':'0.1.0','role':actor,'targets':[{'profile':p,'host_id':h} for p,h in sorted(service.targets)],'works':[work for work in service.store.list() if (work['profile'],work['host_id']) in service.targets]}
    @app.post('/api/v1/interactive')
    async def create(request:Request):
        available();actor=role(request)
        body=await json_body(request)
        if set(body)!={'profile','host_id','goal'}:raise HTTPException(422,'invalid_create_request')
        if actor!='operator':raise HTTPException(403,'operator_required')
        work_id=await run_in_threadpool(service.create,body['profile'],body['host_id'],body['goal'])
        return service.store.snapshot(work_id)
    @app.get('/api/v1/interactive/{work_id}')
    def snapshot(work_id:str,request:Request):
        available();role(request);return scoped_snapshot(work_id)
    @app.get('/api/v1/interactive/{work_id}/events')
    async def events(work_id:str,request:Request,after:int=0):
        available();role(request)
        snap=scoped_snapshot(work_id)
        if after<0 or after>snap['seq']:raise HTTPException(409,'invalid_event_cursor')
        async def stream():
            cursor=after;heartbeat=0
            while not await request.is_disconnected():
                # Revalidate cookies/capabilities for long-running readers.
                try:role(request)
                except HTTPException:return
                batch=await run_in_threadpool(service.store.events,work_id,cursor)
                for event in batch:
                    cursor=event['seq']
                    yield f'id: {cursor}\nevent: delta\ndata: '+json.dumps(event,ensure_ascii=False)+'\n\n'
                heartbeat+=1
                if heartbeat>=40:yield ': heartbeat\n\n';heartbeat=0
                await asyncio.sleep(.25)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})
    @app.post('/api/v1/interactive/{work_id}/{action}')
    async def action(work_id:str,action:str,request:Request):
        available();actor=role(request)
        body=await json_body(request,65536)
        return await run_in_threadpool(service.action,work_id,action,body,role=actor)
