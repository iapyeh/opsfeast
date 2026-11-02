"""Public tests for the optional, data-free Web preview."""
import asyncio
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest

WEB_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@unittest.skipUnless(WEB_AVAILABLE, "optional requirements-web.txt is not installed")
class WebPreviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".opsfeast-data.json").write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')

    async def request(self, path, method="GET", host="127.0.0.1", body=b"", headers=(), token=None, app=None):
        from opsfeast.web.app import create_app
        from urllib.parse import urlsplit
        parsed=urlsplit(path)
        messages = []
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                 "http_version": "1.1", "method": method, "scheme": "http", "path": parsed.path,
                 "raw_path": parsed.path.encode(), "query_string": parsed.query.encode(), "root_path": "",
                 "headers": [(b"host", host.encode()), *headers], "server": ("127.0.0.1", 8740),
                 "client": ("127.0.0.1", 12345)}
        await (app or create_app(self.root, edit_token=token))(scope, receive, send)
        response = next(m for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return response["status"], dict(response["headers"]), body

    async def test_pages_and_local_assets(self):
        from opsfeast.web.app import PAGES
        for path in PAGES:
            with self.subTest(path=path):
                status, headers, body = await self.request(path)
                self.assertEqual(status, 200)
                self.assertIn(b"text/html", headers[b"content-type"])
                self.assertIn(b'type="module"', body)
                self.assertIn(b'lang="zh-TW"', body)
        for path in ("/assets/workbench.css", "/assets/workbench.js", "/assets/mark.svg",
                     "/assets/i18n.mjs", "/assets/locales/zh-TW.mjs", "/assets/site-settings.mjs", "/assets/site-assets.mjs", "/assets/roadmap.mjs", "/assets/locales/roadmap-zh-TW.mjs", "/assets/host-draft.mjs", "/assets/host-model.mjs", "/assets/locales/host-draft-zh-TW.mjs"):
            self.assertEqual((await self.request(path))[0], 200)

    async def test_no_private_file_or_arbitrary_spa_fallback(self):
        for path in ("/AGENTS.local.md", "/hosts.yaml", "/.git/config", "/missing", "/assets/../index.html"):
            with self.subTest(path=path):
                self.assertEqual((await self.request(path))[0], 404)

    async def test_no_operation_endpoint(self):
        self.assertEqual((await self.request("/operations", "POST"))[0], 405)
        self.assertEqual((await self.request("/login", "POST"))[0], 405)
        self.assertEqual((await self.request("/api/v1/operations", "POST"))[0], 404)

    async def test_host_restriction_and_headers(self):
        self.assertEqual((await self.request("/", host="untrusted.example"))[0], 400)
        _, headers, _ = await self.request("/")
        self.assertIn(b"frame-ancestors 'none'", headers[b"content-security-policy"])
        self.assertEqual(headers[b"cache-control"], b"no-store")

    async def test_explicit_preview_contract(self):
        status, _, body = await self.request("/api/v1/preview")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["data_source"], "installation_presentation")
        self.assertFalse(data["operations_enabled"])
        self.assertTrue(data["profile_configuration_enabled"])
        self.assertEqual(data["authentication"], "single_administrator")

    async def test_first_use_status_is_nonsecret_and_authoritative(self):
        from opsfeast.web.app import create_app
        app=create_app(self.root,edit_token='synthetic-setup-capability')
        status,_,body=await self.request('/api/v1/setup',app=app)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body),{'schema_version':'0.1.0','admin_configured':False,
            'authenticated':False,'edit_unlocked':False,'local_unlock_available':True})
        self.assertNotIn(b'synthetic-setup-capability',body)
        self.assertEqual((await self.request('/api/v1/setup',headers=[(b'origin',b'https://untrusted.example')],app=app))[0],403)

    async def test_real_host_api_requires_admin_revision_and_delete_confirmation(self):
        try:__import__('ruamel.yaml')
        except ImportError:self.skipTest('optional host writer unavailable')
        from opsfeast import admin,profile_settings
        from opsfeast.web.app import create_app
        state=profile_settings.inspect(self.root)
        profile_settings.create(self.root,self.root,name='main',expected_revision=state['revision'])
        path=self.root/'profiles/main/hosts.yaml'
        path.write_text('hosts:\n  original:\n    connection: {local: true}\n    group: prod\ngroups:\n  prod: {label: Production}\n')
        app=create_app(self.root,edit_token='synthetic-host-api-token')
        content=(b'content-type',b'application/json')
        async def call(method='GET',data=None,headers=()):
            return await self.request('/api/v1/hosts?profile=main',method,body=json.dumps(data).encode() if data is not None else b'',headers=[content,*headers],app=app)
        for method in ('GET','POST','PATCH','DELETE'):
            self.assertEqual((await call(method,headers=[(b'authorization',b'Bearer synthetic-host-api-token')]))[0],401)
        password='Synthetic-host-api-password-001'
        admin.configure(self.root,username='synthetic',password=password,expected_revision=0)
        status,headers,_=await self.request('/hosts?profile=main',app=app)
        self.assertEqual(status,303)
        self.assertEqual(headers[b'location'],b'/login?next=%2Fhosts%3Fprofile%3Dmain')
        status,headers,_=await self.request('/api/v1/auth/login','POST',body=json.dumps({'username':'synthetic','password':password}).encode(),headers=[content],app=app)
        cookie=(b'cookie',headers[b'set-cookie'].split(b';')[0]);self.assertEqual(status,200)
        state=json.loads((await call(headers=[cookie]))[2]);self.assertEqual([host['host_id'] for host in state['hosts']],['original'])
        payload={'profile':'main','host_id':'new','expected_revision':state['revision'],'changes':{'connection':{'local':True},'group':['prod']}}
        self.assertEqual((await call('POST',payload,[cookie,(b'origin',b'https://untrusted.example')]))[0],403)
        self.assertEqual((await call('POST',payload,[cookie]))[0],200)
        self.assertEqual((await call('POST',payload,[cookie]))[0],409)
        state=json.loads((await call(headers=[cookie]))[2])
        deletion={'profile':'main','host_id':'new','expected_revision':state['revision'],'confirmation':'wrong'}
        self.assertEqual((await call('DELETE',deletion,[cookie]))[0],422)
        self.assertIn('new',[host['host_id'] for host in json.loads((await call(headers=[cookie]))[2])['hosts']])
        deletion['confirmation']='new'
        self.assertEqual((await call('DELETE',deletion,[cookie]))[0],200)
        self.assertEqual([host['host_id'] for host in json.loads((await call(headers=[cookie]))[2])['hosts']],['original'])

    async def test_settings_catalog_matches_shared_service_without_private_data(self):
        from opsfeast.settings import catalog
        status,_,body=await self.request('/api/v1/settings/catalog')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body),catalog())
        for category in ('hosts','recipes','parameters','retention'):
            self.assertEqual((await self.request('/settings/'+category))[0],200)
            self.assertEqual((await self.request('/api/v1/settings/'+category,'PUT'))[0],404)
        self.assertNotIn('data_root',json.loads(body))

    async def test_settings_auth_origin_and_conflict(self):
        from opsfeast.site import DEFAULT
        self.assertEqual((await self.request('/api/v1/site/settings'))[0], 401)
        token = 'synthetic-test-capability'
        auth = [(b'authorization', ('Bearer '+token).encode()), (b'content-type', b'application/json')]
        payload = json.dumps({'settings':dict(DEFAULT, site_name='synthetic'), 'expected_revision':0}).encode()
        self.assertEqual((await self.request('/api/v1/site/settings', 'PUT', body=payload, headers=auth))[0], 401)
        self.assertEqual((await self.request('/api/v1/site/settings', 'PUT', body=payload, headers=auth+[(b'origin',b'https://untrusted.example')], token=token))[0], 403)
        self.assertEqual((await self.request('/api/v1/site/settings', 'PUT', body=payload, headers=auth, token=token))[0], 200)
        self.assertEqual((await self.request('/api/v1/site/settings', 'PUT', body=payload, headers=auth, token=token))[0], 409)
        status, _, body = await self.request('/api/v1/site')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['site_name'], 'synthetic')
        self.assertNotIn('identity', json.loads(body))

    async def test_site_edit_session_survives_navigation_but_not_lock_expiry_or_restart(self):
        from opsfeast.web.app import create_app
        from opsfeast import admin
        from unittest.mock import patch
        token='synthetic-edit-session'
        app=create_app(self.root,edit_token=token)
        auth=[(b'authorization',('Bearer '+token).encode())]
        self.assertEqual((await self.request('/api/v1/site/unlock','POST',app=app))[0],401)
        self.assertEqual((await self.request('/api/v1/site/unlock','POST',headers=auth+[(b'origin',b'https://untrusted.example')],app=app))[0],403)
        status,headers,_=await self.request('/api/v1/site/unlock','POST',headers=auth,app=app)
        self.assertEqual(status,200)
        self.assertIn(b'HttpOnly',headers[b'set-cookie']);self.assertIn(b'SameSite=strict',headers[b'set-cookie'])
        cookie=[(b'cookie',headers[b'set-cookie'].split(b';')[0])]
        # New page requests carry only the cookie, not the original token text.
        for path in ('/','/settings/site','/api/v1/site/settings','/api/v1/admin'):
            self.assertEqual((await self.request(path,headers=cookie,app=app))[0],200)
        self.assertEqual((await self.request('/api/v1/profiles',headers=cookie,app=app))[0],401)
        self.assertEqual((await self.request('/api/v1/site/settings',headers=cookie,app=create_app(self.root,edit_token=token)))[0],401)
        import time
        with patch('opsfeast.web.security.time.monotonic',return_value=time.monotonic()+1801):
            self.assertEqual((await self.request('/api/v1/site/settings',headers=cookie,app=app))[0],401)
        payload=json.dumps({'username':'synthetic','password':'Synthetic-password-001','expected_revision':0}).encode()
        self.assertEqual((await self.request('/api/v1/admin/bootstrap','POST',headers=cookie+[(b'content-type',b'application/json')],body=payload,app=app))[0],200)
        progress=json.loads((await self.request('/api/v1/setup',headers=cookie,app=app))[2])
        self.assertTrue(progress['admin_configured']);self.assertTrue(progress['edit_unlocked'])
        self.assertFalse(progress['authenticated'])
        self.assertEqual((await self.request('/api/v1/admin',headers=cookie,app=app))[0],401)
        self.assertEqual((await self.request('/api/v1/admin','PUT',headers=cookie,app=app))[0],401)
        self.assertEqual((await self.request('/api/v1/site/lock','POST',headers=cookie+[(b'origin',b'https://untrusted.example')],app=app))[0],403)
        self.assertEqual((await self.request('/api/v1/site/lock','POST',headers=cookie,app=app))[0],200)
        self.assertEqual((await self.request('/api/v1/site/settings',headers=cookie,app=app))[0],401)

    async def test_image_api_limits_and_staging_visibility(self):
        import importlib.util
        if not importlib.util.find_spec('PIL'): self.skipTest('optional Pillow is absent')
        import io
        from PIL import Image
        from opsfeast.site import DEFAULT, MAX_UPLOAD
        token='synthetic-test-capability'
        auth=[(b'authorization', ('Bearer '+token).encode())]
        self.assertEqual((await self.request('/api/v1/site/images', 'POST'))[0],401)
        self.assertEqual((await self.request('/api/v1/site/images','POST',headers=auth,token=token))[0],415)
        self.assertEqual((await self.request('/api/v1/site/images','POST',body=b'x'*(MAX_UPLOAD+1),headers=auth+[(b'content-type',b'image/png')],token=token))[0],413)
        buf=io.BytesIO();Image.new('RGB',(2,2),'green').save(buf,format='PNG')
        status,_,body=await self.request('/api/v1/site/images','POST',body=buf.getvalue(),headers=auth+[(b'content-type',b'image/png')],token=token)
        self.assertEqual(status,200)
        asset=json.loads(body)['asset_id']
        self.assertEqual((await self.request('/site-assets/'+asset))[0],404)
        payload=json.dumps({'settings':dict(DEFAULT,logo=asset),'expected_revision':0}).encode()
        self.assertEqual((await self.request('/api/v1/site/settings','PUT',body=payload,headers=auth+[(b'content-type',b'application/json')],token=token))[0],200)
        self.assertEqual((await self.request('/site-assets/'+asset))[0],200)
        self.assertEqual((await self.request('/.opsfeast-site.json'))[0],404)

    async def test_new_product_serves_same_external_presentation_and_assets(self):
        import io, shutil
        if not importlib.util.find_spec('PIL'): self.skipTest('optional Pillow is absent')
        from PIL import Image
        from opsfeast import site
        from opsfeast.storage import initialize_data_root, bind_data_root
        code1=self.root/'code1';code1.mkdir()
        data=self.root/'persistent';initialize_data_root(code1,data)
        buf=io.BytesIO();Image.new('RGB',(2,2),'green').save(buf,format='PNG')
        asset=site.upload_image(data,buf.getvalue())['asset_id']
        site.save_site(data,dict(site.DEFAULT,site_name='Persistent synthetic site',slogan='Keep this',avatar=asset),expected_revision=0)
        self.root=code1
        before=(await self.request('/api/v1/site'))[2]
        shutil.rmtree(code1)
        code2=data.parent/'code2';code2.mkdir();bind_data_root(code2,data)
        self.root=code2
        self.assertEqual((await self.request('/api/v1/site'))[2],before)
        self.assertEqual((await self.request('/site-assets/'+asset))[0],200)

    async def test_administrator_login_profiles_and_credential_invalidation(self):
        from opsfeast.web.app import create_app
        app=create_app(self.root,edit_token='synthetic-bootstrap-capability')
        token_header=(b'authorization',b'Bearer synthetic-bootstrap-capability')
        content=(b'content-type',b'application/json')
        password='測試專用維運基地密碼🦉123'
        async def call(path,method='GET',data=None,headers=()):
            return await self.request(path,method,body=json.dumps(data).encode() if data is not None else b'',headers=[content,*headers],app=app)
        self.assertEqual((await call('/api/v1/profiles'))[0],401)
        self.assertEqual((await call('/settings/profiles'))[0],200)
        self.assertEqual((await call('/api/v1/profiles',headers=[token_header]))[0],401)
        payload={'username':'synthetic','password':password,'expected_revision':0}
        self.assertEqual((await call('/api/v1/admin/bootstrap','POST',payload))[0],401)
        self.assertEqual((await call('/api/v1/admin/bootstrap','POST',payload,[token_header]))[0],200)
        self.assertEqual((await call('/settings/profiles'))[0],200)
        self.assertEqual((await call('/api/v1/profiles'))[0],401)
        self.assertEqual((await call('/api/v1/admin/bootstrap','POST',payload,[token_header]))[0],409)
        public=json.loads((await call('/api/v1/auth/status'))[2]);self.assertIsNone(public['username'])
        for path in ('/workspace','/work','/logs','/skills','/recipes/data'):
            self.assertEqual((await call(path))[0],303)
        self.assertEqual((await call('/api/v1/auth/login','POST',{'username':'synthetic','password':'wrong'}))[0],401)
        status,headers,_=await call('/api/v1/auth/login','POST',{'username':'synthetic','password':password})
        self.assertEqual(status,200)
        self.assertIn(b'HttpOnly',headers[b'set-cookie']);self.assertIn(b'SameSite=strict',headers[b'set-cookie'])
        cookie=(b'cookie',headers[b'set-cookie'].split(b';')[0])
        self.assertTrue(json.loads((await call('/api/v1/auth/status',headers=[cookie]))[2])['authenticated'])
        state=json.loads((await call('/api/v1/profiles',headers=[cookie]))[2])
        status,_,body=await call('/api/v1/profiles','POST',{'name':'main','namespace':None,'expected_revision':state['revision']},[cookie])
        self.assertEqual(status,200,body)
        created=json.loads(body);self.assertEqual(created['default_profile'],'main')
        self.assertEqual((await call('/api/v1/profiles/default','PUT',{'name':'main','expected_revision':state['revision']},[cookie]))[0],409)
        foreign=[cookie,(b'origin',b'https://untrusted.example')]
        self.assertEqual((await call('/api/v1/profiles/default','PUT',{'name':'main','expected_revision':created['revision']},foreign))[0],403)
        self.assertEqual((await call('/api/v1/admin','PUT',{'username':'synthetic2','password':'Synthetic-test-password-002','current_password':'wrong','expected_revision':1},[cookie]))[0],401)
        self.assertEqual((await call('/api/v1/admin','PUT',{'username':'synthetic2','password':'Synthetic-test-password-002','current_password':password,'expected_revision':1},[cookie]))[0],200)
        self.assertEqual((await call('/api/v1/profiles',headers=[cookie]))[0],401)
        self.assertEqual((await call('/api/v1/admin',headers=[token_header]))[0],401)

    async def test_logout_session_expiry_and_login_rate_limit(self):
        from opsfeast.web.app import create_app
        from opsfeast import admin
        from opsfeast.web.security import Sessions
        admin.configure(self.root,username='synthetic',password='Synthetic-test-password-001',expected_revision=0)
        app=create_app(self.root)
        payload=json.dumps({'username':'synthetic','password':'Synthetic-test-password-001'}).encode()
        content=[(b'content-type',b'application/json')]
        status,headers,_=await self.request('/api/v1/auth/login','POST',body=payload,headers=content,app=app)
        self.assertEqual(status,200)
        cookie=(b'cookie',headers[b'set-cookie'].split(b';')[0])
        self.assertEqual((await self.request('/api/v1/auth/logout','POST',headers=[cookie],app=app))[0],200)
        self.assertFalse(json.loads((await self.request('/api/v1/auth/status',headers=[cookie],app=app))[2])['authenticated'])
        for _ in range(4):await self.request('/api/v1/auth/login','POST',body=payload,headers=content,app=app)
        self.assertEqual((await self.request('/api/v1/auth/login','POST',body=payload,headers=content,app=app))[0],429)
        sessions=Sessions();token=sessions.issue(1)
        self.assertTrue(sessions.authenticated(token,self.root))
        sessions.items={key:(revision,0) for key,(revision,_) in sessions.items.items()}
        self.assertFalse(sessions.authenticated(token,self.root))

    async def test_interactive_capabilities_and_disabled_default(self):
        from opsfeast.web.app import create_app
        app=create_app(self.root)
        self.assertEqual((await self.request('/interactive',app=app))[0],200)
        self.assertEqual((await self.request('/api/v1/interactive',app=app))[0],503)
        options={'targets':[('synthetic','host')],'operator_token':'operator-test','agent_token':'agent-test'}
        app=create_app(self.root,interactive_options=options)
        self.addCleanup(app.state.interactive.shutdown)
        app.state.interactive.custom_connector=True
        async def call(path='',body=None,role='operator',extra=()):
            headers=[(b'authorization',('Bearer '+role+'-test').encode()),(b'content-type',b'application/json'),*extra]
            return await self.request('/api/v1/interactive'+path,'POST' if body is not None else 'GET',body=json.dumps(body).encode() if body is not None else b'',headers=headers,app=app)
        self.assertEqual((await self.request('/api/v1/interactive',app=app))[0],401)
        self.assertEqual((await call(extra=[(b'origin',b'http://elsewhere.invalid')]))[0],403)
        self.assertEqual((await call(body={'profile':'synthetic','host_id':'host','goal':'test'},role='agent'))[0],403)
        status,_,body=await call(body={'profile':'synthetic','host_id':'host','goal':'test'})
        self.assertEqual(status,200);work=json.loads(body)['state']['work_id']
        payload={'request_id':'plan-test-001','title':'test','approval_mode':'each','steps':[{'command':'printf safe','purpose':'test','checkpoint':True,'timeout':5}]}
        self.assertEqual((await call('/'+work+'/plan',payload,'agent'))[0],200)
        state=json.loads((await call('/'+work))[2])['state'];plan=state['plan']['plan_id']
        invalid={**payload,'request_id':'bad-lines-001','steps':[{**payload['steps'][0],'command':'hostname\nid -un'}]}
        invalid_status,_,invalid_body=await call('/'+work+'/plan',invalid,'agent')
        self.assertEqual(invalid_status,409)
        self.assertEqual(json.loads(invalid_body)['detail'],'command_must_be_single_line')
        self.assertEqual(json.loads((await call('/'+work))[2])['state']['plan']['plan_id'],plan)
        self.assertEqual((await call('/'+work+'/approve',{'request_id':'approve-test','plan_id':plan},'agent'))[0],403)
        self.assertIsNone(app.state.interactive.worker)
        for asset in ('interactive.mjs','interactive-state.mjs','interactive.css'):
            self.assertEqual((await self.request('/assets/'+asset,app=app))[0],200)
        self.assertEqual((await call('/'+work+'/feedback',{'request_id':'feedback-test','text':'comment'},'agent'))[0],200)

    async def test_console_blocks_login_range_form_and_agent_responses(self):
        import uuid
        from opsfeast.web.app import create_app
        from opsfeast import admin
        app=create_app(self.root,console_options={'writer_token':'w','reader_token':'r'})
        sid=str(uuid.uuid4());bid=str(uuid.uuid4());fid=str(uuid.uuid4())
        async def call(path='',body=None,token='w',cookie=None,origin=None):
            headers=[(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json')]
            if cookie:headers.append((b'cookie',cookie))
            if origin:headers.append((b'origin',origin.encode()))
            return await self.request('/api/v1/console-sessions'+path,'POST' if body is not None else 'GET',body=json.dumps(body).encode() if body is not None else b'',headers=headers,app=app)
        body={'session_id':sid,'title':'fixture','host_id':'synthetic','work_id':None}
        self.assertEqual((await call(body=body,token='r'))[0],401)
        self.assertEqual((await call(body=body,origin='http://elsewhere.invalid'))[0],403)
        self.assertEqual((await call(body=body))[0],200)
        block={'event_id':str(uuid.uuid4()),'block_id':bid,'kind':'stdout','title':'Long output','text':'文'*1000,'form':None}
        self.assertEqual((await call('/'+sid+'/blocks',block))[0],200)
        snapshot=json.loads((await call('/'+sid,token='r'))[2]);self.assertEqual(len(snapshot['blocks']),1)
        page=json.loads((await call('/'+sid+'/blocks/'+bid+'/content?limit=256',token='r'))[2]);self.assertEqual(page['next_offset'],255)
        self.assertEqual((await self.request('/console/'+sid,app=app))[0],303)
        admin.configure(self.root,username='synthetic',password='fixture-only-123',expected_revision=0)
        login=await self.request('/api/v1/auth/login','POST',body=json.dumps({'username':'synthetic','password':'fixture-only-123'}).encode(),headers=[(b'content-type',b'application/json')],app=app)
        cookie=login[1][b'set-cookie'].split(b';')[0]
        self.assertEqual((await self.request('/console/'+sid,headers=[(b'cookie',cookie)],app=app))[0],200)
        self.assertEqual((await self.request('/console/'+sid+'/blocks/'+bid,headers=[(b'cookie',cookie)],app=app))[0],200)
        schema={'fields':[],'choices':[{'id':'yes','label':'Yes'}],'expires_at':None}
        self.assertEqual((await call('/'+sid+'/blocks',{**block,'event_id':str(uuid.uuid4()),'block_id':fid,'kind':'form','form':schema}))[0],200)
        reply={'event_id':str(uuid.uuid4()),'revision':1,'choice':'yes','values':{}}
        path='/'+sid+'/blocks/'+fid+'/responses'
        self.assertEqual((await call(path,reply))[0],401)
        self.assertEqual((await call(path,reply,cookie=cookie,origin='http://elsewhere.invalid'))[0],403)
        self.assertEqual((await call(path,reply,cookie=cookie))[0],200)
        replies=json.loads((await call('/'+sid+'/responses?after=0&wait=0'))[2])
        self.assertEqual(len(replies['responses']),1)
        self.assertEqual(replies['responses'][0]['response']['actor'],'synthetic')
        self.assertEqual((await call(path,{**reply,'event_id':str(uuid.uuid4())},cookie=cookie))[0],409)
        self.assertEqual((await call('/'+sid+'/stream?after=99',token='r'))[0],409)

    async def test_console_sse_covers_snapshot_to_stream_race_and_new_delta(self):
        import uuid
        from types import SimpleNamespace
        from opsfeast.web.app import create_app
        app=create_app(self.root,console_options={'writer_token':'w','reader_token':'r'})
        records=app.state.console_records;sid=str(uuid.uuid4());bid=str(uuid.uuid4())
        records.create({'session_id':sid,'title':'SSE fixture','host_id':'synthetic','work_id':None})
        cursor=records.snapshot(sid)['seq']
        records.add_block(sid,{'event_id':str(uuid.uuid4()),'block_id':bid,'title':'stream','kind':'stdout','text':'first','form':None})
        async def disconnected():return False
        req=SimpleNamespace(headers={'authorization':'Bearer r'},cookies={},is_disconnected=disconnected)
        route=next(r for r in app.routes if getattr(r,'path','')=='/api/v1/console-sessions/{session_id}/stream')
        response=await route.endpoint(sid,req,cursor);iterator=response.body_iterator
        try:
            first=await asyncio.wait_for(anext(iterator),2);self.assertIn('first',first)
            records.append(sid,bid,{'event_id':str(uuid.uuid4()),'offset':5,'text':' second'})
            second=await asyncio.wait_for(anext(iterator),2);self.assertIn('first second',second);self.assertIn('id: 2',second)
        finally:await iterator.aclose()



if __name__ == "__main__":
    unittest.main()
