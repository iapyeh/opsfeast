"""Authenticated bundle reads, safe Markdown, and isolated scoped active assets."""
import io
import json
import unittest
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError

from PIL import Image
from opsfeast import host_notes as notes,note_bundles as bundles
from opsfeast.web.app import create_app
from opsfeast.web.note_bundle_preview import BundlePreview
import test_host_notes
import test_web_preview


def png():
    out=io.BytesIO();Image.new('RGB',(2,2),'red').save(out,format='PNG');return out.getvalue()


class BundleWebTests(unittest.IsolatedAsyncioTestCase):
    setUp=test_host_notes.HostNotesTests.setUp
    state=test_host_notes.HostNotesTests.state
    change=test_host_notes.HostNotesTests.change
    content=test_host_notes.HostNotesTests.content
    request=test_web_preview.WebPreviewTests.request
    def headers(self):return [(b'authorization',b'Bearer synthetic-owner-with-at-least-32-characters'),(b'content-type',b'application/json')]
    def fixture(self):
        self.app=create_app(self.code,data_root=self.data,agent_token='synthetic-owner-with-at-least-32-characters')
        note=self.change(changes=self.content())['note']
        return dict(profile='main',host_id='sample',note_uuid=note['uuid'])

    async def test_upload_markdown_images_downloads_and_authority(self):
        scope=self.fixture()
        source=b'# Report\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n![local](images/a.png)\n![remote](https://example.invalid/a.png)\n<script>evil()</script>\n[HTML](index.html)'
        from test_note_bundles import archive
        raw=archive({'report.md':source,'images/a.png':png(),'index.html':b'<script>evil()</script>'})
        query=urlencode({**scope,'expected_revision':self.state()['revision'],'title':'Synthetic report','entry':'report.md'})
        path='/api/v1/note-bundles?'+query
        self.assertEqual((await self.request(path,'POST',app=self.app,body=raw,headers=[(b'content-type',b'application/zip')]))[0],401)
        code,_,body=await self.request(path,'POST',app=self.app,body=raw,headers=[*self.headers()[:1],(b'content-type',b'application/zip')])
        self.assertEqual(code,200,body);state=json.loads(body);scope['bundle_uuid']=state['bundle']['uuid'];params=urlencode(scope)
        code,_,raw=await self.request('/api/v1/note-bundles/markdown?'+params,app=self.app,headers=self.headers());self.assertEqual(code,200,raw)
        rendered=json.loads(raw);self.assertIn('<table>',rendered['html']);self.assertNotIn('<script>',rendered['html']);self.assertIn('&lt;script&gt;',rendered['html'])
        self.assertIn('/api/v1/note-bundles/image?',rendered['html']);self.assertNotIn('src="https:',rendered['html']);self.assertEqual(len(rendered['warnings']),1)
        for name in ['image','file','export','markdown','']:
            suffix='/' + name if name else ''
            self.assertEqual((await self.request('/api/v1/note-bundles'+suffix+'?'+params+'&path=images%2Fa.png',app=self.app))[0],401)
        code,headers,raw=await self.request('/api/v1/note-bundles/image?'+params+'&path=images%2Fa.png',app=self.app,headers=self.headers());self.assertEqual(code,200);self.assertEqual(headers[b'content-type'],b'image/png')
        code,headers,raw=await self.request('/api/v1/note-bundles/file?'+params+'&path=index.html',app=self.app,headers=self.headers());self.assertEqual(code,200);self.assertIn(b'attachment',headers[b'content-disposition']);self.assertIn(b'application/octet-stream',headers[b'content-type'])
        code,headers,raw=await self.request('/note-attachments?'+params,app=self.app);self.assertEqual(code,303);self.assertIn(b'/login?',headers[b'location'])
        code,headers,raw=await self.request('/note-attachments?'+params,app=self.app,headers=self.headers());self.assertEqual(code,200);self.assertIn(b'note-bundle-reader.mjs',raw)
        payload={**scope,'expected_revision':self.state()['revision'],'confirmation':scope['bundle_uuid']}
        code,_,_=await self.request('/api/v1/note-bundles','DELETE',body=json.dumps(payload).encode(),headers=[*self.headers(),(b'origin',b'https://evil.invalid')],app=self.app);self.assertEqual(code,403)
        code,_,raw=await self.request('/api/v1/note-bundles','DELETE',body=json.dumps(payload).encode(),headers=self.headers(),app=self.app);self.assertEqual(code,200,raw)
        self.assertEqual((await self.request('/api/v1/note-bundles?'+params,app=self.app,headers=self.headers()))[0],404)

    async def test_folder_json_upload_is_bounded_and_revision_checked(self):
        import base64
        scope=self.fixture();query=urlencode({**scope,'expected_revision':self.state()['revision'],'title':'Folder report','entry':'index.md'})
        body={'files':[{'path':'index.md','base64':base64.b64encode(b'# Folder report').decode()}]}
        code,_,raw=await self.request('/api/v1/note-bundles?'+query,'POST',body=json.dumps(body).encode(),headers=self.headers(),app=self.app);self.assertEqual(code,200,raw)
        self.assertEqual((await self.request('/api/v1/note-bundles?'+query,'POST',body=json.dumps(body).encode(),headers=self.headers(),app=self.app))[0],409)
        body['files'][0]['path']='../escape'
        self.assertEqual((await self.request('/api/v1/note-bundles?'+query,'POST',body=json.dumps(body).encode(),headers=self.headers(),app=self.app))[0],422)


