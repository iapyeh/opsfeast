"""Authenticated recipe selection, review, execution and saved receipts."""
from fastapi import HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response

from opsfeast.core import Instance
from opsfeast.recipe_runs import RecipeRuns, RecipeRunError


def install(app, *, product, root, require_admin, json_body):
    runs = RecipeRuns(product, root)
    app.state.recipe_runs = runs
    @app.get('/api/v1/recipe-execution/settings')
    def execution_defaults(request: Request):
        require_admin(request)
        from opsfeast.execution_settings import inspect
        return inspect(root)

    @app.put('/api/v1/recipe-execution/settings')
    async def save_execution_defaults(request: Request):
        require_admin(request)
        body = await json_body(request, 8192)
        if set(body) != {'threads', 'expected_revision'}:
            raise HTTPException(422, 'invalid_execution_settings')
        from opsfeast.execution_settings import save
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(save, root, **body)
    from opsfeast.menu_preferences import MenuError
    @app.exception_handler(MenuError)
    async def menu_error(request,exc):
        return JSONResponse(status_code=422,content={'detail':str(exc)})
    from opsfeast.report_view import ArtifactError
    @app.exception_handler(ArtifactError)
    async def artifact_error(request, exc):
        return JSONResponse(status_code=422, content={'detail':str(exc)})
    @app.exception_handler(RecipeRunError)
    async def selection_error(request, exc):
        return JSONResponse(status_code=409 if str(exc) in ('recipe_selection_already_running', 'recipe_preview_changed_review_again', 'recipe_preview_expired') else 422,
                            content={'detail': str(exc)})
    from contextlib import asynccontextmanager
    previous = app.router.lifespan_context
    @asynccontextmanager
    async def lifecycle(application):
        async with previous(application) as state:
            try:
                yield state
            finally:
                from starlette.concurrency import run_in_threadpool
                await run_in_threadpool(runs.close)
    app.router.lifespan_context = lifecycle

    @app.get('/api/v1/recipe-menu')
    def menu(request: Request, profile: str | None = None):
        require_admin(request)
        from opsfeast.recipe_menu import menu as describe
        selected = Instance.open(product).profile(profile) if profile else None
        result = describe(selected)
        if selected:
            result['hosts'] = [{'host_id': name, 'title': value.get('label') or name,
                                'enabled': value.get('enabled', True)}
                               for name, value in selected.hosts.list().items()]
            result['groups'] = [{'id': name, 'title': value.get('label') or name, 'host_ids': value['hosts']}
                                for name, value in selected.hosts.groups().items()]
        else:
            result['hosts'] = []
            result['groups'] = []
        return result

    @app.post('/api/v1/recipe-menu/preferences')
    async def preferences(request: Request):
        require_admin(request)
        body=await json_body(request,65536)
        if set(body)!={'profile','expected_revision','action','changes'}:raise HTTPException(422,'invalid_menu_mutation')
        from opsfeast.menu_preferences import mutate
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(mutate,product,**body)

    @app.get('/api/v1/recipe-detail')
    def detail(request: Request,profile: str,reference: str,offset: int=Query(0,ge=0),limit: int=Query(5,ge=1,le=20),host: str|None=None):
        require_admin(request)
        from opsfeast.recipe_detail import inspect
        return inspect(product,profile=profile,reference=reference,offset=offset,limit=limit,host=host)

    @app.post('/api/v1/recipe-detail/defaults')
    async def defaults(request: Request):
        require_admin(request)
        body=await json_body(request,65536)
        if set(body)!={'profile','reference','expected_revision','changes','remove'}:raise HTTPException(422,'invalid_recipe_default_mutation')
        from opsfeast.recipe_defaults import update
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(update,product,**body)

    @app.get('/api/v1/recipe-detail/record')
    def detail_record(request: Request,profile: str,reference: str,record_id: str,download: bool=False):
        require_admin(request)
        from opsfeast.recipe_detail import record
        content=record(product,profile=profile,reference=reference,record_id=record_id)
        headers={'Content-Disposition':'attachment; filename=retention-record.json'} if download else {}
        return Response(content,media_type='application/json',headers=headers)

    @app.get('/api/v1/reports')
    def reports(request: Request, profile: str, offset: int=Query(0, ge=0), limit: int=Query(50, ge=1, le=100)):
        require_admin(request)
        from opsfeast.report_view import list_reports
        return list_reports(Instance.open(product).profile(profile), offset=offset, limit=limit)

    @app.get('/api/v1/reports/result')
    def report(request: Request, profile: str, result_id: str):
        require_admin(request)
        from opsfeast.report_view import show_report
        return show_report(Instance.open(product).profile(profile), result_id)

    @app.get('/api/v1/reports/artifact')
    def artifact(request: Request, profile: str, result_id: str, name: str, mode: str='text'):
        require_admin(request)
        if mode not in ('text','preview','download'):
            raise HTTPException(422, 'invalid_artifact_mode')
        from opsfeast.report_view import read_artifact, static_html, PREVIEW_CSP
        from pathlib import Path
        from urllib.parse import quote
        info, content = read_artifact(Instance.open(product).profile(profile), result_id, name)
        if mode == 'download':
            return Response(content, media_type='application/octet-stream', headers={
                'Content-Disposition':"attachment; filename=artifact; filename*=UTF-8''"+quote(Path(name).name, safe='')})
        if mode == 'text':
            try: text = content.decode('utf-8')
            except UnicodeError: raise HTTPException(422,'artifact_is_not_readable_utf8') from None
            return {**info, 'content':text}
        if info['media_type'] == 'text/html':
            return Response(static_html(content), media_type='text/html', headers={'Content-Security-Policy':PREVIEW_CSP})
        if info['media_type'] in ('image/png','image/jpeg','image/gif','image/webp'):
            return Response(content, media_type=info['media_type'])
        raise HTTPException(422,'artifact_preview_requires_html_or_raster_image')

    @app.post('/api/v1/recipe-runs/preview')
    async def preview(request: Request):
        require_admin(request)
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(runs.preview, await json_body(request, 65536))

    @app.post('/api/v1/recipe-runs')
    async def start(request: Request):
        require_admin(request)
        body = await json_body(request)
        if set(body)-{'threads'} != {'preview_id', 'confirmed'}:
            raise HTTPException(422, 'invalid_recipe_confirmation')
        from starlette.concurrency import run_in_threadpool
        if 'threads' in body:
            from opsfeast.execution_settings import validate_threads
            from opsfeast import ConfigError
            try:validate_threads(body['threads'])
            except ConfigError:raise RecipeRunError('invalid_recipe_threads') from None
        return await run_in_threadpool(runs.start, body['preview_id'], body['confirmed'], threads=body.get('threads'))

    @app.get('/api/v1/recipe-runs')
    def listing(request: Request, profile: str):
        require_admin(request)
        Instance.open(product).profile(profile)
        return runs.list(profile)

    @app.get('/api/v1/recipe-runs/{identifier}')
    def show(identifier: str, request: Request, profile: str):
        require_admin(request)
        Instance.open(product).profile(profile)
        return runs.show(identifier, profile)

    @app.post('/api/v1/recipe-runs/{identifier}/stop')
    async def stop(identifier: str, request: Request):
        require_admin(request)
        body = await json_body(request)
        if set(body) != {'profile'} or not isinstance(body['profile'], str):
            raise HTTPException(422, 'explicit_profile_required')
        Instance.open(product).profile(body['profile'])
        return runs.stop(identifier, body['profile'])
