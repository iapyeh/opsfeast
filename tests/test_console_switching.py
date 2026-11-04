"""Runtime switch authorization and actor/target credential policy; no real hosts."""
import ast
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from opsfeast.core import Sessions, CoreError
from opsfeast.console_agent import Worker, Publisher, ControlError
from opsfeast.console_records import Records
from test_console_agent import StoreTransport


@dataclass(frozen=True)
class Environment:
    kind: str = 'ssh'
    host: str = 'synthetic'
    connection_user: str = 'login'
    effective_user: str = 'login'
    identity_verified: bool = True


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.records=Records(Path(self.tmp.name))
        self.publisher=Publisher(StoreTransport(self.records),title='Switch fixture',host_id='lab / synthetic')
        self.manager=Sessions(SimpleNamespace(hosts=SimpleNamespace(_config=SimpleNamespace(hosts={'target':{'users':{'app':{},'login':{}}}}))))
        self.connections=0
        test=self
        @contextmanager
        def connection(*args,**kwargs):
            test.connections+=1
            yield SimpleNamespace(_actor=object())
        self.connection_patch=patch.object(self.manager,'connect',connection);self.connection_patch.start();self.addCleanup(self.connection_patch.stop)
        self.lookup=patch('host_runtime.privilege_password',return_value=('synthetic-secret','configured')).start()
        self.addCleanup(patch.stopall)
        self.update=SimpleNamespace(state='completed',result=None,error_type=None)
        class FakeConsole:
            session_reuse='confirmed'
            def __init__(self,actor,**kwargs):
                self.resolve=kwargs['credential_resolver'];self.environments=[Environment()];self.submissions=[]
            @property
            def prompt(self):return 'synthetic ['+self.environments[-1].effective_user+']> '
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def submit(self,source):
                self.submissions.append(source)
                if source=='$.exit()':self.environments.pop()
                else:
                    call=ast.parse(source.replace('$.','console.'),mode='eval').body
                    options={k.arg:ast.literal_eval(k.value) for k in call.keywords}
                    request=SimpleNamespace(kind=call.func.attr,username=options['username'],environment=self.environments[-1],credential_supplied=False)
                    self.resolve(request)
                    self.environments.append(Environment(kind=request.kind,effective_user=request.username))
                return test.update
            def start_command(self,command,timeout):return test.update
        self.console_patch=patch('sshscript.Console',FakeConsole);self.console_patch.start();self.addCleanup(self.console_patch.stop)
        @contextmanager
        def opener(stdout,stderr):
            with self.manager.console('target',switch_authorizer=self.worker.authorize_switch) as console:yield console
        self.worker=Worker(self.publisher,opener,lambda value:None)
        self.addCleanup(lambda:self.worker.close() if not self.worker.closed else None)
        self.worker.request({'op':'connect','request_id':'connect'})

    def action(self,op,rid,**kwargs):return self.worker.request(dict(op=op,request_id=rid,**kwargs))

    def test_login_then_authorized_sudo_leave_su_and_nested_sudo_keep_one_session(self):
        self.assertEqual(self.worker.console.environments[-1].effective_user,'login')
        self.lookup.assert_not_called()
        result=self.action('sudo','root',authorization='Human authorized root inspection',purpose='Inspect storage as root')
        self.assertEqual(result['identity']['effective_user'],'root')
        self.assertEqual(self.lookup.call_args.args[2:],('login','sudo','login'))
        self.assertFalse(self.worker.authorize_switch(SimpleNamespace(kind='sudo',username='root',environment=Environment())))
        self.assertEqual(self.action('leave','back')['identity']['effective_user'],'login')
        self.assertEqual(self.action('su','app',username='app',authorization='Human selected app')['identity']['effective_user'],'app')
        self.assertEqual(self.lookup.call_args.args[2:],('app','su','login'))
        self.action('sudo','app-root',authorization='Human authorized app sudo')
        self.assertEqual(self.lookup.call_args.args[2:],('app','sudo','login'))
        self.assertEqual(self.action('leave','back-app')['identity']['effective_user'],'app')
        self.assertEqual(self.action('leave','back-login')['identity']['effective_user'],'login')
        self.assertEqual(self.connections,1)
        text=''.join(b['head'] for b in self.records.snapshot(self.publisher.sid)['blocks'])
        self.assertIn('Inspect storage as root',text);self.assertNotIn('synthetic-secret',text)

    def test_missing_grant_unknown_fields_and_duplicate_do_not_switch(self):
        for body in [dict(op='sudo',request_id='missing'),dict(op='su',request_id='empty',username='app'),dict(op='su',request_id='injected',username='app',authorization='grant',password='forbidden')]:
            with self.assertRaises(ControlError):self.worker.request(body)
        self.lookup.assert_not_called()
        self.action('sudo','once',authorization='Human grant')
        with self.assertRaisesRegex(ControlError,'duplicate'):self.action('sudo','once',authorization='Human grant')
        self.assertEqual(self.lookup.call_count,1)

    def test_root_su_needs_no_target_secret_and_leave_cannot_close_login(self):
        with self.assertRaisesRegex(ControlError,'identity_layer_required'):self.action('leave','no-layer')
        self.action('sudo','root',authorization='Human grant')
        self.lookup.reset_mock()
        self.action('su','other',username='other',authorization='Human selected other account')
        self.lookup.assert_not_called()
        self.assertEqual(self.action('leave','parent')['identity']['effective_user'],'root')

    def test_core_no_grant_unverified_identity_explicit_secret_and_disabled_sudo(self):
        console=self.worker.console
        request=SimpleNamespace(kind='sudo',username='root',environment=Environment(),credential_supplied=False)
        with self.assertRaises(CoreError):console.resolve(request)
        self.worker.pending_switch=('sudo','root','synthetic','login')
        with self.assertRaises(CoreError):console.resolve(SimpleNamespace(**{**vars(request),'credential_supplied':True}))
        with self.assertRaises(CoreError):console.resolve(SimpleNamespace(**{**vars(request),'environment':Environment(identity_verified=False)}))
        self.lookup.return_value=(None,'sudo_disabled')
        with self.assertRaisesRegex(CoreError,'sudo_disabled'):console.resolve(request)
        self.assertEqual(self.lookup.call_count,1)
        self.assertIsNone(self.worker.pending_switch)

    def test_missing_su_credential_uses_private_callback_and_never_retries(self):
        self.lookup.return_value=(None,'none')
        password=lambda prompt:'temporary-test-secret'
        with self.manager.console('target',switch_authorizer=lambda request:True,password_func=password) as console:
            request=SimpleNamespace(kind='su',username='operator',environment=Environment(),credential_supplied=False)
            self.assertEqual(console.resolve(request).password,'temporary-test-secret')
        with self.manager.console('target',switch_authorizer=lambda request:True) as console:
            with self.assertRaisesRegex(CoreError,'su_password_required'):console.resolve(request)
