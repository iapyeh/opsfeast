"""Administrator-only Profile lifecycle and private backup endpoints."""
from contextlib import nullcontext
import sqlite3
import zipfile
from fastapi import HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from opsfeast import ConfigError
from opsfeast import profile_settings, profile_transfer


def install(app, *, product, root, require_admin, json_body):
    def perform(function, **kwargs):
        runs = getattr(app.state,'recipe_runs',None)
        # Serialize against this Web controller's start/stop changes; never stop work.
        with runs.lock if runs else nullcontext():
            if runs and runs.active:
                raise HTTPException(409,'profile_management_requires_idle_recipes')
            try:return function(**kwargs)
            except (OSError,sqlite3.Error,zipfile.BadZipFile) as error:
                raise ConfigError('profile filesystem/database operation failed; existing data was not purged') from error

    @app.post('/api/v1/profiles/detach')
    async def detach(request: Request):
        require_admin(request);body=await json_body(request)
        if set(body)!={'name','expected_revision'}:raise HTTPException(422,'invalid_profile_request')
        return await run_in_threadpool(perform,profile_settings.detach,installation=product,**body)

    @app.post('/api/v1/profiles/delete')
    async def delete(request: Request):
        require_admin(request);body=await json_body(request)
        if set(body)!={'name','expected_revision','confirm_name'}:raise HTTPException(422,'invalid_profile_request')
        return await run_in_threadpool(perform,profile_transfer.delete,installation=product,data_root=root,**body)

    @app.post('/api/v1/profiles/export')
    async def export(request: Request):
        require_admin(request);body=await json_body(request)
        if set(body)!={'name','expected_revision'}:raise HTTPException(422,'invalid_profile_request')
        raw=await run_in_threadpool(perform,profile_transfer.export,installation=product,**body)
        return Response(raw,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="profile-backup.zip"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    @app.post('/api/v1/profiles/import')
    async def import_profile(request: Request,name: str,expected_revision: str):
        require_admin(request)
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>profile_transfer.MAX_ARCHIVE:raise HTTPException(413,'profile_archive_too_large')
        return await run_in_threadpool(perform,profile_transfer.import_archive,installation=product,data_root=root,raw=bytes(raw),name=name,expected_revision=expected_revision)
