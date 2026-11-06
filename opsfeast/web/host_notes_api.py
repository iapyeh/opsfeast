"""Administrator-only host notes adapter over the shared local service."""
from fastapi import Request, HTTPException, Query
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from opsfeast.host_notes import HostNotesError, inspect, mutate


def install(app, *, product, require_admin, json_body, agent_authorized):
    @app.exception_handler(HostNotesError)
    async def error(request, exc):
        status = 409 if exc.code == 'note_revision_conflict' else 404 if exc.code in ('host_not_found', 'note_not_found') else 422
        return JSONResponse({'detail': exc.code}, status_code=status)

    @app.get('/api/v1/host-notes')
    def notes(request: Request, profile: str, host_id: str, query: str = '', recipe_reference: str | None = None,
              tags: list[str] | None = Query(default=None, alias='tag'), include_general: bool = False):
        require_admin(request)
        try:
            return inspect(product, profile=profile, host_id=host_id, query=query,recipe_reference=recipe_reference,tags=tags,include_general=include_general)
        except OSError:
            raise HTTPException(422, 'note_storage_unavailable') from None

    async def write(request, action):
        require_admin(request)
        body = await json_body(request, 131072)
        expected = {'profile', 'host_id', 'expected_revision'}
        if action != 'create':
            expected.add('note_uuid')
        if action != 'delete':
            expected.add('changes')
        if action in ('delete', 'merge'):
            expected.add('confirmation')
        if action == 'merge':
            expected.add('remove')
        if set(body) != expected:
            raise HTTPException(422, 'invalid_note_request')
        # Derive provenance from authentication, never from submitted source.
        if action != 'delete':
            if not isinstance(body['changes'], dict):
                raise HTTPException(422, 'invalid_note_input')
            body['changes'] = dict(body['changes'], source='agent' if agent_authorized(request) else 'user')
        try:
            return await run_in_threadpool(mutate, product, action=action, **body)
        except OSError:
            raise HTTPException(422, 'note_storage_unavailable') from None

    @app.post('/api/v1/host-notes')
    async def create(request: Request): return await write(request, 'create')

    @app.patch('/api/v1/host-notes')
    async def update(request: Request): return await write(request, 'update')

    @app.delete('/api/v1/host-notes')
    async def delete(request: Request): return await write(request, 'delete')

    @app.post('/api/v1/host-notes/merge')
    async def merge(request: Request): return await write(request, 'merge')
