import json
import tempfile
import time
from pathlib import Path
from contextlib import contextmanager
import unittest
from opsfeast.interactive import Service,Store,InteractiveError,apply_delta

try:
    from sshscript import Session,Console
    HAVE_CONSOLE=True
except ImportError:HAVE_CONSOLE=False

@contextmanager
def local_console(profile,host):
    with Session() as session:
        with Console(session) as console:yield console

class StoreTests(unittest.TestCase):
    def test_database_scope_closes_on_success_and_failure(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp)
            with store.connect() as db:db.execute('SELECT 1')
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            with self.assertRaisesRegex(RuntimeError,'rollback'):
                with store.connect() as failed:
                    failed.execute("INSERT INTO work VALUES('rolled-back',0,'{}')")
                    raise RuntimeError('rollback')
            with self.assertRaises(sqlite3.ProgrammingError):failed.execute('SELECT 1')
            with self.assertRaisesRegex(InteractiveError,'unknown_work'):store.snapshot('rolled-back')

    def test_durable_replay_and_invalid_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);work=store.create('test','local','goal')
            store.emit(work,'test','agent',[{'op':'append','path':['feedback'],'value':{'text':'你好'}}])
            state={}
            for event in store.events(work):state=apply_delta(state,event['delta'])
            self.assertEqual(state,Store(tmp).snapshot(work)['state'])
            with self.assertRaises(InteractiveError):apply_delta({},[{'op':'set','path':['__proto__'],'value':{}}])

