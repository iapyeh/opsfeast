"""Local preview and capability-protected installation presentation settings."""
import hmac
import json
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from opsfeast import ConfigError
from opsfeast.identity import read_identity
from opsfeast import site, admin
from .security import Sessions, COOKIE, LIFETIME, EditingSessions, EDIT_COOKIE, EDIT_LIFETIME

WEB_ROOT = Path(__file__).resolve().parents[2] / 'web'
PAGES = ('/', '/setup', '/login', '/workspace', '/settings', '/settings/hosts', '/settings/recipes', '/settings/parameters', '/settings/retention', '/settings/site', '/settings/profiles', '/operations', '/hosts', '/recipes', '/retention', '/apps', '/learn', '/docs', '/work', '/logs', '/skills', '/recipes/data')


def create_app(installation=None, *, data_root=None, edit_token=None, interactive_options=None, console_options=None) -> FastAPI:
    """Local Web app; token bootstrap, administrator config writes, opt-in Console."""
    from opsfeast.storage import resolve_data_root
    root = resolve_data_root(WEB_ROOT.parent if installation is None else installation, data_root=data_root, required=True)
    product = WEB_ROOT.parent if installation is None else Path(installation).resolve(strict=True)
    sessions = Sessions()
    editing_sessions = EditingSessions()
    app = FastAPI(title='OpsFeast Web preview', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])

    @app.middleware('http')
    async def preview_headers(request, call_next):
        response = await call_next(request)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' blob:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(ConfigError)
    async def config_error(request, exc):
        # Public errors are typed; no paths, user values or exception strings.
        conflict = isinstance(exc, site.SiteConflict)
        credential_error = isinstance(exc, admin.InvalidCredentials)
        return JSONResponse(status_code=409 if conflict else 401 if credential_error else 422,
                            content={'detail': 'revision_conflict' if conflict else 'invalid_credentials' if credential_error else 'invalid_configuration'})

    def check_origin(request):
        origin = request.headers.get('origin')
        if origin is not None and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'same_origin_required')
        if request.headers.get('sec-fetch-site') == 'cross-site':
            raise HTTPException(403, 'same_origin_required')

    def local_capability(request):
        auth=request.headers.get('authorization','')
        return bool(edit_token and (hmac.compare_digest(auth.encode(),('Bearer '+edit_token).encode())
                                   or editing_sessions.valid(request.cookies.get(EDIT_COOKIE))))

    def authenticated(request):
        return sessions.authenticated(request.cookies.get(COOKIE),root)

    def require_admin(request):
        check_origin(request)
        if not authenticated(request): raise HTTPException(401,'administrator_login_required')

    def authorize(request):
        check_origin(request)
        if not local_capability(request) and not authenticated(request):
            raise HTTPException(401,'site_edit_token_or_login_required')

    @app.post('/api/v1/site/unlock')
    def unlock_site(request: Request):
        authorize(request)
        editing_sessions.revoke(request.cookies.get(EDIT_COOKIE))
        response=JSONResponse({'unlocked':True,'expires_in':EDIT_LIFETIME})
        response.set_cookie(EDIT_COOKIE,editing_sessions.issue(),httponly=True,samesite='strict',
                            secure=request.url.scheme=='https',path='/')
        return response

    @app.post('/api/v1/site/lock')
    def lock_site(request: Request):
        check_origin(request)
        editing_sessions.revoke(request.cookies.get(EDIT_COOKIE))
        response=JSONResponse({'unlocked':False})
        response.delete_cookie(EDIT_COOKIE,path='/')
        return response

    async def bounded_body(request, limit):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > limit:
                raise HTTPException(413, 'request_too_large')
        return bytes(data)

    async def landing(request: Request):
        protected = admin.status(root)['configured'] and request.url.path in ('/workspace','/operations','/hosts','/recipes','/retention','/apps','/work','/logs','/skills','/recipes/data')
        if protected and not authenticated(request):
            destination=request.url.path+('?' + request.url.query if request.url.query else '')
            return RedirectResponse('/login?next='+quote(destination,safe=''), status_code=303)
        return FileResponse(WEB_ROOT / 'index.html')
    for page in PAGES:
        app.add_api_route(page, landing, methods=['GET'], include_in_schema=False)

    @app.get('/api/v1/preview')
    async def preview_status():
        return {'mode': 'preview', 'data_source': 'installation_presentation',
                'authentication': 'single_administrator', 'site_edit_authentication': 'local_capability_or_administrator_session',
                'operations_enabled': bool(interactive_options), 'interactive_enabled': bool(interactive_options), 'profile_configuration_enabled': True}

    async def json_body(request, limit=8192):
        if request.headers.get('content-type','').split(';')[0] != 'application/json':
            raise HTTPException(415,'json_required')
        try:
            value=json.loads(await bounded_body(request,limit))
        except (ValueError,UnicodeError):raise HTTPException(422,'invalid_json') from None
        if not isinstance(value,dict):raise HTTPException(422,'object_required')
        return value

    from .interactive_api import install
    install(app,root=root,product=product,web_root=WEB_ROOT,options=interactive_options,
            check_origin=check_origin,authenticated=authenticated,json_body=json_body)

    from .console_api import install as install_console_records
    install_console_records(app,root=root,web_root=WEB_ROOT,options=console_options,
                            check_origin=check_origin,authenticated=authenticated,json_body=json_body)

    from .host_api import install as install_hosts
    install_hosts(app,product=product,require_admin=require_admin,json_body=json_body)

    @app.get('/api/v1/auth/status')
    def auth_status(request: Request):
        state=admin.status(root)
        signed_in=authenticated(request)
        return {'configured':state['configured'],'authenticated':signed_in,
                'username':state['username'] if signed_in else None}

    @app.get('/api/v1/setup')
    def setup_status(request: Request):
        check_origin(request)
        return {'schema_version':'0.1.0','admin_configured':admin.status(root)['configured'],
                'authenticated':authenticated(request),'edit_unlocked':local_capability(request),
                'local_unlock_available':bool(edit_token)}

    @app.post('/api/v1/auth/login')
    async def login(request: Request):
        check_origin(request)
        body=await json_body(request)
        if set(body)!={'username','password'}:raise HTTPException(422,'invalid_login_request')
        if not sessions.allow_login():raise HTTPException(429,'login_rate_limited')
        from starlette.concurrency import run_in_threadpool
        before=admin.status(root)
        if not await run_in_threadpool(admin.verify,root,body['username'],body['password']):
            raise HTTPException(401,'invalid_credentials')
        if admin.status(root)['revision'] != before['revision']:
            raise HTTPException(401,'invalid_credentials')
        token=sessions.issue(before['revision'])
        response=JSONResponse({'authenticated':True})
        response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=LIFETIME,path='/')
        return response

    @app.post('/api/v1/auth/logout')
    def logout(request: Request):
        check_origin(request)
        sessions.revoke(request.cookies.get(COOKIE))
        editing_sessions.revoke(request.cookies.get(EDIT_COOKIE))
        response=JSONResponse({'authenticated':False})
        response.delete_cookie(COOKIE,path='/')
        response.delete_cookie(EDIT_COOKIE,path='/')
        return response

    @app.get('/api/v1/admin')
    def administrator(request: Request):
        if not (not admin.status(root)['configured'] and local_capability(request)):
            require_admin(request)
        return admin.status(root)

    @app.post('/api/v1/admin/bootstrap')
    async def bootstrap(request: Request):
        check_origin(request)
        if not local_capability(request):raise HTTPException(401,'local_bootstrap_capability_required')
        if admin.status(root)['configured']:raise HTTPException(409,'administrator_already_configured')
        body=await json_body(request)
        if set(body)!={'username','password','expected_revision'}:raise HTTPException(422,'invalid_admin_request')
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(admin.configure,root,**body)

    @app.put('/api/v1/admin')
    async def update_administrator(request: Request):
        require_admin(request)
        body=await json_body(request)
        if set(body)!={'username','password','current_password','expected_revision'}:raise HTTPException(422,'invalid_admin_request')
        from starlette.concurrency import run_in_threadpool
        result=await run_in_threadpool(admin.configure,root,**body)
        sessions.clear()
        response=JSONResponse(result);response.delete_cookie(COOKIE,path='/')
        return response

    @app.get('/api/v1/profiles')
    def profiles_status(request: Request):
        require_admin(request)
        from opsfeast.profile_settings import inspect
        return inspect(product)

    @app.post('/api/v1/profiles')
    async def create_profile(request: Request):
        require_admin(request)
        body=await json_body(request)
        if set(body)!={'name','namespace','expected_revision'}:raise HTTPException(422,'invalid_profile_request')
        from opsfeast.profile_settings import create
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(create,product,root,**body)

    @app.put('/api/v1/profiles/default')
    async def switch_profile(request: Request):
        require_admin(request)
        body=await json_body(request)
        if set(body)!={'name','expected_revision'}:raise HTTPException(422,'invalid_profile_request')
        from opsfeast.profile_settings import use
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(use,product,**body)

    @app.post('/api/v1/profiles/attach')
    async def attach_profile(request: Request):
        require_admin(request)
        body=await json_body(request)
        if set(body)!={'name','root','expected_revision'}:raise HTTPException(422,'invalid_profile_request')
        from opsfeast.profile_settings import attach
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(attach,product,**body)

    @app.get('/api/v1/settings/catalog')
    def settings_catalog():
        from opsfeast.settings import catalog
        return catalog()

    @app.get('/api/v1/site')
    def public_settings():
        return site.public_site(root)

    @app.get('/api/v1/site/settings')
    def private_settings(request: Request):
        authorize(request)
        identity = read_identity(root)
        return {'site': site.read_site(root), 'identity': {key: identity[key] for key in ('id', 'name', 'description', 'identity_status')}}

    @app.put('/api/v1/site/settings')
    async def update_settings(request: Request):
        authorize(request)
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise HTTPException(415, 'json_required')
        try:
            payload = json.loads(await bounded_body(request, 8192))
        except (ValueError, UnicodeError):
            raise HTTPException(422, 'invalid_json') from None
        if not isinstance(payload, dict) or set(payload) != {'settings', 'expected_revision'}:
            raise HTTPException(422, 'invalid_site_request')
        # Sync image/storage operations are dispatched off the event loop.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(site.save_site, root, payload['settings'], expected_revision=payload['expected_revision'])

    @app.post('/api/v1/site/images')
    async def upload(request: Request):
        authorize(request)
        if request.headers.get('content-type') not in ('image/png', 'image/jpeg'):
            raise HTTPException(415, 'png_or_jpeg_required')
        content = await bounded_body(request, site.MAX_UPLOAD)
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(site.upload_image, root, content)

    @app.get('/site-assets/{asset_id}')
    def site_image(asset_id: str):
        try:
            path = site.image_path(root, asset_id)
        except ConfigError:
            raise HTTPException(404, 'site_asset_unavailable') from None
        return FileResponse(path, media_type='image/png')

    app.mount('/assets', StaticFiles(directory=WEB_ROOT / 'assets'), name='assets')
    return app
