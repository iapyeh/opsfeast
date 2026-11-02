"""Administrator-only host settings adapter; no SSH or recipe execution."""
from fastapi import Request,HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from opsfeast.host_settings import HostSettingsError,inspect,mutate


def install(app,*,product,require_admin,json_body):
    @app.exception_handler(HostSettingsError)
    async def error(request,exc):
        status=404 if exc.code=='host_not_found' else 409 if exc.code in ('host_already_exists','host_is_jump_dependency') else 422
        return JSONResponse({'detail':exc.code},status_code=status)

    @app.get('/api/v1/hosts')
    def list_hosts(request:Request,profile:str):
        require_admin(request)
        try:return inspect(product,profile=profile)
        except OSError:raise HTTPException(422,'host_storage_unavailable') from None

    async def write(request,action):
        require_admin(request)
        body=await json_body(request,65536)
        expected={'profile','host_id','expected_revision'}|({'confirmation'} if action=='delete' else {'changes'})
        if set(body)!=expected:raise HTTPException(422,'invalid_host_request')
        try:return await run_in_threadpool(mutate,product,action=action,**body)
        except OSError:raise HTTPException(422,'host_storage_unavailable') from None
        except ImportError:raise HTTPException(503,'host_writer_dependency_missing') from None

    @app.post('/api/v1/hosts')
    async def create_host(request:Request):return await write(request,'create')

    @app.patch('/api/v1/hosts')
    async def update_host(request:Request):return await write(request,'update')

    @app.delete('/api/v1/hosts')
    async def delete_host(request:Request):return await write(request,'delete')
