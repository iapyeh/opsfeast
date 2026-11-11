"""Execution defaults and throttled host lanes; all targets are synthetic."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from opsfeast import ConfigError, Instance
from opsfeast import execution_settings as settings
from opsfeast.recipe_runs import RecipeRuns
from opsfeast.site import SiteConflict


class ExecutionSettingsTests(unittest.TestCase):
    def test_default_save_revision_validation_and_no_write_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            state=settings.inspect(root)
            self.assertEqual(state['threads'],8)
            self.assertEqual(list(root.iterdir()),[])
            saved=settings.save(root,threads=3,expected_revision=state['revision'])
            self.assertEqual(settings.inspect(root)['threads'],3)
            with self.assertRaises(SiteConflict):settings.save(root,threads=4,expected_revision=state['revision'])
            for value in (True,0,-1,1.5,'8',None):
                with self.assertRaises(ConfigError):settings.save(root,threads=value,expected_revision=saved['revision'])
            self.assertEqual(settings.inspect(root)['threads'],3)
            path=root/settings.FILENAME
            path.write_text('{broken')
            before=path.read_bytes()
            with self.assertRaises(ConfigError):settings.inspect(root)
            self.assertEqual(path.read_bytes(),before)
            path.unlink();target=root/'private';target.write_text('do not touch');path.symlink_to(target)
            with self.assertRaises(ConfigError):settings.inspect(root)
            self.assertEqual(target.read_text(),'do not touch')


class ThrottleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()):self.profile=Instance.open(self.root).init_profile()
        self.hosts=['host-'+str(i) for i in range(6)]
        (self.profile.root/'hosts.yaml').write_text(json.dumps({'hosts':{h:{'connection':{'local':True}} for h in self.hosts}}))
        self.service=RecipeRuns(self.root,self.root);self.addCleanup(self.service.close)
        def prepare(root,reference,host,variables,inputs,selection=None):
            return {'reference':reference,'host_id':host,'kind':'operation','invocation':[], 'composition':None,'fingerprint':'synthetic'},[]
        self.prepare=patch('opsfeast.recipe_runs.prepare_pair',side_effect=prepare);self.prepare.start();self.addCleanup(self.prepare.stop)
        self.choose=patch('recipe_catalog.choose',return_value={'kind':'operation'});self.choose.start();self.addCleanup(self.choose.stop)

    def body(self,**changes):
        return {'profile':'main','hosts':self.hosts,'recipes':[{'reference':r,'vars':{},'inputs':[]} for r in ('a','b')],'timeout':30,**changes}

    def finished(self,identifier):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            result=self.service.show(identifier,'main')
            if result['state'] not in ('running','stopping'):return result
            time.sleep(.01)
        self.fail('synthetic lane did not complete')

    def test_default_and_temporary_override_are_runtime_only(self):
        plan=self.service.preview(self.body())
        self.assertNotIn('threads',plan)
        current=settings.inspect(self.root)
        settings.save(self.root,threads=3,expected_revision=current['revision'])
        def finish(record,plan):
            record['state']='completed'
            with self.service.lock:
                self.service._save(record);self.service.active=None
        with patch.object(self.service,'_work',side_effect=finish):
            first=self.service.start(plan['preview_id'],True)
            self.finished(first['id'])
            self.assertEqual(first['threads'],3)
            self.assertEqual(self.service.start(plan['preview_id'],True,threads=9)['threads'],3)
            other=self.service.preview(self.body())
            second=self.service.start(other['preview_id'],True,threads=2)
            self.finished(second['id'])
            self.assertEqual(second['threads'],2)
            for value in (True,0,-2,1.2,'8'):
                with self.assertRaises(ConfigError):self.service.start(self.service.preview(self.body())['preview_id'],True,threads=value)
        self.assertEqual(settings.inspect(self.root)['threads'],3)
        with self.assertRaises(ConfigError):self.service.preview(self.body(threads=2))

    def test_parallel_hosts_are_bounded_same_host_stays_serial_and_failures_continue(self):
        reached=threading.Event();release=threading.Event();lock=threading.Lock()
        active=set();maximum=0;calls=[]
        def invoke(task,spec,record):
            nonlocal maximum
            with lock:
                self.assertNotIn(spec['host'],active)
                active.add(spec['host']);maximum=max(maximum,len(active));calls.append((spec['host'],spec['reference']))
                if len(active)==2:reached.set()
            release.wait(3)
            with lock:active.remove(spec['host'])
            task['state']='failed' if spec['host']==self.hosts[0] and spec['reference']=='a' else 'success'
        with patch.object(self.service,'_invoke',side_effect=invoke):
            plan=self.service.preview(self.body())
            run=self.service.start(plan['preview_id'],True,threads=2)
            try:
                self.assertTrue(reached.wait(2))
                self.assertEqual(maximum,2)
            finally:release.set()
            result=self.finished(run['id'])
        self.assertEqual(maximum,2)
        self.assertEqual(len(calls),12)
        self.assertEqual(result['threads'],2)
        self.assertEqual(result['state'],'completed_with_gaps')
        for host in self.hosts:self.assertEqual([r for h,r in calls if h==host],['a','b'])

    def test_stop_ends_active_lanes_and_does_not_start_queued_hosts(self):
        reached=threading.Event();lock=threading.Lock();calls=[]
        def invoke(task,spec,record):
            with lock:
                calls.append(spec['host'])
                if len(calls)==2:reached.set()
            self.service.stopping.wait(3)
            task.update(state='stopped',local_termination='confirmed')
        with patch.object(self.service,'_invoke',side_effect=invoke):
            plan=self.service.preview(self.body())
            run=self.service.start(plan['preview_id'],True,threads=2)
            self.assertTrue(reached.wait(2))
            self.service.stop(run['id'],'main')
            result=self.finished(run['id'])
        self.assertEqual(len(calls),2)
        self.assertEqual(result['state'],'stopped')
        self.assertEqual(sum(t['state']=='skipped' for t in result['tasks']),10)
        self.assertEqual(result['remote_cleanup'],'unknown')

    def test_stop_terminates_every_active_owned_process(self):
        import subprocess
        import sys
        real=subprocess.Popen
        def launch(argv,**options):
            return real([sys.executable,'-u','-c','import sys,time; sys.stdin.read(); print("synthetic-ready",file=sys.stderr,flush=True); time.sleep(30)'],**options)
        with patch('opsfeast.recipe_runs.subprocess.Popen',side_effect=launch):
            plan=self.service.preview(self.body())
            run=self.service.start(plan['preview_id'],True,threads=2)
            try:
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    with self.service.lock:
                        ready=len(self.service.processes)==2 and sum(bool(t['progress']) for t in self.service.show(run['id'],'main')['tasks'])==2
                    if ready:break
                    time.sleep(.01)
                self.assertTrue(ready)
            finally:self.service.stop(run['id'],'main')
            result=self.finished(run['id'])
        self.assertEqual(sum(t['local_termination']=='confirmed' for t in result['tasks']),2)
        self.assertEqual(sum(t['state']=='skipped' for t in result['tasks']),10)
        self.assertEqual(self.service.processes,{})
        self.assertEqual(result['remote_cleanup'],'unknown')


    def test_concurrent_worker_results_are_saved_consistently(self):
        import subprocess
        import sys
        real=subprocess.Popen
        program='import sys,json; json.load(sys.stdin); [print("synthetic-progress",file=sys.stderr,flush=True) for _ in range(20)]; print(json.dumps({"status":"success","retention":{"status":"stored"},"content_update":{"status":"updated"}}))'
        def launch(argv,**options):return real([sys.executable,'-u','-c',program],**options)
        with patch('opsfeast.recipe_runs.subprocess.Popen',side_effect=launch):
            plan=self.service.preview(self.body())
            result=self.finished(self.service.start(plan['preview_id'],True,threads=3)['id'])
        self.assertEqual(result['state'],'completed')
        self.assertEqual(len(result['tasks']),12)
        self.assertTrue(all(t['state']=='success' and t['result']['status']=='success' for t in result['tasks']))
        self.assertEqual(self.service.processes,{})


import test_web_preview as web

@unittest.skipUnless(web.WEB_AVAILABLE,'optional Web requirements absent')
class ExecutionSettingsHTTPTests(unittest.IsolatedAsyncioTestCase):
    setUp=web.WebPreviewTests.setUp
    request=web.WebPreviewTests.request

    async def test_settings_auth_origin_conflict_and_preview_override(self):
        from opsfeast.web.app import create_app
        app=create_app(self.root,agent_token='t'*32)
        with contextlib.redirect_stdout(io.StringIO()):profile=Instance.open(self.root).init_profile()
        (profile.root/'hosts.yaml').write_text('hosts: {node: {connection: {local: true}}}\n')
        auth=[(b'authorization',b'Bearer '+b't'*32)]
        headers=auth+[(b'content-type',b'application/json')]
        path='/api/v1/recipe-execution/settings'
        self.assertEqual((await self.request(path,app=app))[0],401)
        status,_,raw=await self.request(path,headers=auth,app=app)
        self.assertEqual(status,200);state=json.loads(raw)
        self.assertEqual(state['threads'],8)
        payload=json.dumps({'threads':3,'expected_revision':state['revision']}).encode()
        self.assertEqual((await self.request(path,'PUT',headers=headers+[(b'origin',b'https://outside.invalid')],body=payload,app=app))[0],403)
        self.assertEqual((await self.request(path,'PUT',headers=headers,body=payload,app=app))[0],200)
        self.assertEqual((await self.request(path,'PUT',headers=headers,body=payload,app=app))[0],409)
        selection={'profile':'main','hosts':['node'],'recipes':[{'reference':'system/inventory/hardware','vars':{},'inputs':[]}],'timeout':30}
        _,_,raw=await self.request('/api/v1/recipe-runs/preview','POST',headers=headers,body=json.dumps(selection).encode(),app=app)
        self.assertNotIn('threads',json.loads(raw))
        preview=json.loads(raw)
        with patch.object(app.state.recipe_runs,'start',return_value={'threads':2}) as start:
            status,_,raw=await self.request('/api/v1/recipe-runs','POST',headers=headers,body=json.dumps({'preview_id':preview['preview_id'],'confirmed':True,'threads':2}).encode(),app=app)
            self.assertEqual(status,200)
            self.assertEqual(json.loads(raw)['threads'],2)
            start.assert_called_once_with(preview['preview_id'],True,threads=2)
        for value in (None,True,0):
            self.assertEqual((await self.request('/api/v1/recipe-runs','POST',headers=headers,body=json.dumps({'preview_id':preview['preview_id'],'confirmed':True,'threads':value}).encode(),app=app))[0],422)
        _,_,raw=await self.request(path,headers=auth,app=app)
        self.assertEqual(json.loads(raw)['threads'],3)
        self.assertFalse(app.state.recipe_runs.directory.exists())