@unittest.skipUnless(HAVE_CONSOLE,'SSHScript is optional in generic test environments')
class InteractiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=Service(self.tmp.name,Path.cwd(),targets=[('test','local')],connector=local_console,idle_seconds=30)
        self.addCleanup(self.service.shutdown)
        self.work=self.service.create('test','local','local synthetic test')
    def act(self,action,body=None,role='operator'):
        import uuid
        return self.service.action(self.work,action,{'request_id':str(uuid.uuid4()),**(body or {})},role=role)
    def wait(self,status,timeout=15):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            state=self.service.store.snapshot(self.work)['state']
            if state['status'] in status:return state
            if state['status']=='failed':self.fail(str(state))
            time.sleep(.04)
        self.fail('state timeout: '+str(state))
    def plan(self,commands,mode='each'):
        self.act('plan',{'title':'test plan','approval_mode':mode,'steps':[{'command':command,'purpose':'test','checkpoint':False,'timeout':10} for command in commands]},role='agent')
        return self.service.store.snapshot(self.work)['state']['plan']['plan_id']
    def test_approval_streaming_replay_and_idempotency(self):
        plan=self.plan(['printf first; sleep 0.4; printf second','printf third'])
        self.assertIsNone(self.service.worker)
        with self.assertRaisesRegex(InteractiveError,'operator_required'):self.act('approve',{'plan_id':plan},role='agent')
        request={'request_id':'same-approval-0001','plan_id':plan}
        first=self.service.action(self.work,'approve',request,role='operator')
        self.assertEqual(first,self.service.action(self.work,'approve',request,role='operator'))
        state=self.wait({'awaiting_step'})
        self.assertEqual(len(state['history']),1)
        self.assertEqual(state['history'][0]['stdout'],'firstsecond')
        self.assertIsNone(state['current'])
        self.act('feedback',{'text':'continue'})
        self.act('continue',{'plan_id':plan})
        state=self.wait({'ready'})
        self.assertEqual(len(state['history']),2)
        self.act('analysis',{'content':{'kind':'table','columns':['result'],'rows':[['ok']] }},role='agent')
        composed={};cursor=0
        while True:
            batch=self.service.store.events(self.work,cursor)
            if not batch:break
            for event in batch:composed=apply_delta(composed,event['delta']);cursor=event['seq']
        self.assertEqual(composed,self.service.store.snapshot(self.work)['state'])
        self.act('close');self.wait({'closed'})
    def test_stale_plan_rejection_and_exact_plan_checkpoint(self):
        stale=self.plan(['printf old'])
        plan=self.plan(['printf new','printf later'],mode='plan')
        with self.assertRaisesRegex(InteractiveError,'stale_plan'):self.act('approve',{'plan_id':stale})
        self.act('approve',{'plan_id':plan})
        self.assertEqual(len(self.wait({'ready'})['history']),2)
        self.act('close');self.wait({'closed'})
    def test_stop_only_owned_job_and_preserve_result(self):
        plan=self.plan(['sleep 10','printf next-step'])
        self.act('approve',{'plan_id':plan})
        self.wait({'running'})
        self.act('stop');state=self.wait({'failed_step','paused'})
        self.assertTrue(state['history'][0]['stop_requested'])
        self.assertEqual(len(state['history']),1)
        self.assertEqual(state['plan']['next'],1)
        self.assertNotIn('next-step',state['history'][0]['stdout'])
        self.act('close');self.wait({'closed'})
    def test_output_limit_is_visible_after_step_finalization(self):
        from unittest.mock import patch
        plan=self.plan(['printf 123456789012','printf next-step'],mode='plan')
        with patch('opsfeast.interactive.OUTPUT_LIMIT',8):
            self.act('approve',{'plan_id':plan})
            state=self.wait({'paused','failed_step'})
        self.assertTrue(state['history'][0]['output_truncated'])
        self.assertLessEqual(len(state['history'][0]['stdout'].encode()),8)
        self.assertEqual(len(state['history']),1)
        self.act('close');self.wait({'closed'})
    def test_pre_dispatch_failure_is_preserved_as_failed_history(self):
        plan=self.plan(['exec sleep 1'])
        self.act('approve',{'plan_id':plan})
        state=self.wait({'failed'})
        self.assertIsNone(state['current'])
        self.assertEqual(state['history'][0]['status'],'failed')
        self.assertEqual(state['last_error']['type'],'ValueError')

    def test_recovery_never_executes_pending_plan(self):
        self.plan(['printf never-run'])
        self.service.shutdown()
        restarted=Service(self.tmp.name,Path.cwd(),targets=[('test','local')],connector=local_console)
        self.addCleanup(restarted.shutdown)
        self.assertEqual(restarted.store.snapshot(self.work)['state']['status'],'interrupted')
        self.assertIsNone(restarted.worker)
    def test_second_executor_is_rejected_without_reclassifying_live_work(self):
        with self.assertRaisesRegex(InteractiveError,'interactive_service_already_running'):
            Service(self.tmp.name,Path.cwd(),targets=[('test','local')],connector=local_console)
        self.assertEqual(self.service.store.snapshot(self.work)['state']['status'],'draft')
    def test_conflicts_and_validation(self):
        self.plan(['true'])
        payload={'request_id':'duplicate-feedback','text':'one'}
        self.service.action(self.work,'feedback',payload,role='agent')
        with self.assertRaisesRegex(InteractiveError,'request_id_conflict'):
            self.service.action(self.work,'feedback',{**payload,'text':'two'},role='agent')
        with self.assertRaisesRegex(InteractiveError,'target_not_enabled'):self.service.create('test','elsewhere','goal')

    def test_multiline_plan_rejected_atomically_before_connection(self):
        before=self.service.store.snapshot(self.work)
        for invalid in ('printf first\nprintf second', "printf 'first\n'", 'hostname\rid -un'):
            with self.subTest(command=invalid):
                with self.assertRaisesRegex(InteractiveError,'command_must_be_single_line'):
                    self.plan(['hostname',invalid])
                self.assertEqual(self.service.store.snapshot(self.work),before)
                self.assertIsNone(self.service.worker)

    def test_literal_backslash_newlines_stream_successfully(self):
        plan=self.plan([r"printf 'first\n'; sleep 0.4; printf 'second\n'"])
        self.act('approve',{'plan_id':plan})
        state=self.wait({'ready'})
        self.assertEqual(state['history'][0]['stdout'].replace('\r\n','\n'),'first\nsecond\n')
        self.assertEqual(state['history'][0]['exitcode'],0)
        self.act('close');self.wait({'closed'})

