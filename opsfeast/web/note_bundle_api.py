"""Authenticated document bundle adapters; active content never shares app origin."""
import base64
import binascii
from html import escape
import io
from urllib.parse import quote, urlencode, urlsplit

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from starlette.concurrency import run_in_threadpool
from opsfeast import note_bundles as bundles


def markdown_preview(product,scope):
    from markdown_it import MarkdownIt
    state=bundles.inspect(product,**scope);entry=state['bundle']['entry']
    if state['bundle']['kind']!='markdown':bundles.fail('markdown_bundle_required')
    source=bundles.read_file(product,**scope,path=entry).decode('utf-8')
    parser=MarkdownIt('commonmark',{'html':False}).enable(['table','strikethrough'])
    tokens=parser.parse(source);warnings=[];known={f['path'] for f in state['files']}
    def walk(items):
        for token in items:
            if token.type in ('image','link_open'):
                key='src' if token.type=='image' else 'href';url=token.attrGet(key) or ''
                try:
                    if token.type=='link_open' and url.startswith('#'):pass
                    elif token.type=='link_open' and urlsplit(url).scheme in ('http','https'):
                        token.attrSet('target','_blank');token.attrSet('rel','noopener noreferrer')
                    else:
                        path,fragment=bundles.relative_path(entry,url)
                        if path not in known:bundles.fail('bundle_file_not_found')
                        query=urlencode({**scope,'path':path})
                        if token.type=='image':
                            raw=bundles.read_file(product,**scope,path=path);image_type(raw)
                            token.attrSet('src','/api/v1/note-bundles/image?'+query)
                        else:
                            # Bundle-local links download; never execute HTML on app origin.
                            token.attrSet('href','/api/v1/note-bundles/file?'+query)
                            token.attrSet('download','')
                except (ValueError,OSError):
                    warnings.append({'reference':url,'reason':'unavailable_or_blocked'})
                    if token.type=='image':token.type='text';token.tag='';token.content='[圖片未載入：'+token.content+']';token.children=None;token.attrs={}
                    else:token.attrSet('href','#');token.attrSet('title','連結未提供或不允許')
            if token.children:walk(token.children)
    walk(tokens)
    return {'schema_version':'0.1.0','html':parser.renderer.render(tokens,parser.options,{}),'warnings':warnings,'bundle':state['bundle']}


def image_type(raw):
    from PIL import Image
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('PNG','JPEG','GIF','WEBP') or image.width*image.height>20_000_000:raise ValueError()
            image.verify();return {'PNG':'image/png','JPEG':'image/jpeg','GIF':'image/gif','WEBP':'image/webp'}[image.format]
    except Exception:bundles.fail('unsupported_bundle_image')