class IsolatedPreviewTests(unittest.TestCase):
    setUp=test_host_notes.HostNotesTests.setUp
    state=test_host_notes.HostNotesTests.state
    change=test_host_notes.HostNotesTests.change
    content=test_host_notes.HostNotesTests.content
    def test_auxiliary_host_headers_scoping_expiry_and_delete_revoke(self):
        note=self.change(changes=self.content())['note'];scope=dict(profile='main',host_id='sample',note_uuid=note['uuid'])
        created=bundles.create(self.code,**scope,expected_revision=self.state()['revision'],title='Interactive',entry='index.html',files={'index.html':b'<script type="module" src="app.mjs"></script>','app.mjs':b'fetch("data.json")','data.json':b'{"synthetic":true}','figure.svg':b'<svg xmlns="http://www.w3.org/2000/svg" />'})
        scope['bundle_uuid']=created['bundle']['uuid']
        preview=BundlePreview(self.code);self.addCleanup(preview.close);grant=preview.issue(scope)
        self.assertEqual(urlsplit(grant['url']).hostname,'127.0.0.1')
        http=build_opener(ProxyHandler({}))
        def get(url,headers={}):
            try:
                with http.open(Request(url,headers=headers),timeout=5) as response:return response.status,response.headers,response.read()
            except HTTPError as error:
                with error:return error.code,error.headers,error.read()
        self.assertEqual(get(grant['url'])[0],404)
        code,headers,raw=get(grant['url'],{'Sec-Fetch-Dest':'iframe'});self.assertEqual(code,200)
        self.assertIn('sandbox allow-scripts',headers['Content-Security-Policy']);self.assertNotIn('allow-same-origin',headers['Content-Security-Policy'])
        self.assertEqual(headers['Access-Control-Allow-Origin'],'*');self.assertIsNone(headers.get('Access-Control-Allow-Credentials'));self.assertIsNone(headers.get('Set-Cookie'))
        base=grant['url'].rsplit('/',1)[0]+'/'
        self.assertEqual(get(base+'app.mjs')[0],200);self.assertEqual(get(base+'data.json')[0],200)
        self.assertEqual(get(base+'figure.svg')[0],404);self.assertEqual(get(base+'figure.svg',{'Sec-Fetch-Dest':'image'})[0],200)
        self.assertEqual(get(base+'../manifest.json')[0],404)
        self.assertEqual(get(grant['url'],{'Host':f'localhost:{urlsplit(grant["url"]).port}','Sec-Fetch-Dest':'iframe'})[0],404)
        key=urlsplit(grant['url']).path.split('/')[1];preview.grants[key]['expiry']=0
        self.assertEqual(get(base+'app.mjs')[0],404)
        grant=preview.issue(scope)
        bundles.delete(self.code,**scope,expected_revision=self.state()['revision'],confirmation=scope['bundle_uuid'])
        self.assertEqual(get(grant['url'],{'Sec-Fetch-Dest':'iframe'})[0],404)


class BundleLoginDestinationTests(unittest.TestCase):
    def test_exact_attachment_context_survives_login_without_extra_or_external_values(self):
        from opsfeast.web.security import login_destination
        url='/note-attachments?profile=lab&host_id=node&note_uuid=note&bundle_uuid=bundle'
        self.assertEqual(login_destination(url),url)
        for value in [url+'&profile=other',url+'&next=https://example.invalid',url+'#extra','https://example.invalid'+url]:
            self.assertEqual(login_destination(value),'/workspace')