@unittest.skipUnless(HAVE_CONSOLE,'SSHScript required')
class CoreConsoleTests(unittest.TestCase):
    def test_sudo_root_is_explicit_scoped_and_uses_configured_credentials(self):
        from opsfeast.core import Sessions,CoreError
        from opsfeast import ConfigError
        from types import SimpleNamespace
        from unittest.mock import patch
        profile=SimpleNamespace(hosts=SimpleNamespace(_config=SimpleNamespace(hosts={'target':{}})))
        manager=Sessions(profile)
        env=SimpleNamespace(kind='ssh',connection_user='login',effective_user='login',identity_verified=True)
        request=SimpleNamespace(kind='sudo',username='root',environment=env,credential_supplied=False)
        @contextmanager
        def connection(*args,**kwargs):yield SimpleNamespace(_actor=object())
        class FakeConsole:
            def __init__(self,actor,**kwargs):self.resolve=kwargs['credential_resolver']
            def __enter__(self):return self
            def __exit__(self,*args):pass
        with patch.object(manager,'connect',connection),patch('sshscript.Console',FakeConsole),patch('host_runtime.privilege_password',return_value=('fixture-only-secret','configured-source')) as password:
            with manager.console('target') as console:
                with self.assertRaisesRegex(CoreError,'unsupported'):console.resolve(request)
            password.assert_not_called()
            with manager.console('target',sudo_root=True) as console:
                self.assertEqual(console.resolve(request).password,'fixture-only-secret')
                password.assert_called_once()
                for change in ({'username':'other'},{'kind':'su'},{'credential_supplied':True},{'environment':SimpleNamespace(**{**vars(env),'effective_user':'other'})},{'environment':SimpleNamespace(**{**vars(env),'identity_verified':False})}):
                    with self.assertRaisesRegex(CoreError,'unsupported'):console.resolve(SimpleNamespace(**{**vars(request),**change}))
                password.return_value=(None,'sudo_disabled')
                with self.assertRaisesRegex(CoreError,'sudo_disabled'):console.resolve(request)
            with self.assertRaises(ConfigError):
                with manager.console('target',sudo_root='yes'):pass

    def test_borrowed_adapter_and_expected_target(self):
        from opsfeast.core import Sessions,CoreError
        from types import SimpleNamespace
        from unittest.mock import patch
        @contextmanager
        def connection(host,timeout=30):
            with Session() as session:yield SimpleNamespace(_actor=session)
        manager=Sessions(None)
        with patch.object(manager,'connect',connection),patch.object(manager,'console_target',return_value={'fingerprint':'same'}):
            with self.assertRaisesRegex(CoreError,'console_target_changed'):
                with manager.console('target',expected_fingerprint='old'):pass
            with manager.console('target',expected_fingerprint='same') as console:
                update=console.start_command('printf adapter',timeout=5)
                output=update.stdout
                while update.state=='running':time.sleep(.02);update=console.poll();output+=update.stdout
                self.assertEqual(update.state,'completed');self.assertEqual(output,'adapter')
            import io
            stdout, stderr = io.StringIO(), io.StringIO()
            with manager.console('target', stdout=stdout, stderr=stderr) as console:
                update=console.start_command("printf stream; printf error >&2",timeout=5)
                while update.state=='running':time.sleep(.02);update=console.poll()
                self.assertEqual(update.state,'completed')
                self.assertEqual(update.stdout,'')
                self.assertEqual(update.stderr,'')
                self.assertIn('stream',stdout.getvalue()+stderr.getvalue())
                self.assertIn('error',stdout.getvalue()+stderr.getvalue())
    def test_fingerprint_includes_private_connection_changes_without_exposing_values(self):
        from opsfeast.core import Sessions
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            config=SimpleNamespace(hosts={'target':{'enabled':True}})
            manager=Sessions(SimpleNamespace(root=Path(tmp),hosts=SimpleNamespace(_config=config)))
            plan=[{'hostname':'example.invalid','username':'synthetic','password':'private-one'}]
            with patch('opsfeast.connection_plan',return_value=plan),patch('host_runtime.runtime_class',return_value=object):
                before=manager.console_target('target');plan[0]['password']='private-two';after=manager.console_target('target')
            self.assertNotEqual(before['fingerprint'],after['fingerprint'])
            self.assertNotIn('private',json.dumps(before));self.assertNotIn('password',before)