def install(app,*,product,require_admin,json_body,bounded_body,authenticated,preview):
    @app.exception_handler(bundles.BundleError)
    async def error(request,exc):
        status=404 if exc.code in ('bundle_not_found','note_not_found','bundle_file_not_found') else 409 if exc.code=='note_revision_conflict' else 422
        return JSONResponse({'detail':exc.code},status_code=status)

    def local_read(operation,*args,**kwargs):
        try:return operation(*args,**kwargs)
        except OSError:raise HTTPException(422,'bundle_storage_unavailable') from None

    def scope(profile,host_id,note_uuid,bundle_uuid):return dict(profile=profile,host_id=host_id,note_uuid=note_uuid,bundle_uuid=bundle_uuid)

    @app.post('/api/v1/note-bundles')
    async def upload(request:Request,profile:str,host_id:str,note_uuid:str,expected_revision:str,title:str,entry:str):
        require_admin(request)
        kwargs=dict(profile=profile,host_id=host_id,note_uuid=note_uuid,expected_revision=expected_revision,title=title,entry=entry)
        kind=request.headers.get('content-type','').split(';')[0]
        if kind=='application/zip':kwargs['archive']=await bounded_body(request,bundles.MAX_ARCHIVE)
        elif kind=='application/json':
            body=await json_body(request,90*1024*1024)
            if set(body)!={'files'} or not isinstance(body['files'],list) or not 1<=len(body['files'])<=bundles.MAX_FILES:raise HTTPException(422,'invalid_bundle_request')
            files={}
            try:
                for item in body['files']:
                    if not isinstance(item,dict) or set(item)!={'path','base64'} or item['path'] in files:raise ValueError()
                    bundles.safe_path(item['path'])
                    files[item['path']]=base64.b64decode(item['base64'],validate=True)
            except (ValueError,TypeError,binascii.Error):raise HTTPException(422,'invalid_bundle_request') from None
            kwargs['files']=files
        else:raise HTTPException(415,'zip_or_json_required')
        try:return await run_in_threadpool(bundles.create,product,**kwargs)
        except OSError:raise HTTPException(422,'bundle_storage_unavailable') from None

    @app.get('/api/v1/note-bundles')
    def metadata(request:Request,profile:str,host_id:str,note_uuid:str,bundle_uuid:str):
        require_admin(request);return local_read(bundles.inspect,product,**scope(profile,host_id,note_uuid,bundle_uuid))

    @app.delete('/api/v1/note-bundles')
    async def remove(request:Request):
        require_admin(request);body=await json_body(request)
        if set(body)!={'profile','host_id','note_uuid','bundle_uuid','expected_revision','confirmation'}:raise HTTPException(422,'invalid_bundle_request')
        try:return await run_in_threadpool(bundles.delete,product,**body)
        except OSError:raise HTTPException(422,'bundle_storage_unavailable') from None

    @app.get('/api/v1/note-bundles/export')
    def export(request:Request,profile:str,host_id:str,note_uuid:str,bundle_uuid:str):
        require_admin(request)
        raw=local_read(bundles.export,product,**scope(profile,host_id,note_uuid,bundle_uuid))
        return Response(raw,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="document-{bundle_uuid}.zip"'})

    @app.get('/api/v1/note-bundles/file')
    def file(request:Request,profile:str,host_id:str,note_uuid:str,bundle_uuid:str,path:str):
        require_admin(request);raw=local_read(bundles.read_file,product,**scope(profile,host_id,note_uuid,bundle_uuid),path=path)
        name=quote(path.rsplit('/',1)[-1],safe='')
        return Response(raw,media_type='application/octet-stream',headers={'Content-Disposition':f"attachment; filename*=UTF-8''{name}"})

    @app.get('/api/v1/note-bundles/image')
    def image(request:Request,profile:str,host_id:str,note_uuid:str,bundle_uuid:str,path:str):
        require_admin(request);raw=local_read(bundles.read_file,product,**scope(profile,host_id,note_uuid,bundle_uuid),path=path)
        return Response(raw,media_type=image_type(raw))

    @app.get('/api/v1/note-bundles/markdown')
    def markdown(request:Request,profile:str,host_id:str,note_uuid:str,bundle_uuid:str):
        require_admin(request);return local_read(markdown_preview,product,scope(profile,host_id,note_uuid,bundle_uuid))

    @app.post('/api/v1/note-bundles/preview')
    async def interactive(request:Request):
        require_admin(request);body=await json_body(request)
        if set(body)!={'profile','host_id','note_uuid','bundle_uuid'}:raise HTTPException(422,'invalid_bundle_request')
        try:return await run_in_threadpool(preview.issue,body)
        except OSError:raise HTTPException(503,'isolated_preview_unavailable') from None

    @app.get('/note-attachments')
    def reader(request:Request,profile:str,host_id:str,note_uuid:str,bundle_uuid:str):
        if not authenticated(request):
            return RedirectResponse('/login?'+urlencode({'next':str(request.url.path)+'?'+str(request.url.query)}),status_code=303)
        selected_scope=scope(profile,host_id,note_uuid,bundle_uuid)
        state=local_read(bundles.inspect,product,**selected_scope)
        origin=''
        if state['bundle']['kind']=='html':
            try:origin=preview.origin()
            except OSError:pass  # Static source/download remain available.
        policy=("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; "
                f"frame-src {origin or chr(39)+'none'+chr(39)}; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; connect-src 'self'")
        title=escape(state['bundle']['title'])
        content=f'''<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 主機筆記附件</title><link rel="stylesheet" href="/assets/workbench.css"></head><body><main id="note-bundle-reader" class="note-bundle-reader"><h1>{title}</h1><p role="status">正在讀取附件…</p></main><script type="module" src="/assets/note-bundle-reader.mjs"></script></body></html>'''
        return HTMLResponse(content,headers={'Content-Security-Policy':policy})
