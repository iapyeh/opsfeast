"""On-demand opaque-sandbox preview on a dedicated loopback port/origin."""
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit, quote

from opsfeast import note_bundles as bundles

LIFETIME=15*60
PREVIEW_HOST='127.0.0.1'
TYPES={'.html':'text/html; charset=utf-8','.htm':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp','.glb':'model/gltf-binary','.gltf':'model/gltf+json','.woff':'font/woff','.woff2':'font/woff2','.txt':'text/plain; charset=utf-8','.md':'text/plain; charset=utf-8'}


class BundlePreview:
    def __init__(self,product):
        self.product=product
        self.lock=threading.Lock()
        self.grants={}
        self.server=None
        self.thread=None

    def origin(self):
        with self.lock:
            if self.server is None:
                owner=self
                class Handler(BaseHTTPRequestHandler):
                    def log_message(self,*args):pass
                    def do_GET(self):owner.serve(self,body=True)
                    def do_HEAD(self):owner.serve(self,body=False)
                    def do_OPTIONS(self):owner.serve(self,body=False)
                    def do_POST(self):self.send_error(405)
                server=ThreadingHTTPServer((PREVIEW_HOST,0),Handler)
                server.daemon_threads=True
                self.server=server
                self.thread=threading.Thread(target=server.serve_forever,daemon=True);self.thread.start()
            return f'http://{PREVIEW_HOST}:{self.server.server_port}'

    def issue(self,scope):
        state=bundles.inspect(self.product,**scope)
        if state['bundle']['kind']!='html':bundles.fail('html_bundle_required')
        self.origin()
        with self.lock:
            now=time.monotonic();self.grants={key:value for key,value in self.grants.items() if value['expiry']>now}
            if len(self.grants)>=128:bundles.fail('preview_capacity_reached')
            token=secrets.token_urlsafe(32)
            self.grants[token]={'scope':dict(scope),'expiry':now+LIFETIME}
            base=f'http://{PREVIEW_HOST}:{self.server.server_port}/{token}/files/'
            return {'schema_version':'0.1.0','url':base+quote(state['bundle']['entry'],safe='/'),'expires_in':LIFETIME,'sandbox':'allow-scripts'}

    def serve(self,request,*,body):
        try:
            # Accept only this preview port. Cookies are ignored and never exposed;
            # browser isolation comes from a distinct origin AND an opaque sandbox.
            expected=f'{PREVIEW_HOST}:{self.server.server_port}'
            if request.headers.get('Host')!=expected:raise ValueError()
            parsed=urlsplit(request.path)
            if parsed.fragment:raise ValueError()
            parts=parsed.path.split('/',3)
            if len(parts)!=4 or parts[2]!='files':raise ValueError()
            token,path=parts[1],unquote(parts[3])
            with self.lock:grant=self.grants.get(token)
            if grant is None or grant['expiry']<=time.monotonic():raise ValueError()
            scope=grant['scope']
            raw=bundles.read_file(self.product,**scope,path=path)
            base=f'http://{expected}/{token}/files/'
            csp=(f"default-src 'none'; sandbox allow-scripts; script-src {base} 'unsafe-inline'; "
                 f"style-src {base} 'unsafe-inline'; img-src {base} data: blob:; font-src {base}; "
                 f"connect-src {base}; media-src {base} blob:; worker-src 'none'; object-src 'none'; "
                 "base-uri 'none'; form-action 'none'; frame-ancestors 'self' http://127.0.0.1:* http://localhost:*; frame-src 'none'")
            from pathlib import PurePosixPath
            if PurePosixPath(path).suffix.lower() in ('.html','.htm') and request.headers.get('Sec-Fetch-Dest')!='iframe':raise ValueError()
            if PurePosixPath(path).suffix.lower()=='.svg' and request.headers.get('Sec-Fetch-Dest') not in ('image','iframe'):raise ValueError()
            request.send_response(200 if request.command!='OPTIONS' else 204)
            request.send_header('Content-Type',TYPES.get(PurePosixPath(path).suffix.lower(),'application/octet-stream'))
            request.send_header('Content-Security-Policy',csp)
            request.send_header('X-Content-Type-Options','nosniff')
            request.send_header('Referrer-Policy','no-referrer')
            request.send_header('Cache-Control','no-store')
            # Opaque sandbox origins require CORS for ES modules/textures/fetch.
            # A scoped, unguessable URL authorizes this package only; no cookies.
            request.send_header('Access-Control-Allow-Origin','*')
            request.send_header('Access-Control-Allow-Methods','GET, HEAD, OPTIONS')
            request.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=(), payment=(), usb=()')
            request.send_header('Content-Length',str(len(raw) if request.command!='OPTIONS' else 0))
            request.end_headers()
            if body and request.command!='OPTIONS':request.wfile.write(raw)
        except Exception:
            request.send_response(404);request.send_header('Content-Length','0');request.send_header('Cache-Control','no-store');request.end_headers()

    def close(self):
        with self.lock:
            server=self.server;self.server=None;self.grants.clear()
        if server is not None:server.shutdown();server.server_close()
        if self.thread is not None:self.thread.join(2)
