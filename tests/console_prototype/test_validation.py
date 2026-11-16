"""Consumer tests against only the designated local wheel, no native account switches."""
from pathlib import Path
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).parent))
from adapter import Bridge
from sshscript import Console, Session

EVIDENCE=Path(os.environ.get('CONSOLE_EVIDENCE','/private/tmp/opsfeast-console-evidence-20261023'))
EVIDENCE.mkdir(exist_ok=True)


class ConsoleConsumerTests(unittest.TestCase):
    def setUp(self):
        self.bridge=Bridge(EVIDENCE/(self._testMethodName+'.jsonl'))
        self.addCleanup(self.bridge.stop)

    def open(self,mode='local',fault=None):
        event=self.bridge.call('open',mode,fault=fault)
        self.assertEqual(event['state'],'ready',event)
        self.assertTrue(event['same_session'])
        return event

    def wait(self,seconds=8):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            current=self.bridge.snapshot()['current']
            if current['state']!='running': return current
            time.sleep(.03)
        self.fail('operation did not finish')

    def test_state_python_cwd_environment_and_failure(self):
        self.open()
        for line in ['items=[]','for n in range(2):','    items.append(n)']:
            event=self.bridge.call('submit',line)
        self.assertEqual(event['state'],'incomplete')
        self.assertEqual(self.bridge.call('submit','')['state'],'completed')
        self.assertIn('[0, 1]',self.bridge.call('submit','print(items)')['stdout'])
        self.assertIn('PTY',self.bridge.call('submit','$test -t 0 && printf PTY')['stdout'])
        self.bridge.call('submit','$cd /tmp; export OPS_CONSOLE_VALUE=retained')
        self.bridge.call('start','pwd; printf "$OPS_CONSOLE_VALUE"')
        self.assertEqual(self.wait()['state'],'completed')
        outputs=''.join(e['stdout'] for e in self.bridge.events)
        self.assertIn('retained',outputs)
        self.assertIn('/tmp',outputs)
        bad=self.bridge.call('submit','$false')
        self.assertEqual((bad['state'],bad['exitcode']),('failed',1))
        self.assertEqual(self.bridge.call('submit','raise SystemExit(7)')['error_type'],'SystemExit')
        self.assertEqual(self.bridge.call('submit','print(42)')['state'],'completed')

    def test_streaming_nonblocking_and_shell_stdin_rejected(self):
        self.open()
        update=self.bridge.call('start','printf early; sleep .8; printf late')
        self.assertEqual(update['state'],'running')
        time.sleep(.25)
        self.assertIn('early',''.join(x['stdout'] for x in self.bridge.events))
        before=time.monotonic();self.bridge.snapshot()
        self.assertLess(time.monotonic()-before,.1)
        rejected=self.bridge.call('input','must-not-reach-shell')
        self.assertEqual(rejected['error_type'],'RuntimeError')
        # Rejected input must not prevent polling the real foreground job.
        self.bridge.call('poll')
        end=self.wait()
        self.assertEqual((end['state'],end['exitcode']),('completed',0))
        self.assertIn('late',''.join(x['stdout'] for x in self.bridge.events))

    def test_timeout_interrupt_and_recovery(self):
        self.open()
        self.bridge.call('start','sleep 10',timeout=.15)
        end=self.wait()
        self.assertEqual((end['state'],end['error_type']),('failed','CommandTimeoutError'))
        self.bridge.call('start','sleep 10')
        end=self.bridge.call('interrupt')
        self.assertEqual(end['stop_reason'],'cancelled')
        self.assertEqual(end['termination_status'],'confirmed')
        self.assertEqual(self.bridge.call('submit','$printf recovered')['stdout'],'recovered')

    def test_program_state_prompt_timeout_poll_ctrlc_eof_and_exitcode(self):
        self.open()
        event=self.bridge.call('enter')
        self.assertEqual(event['state'],'waiting_input')
        self.assertFalse(event['environments'][-1]['identity_verified'])
        self.bridge.call('input','x=40')
        self.assertIn('42',self.bridge.call('input','print(x+2)')['stdout'])
        event=self.bridge.call('input','import time; time.sleep(.6)',timeout=.1)
        self.assertEqual(event['state'],'running')
        self.assertEqual(self.wait()['state'],'waiting_input')
        self.bridge.call('eof')
        self.assertEqual(len(self.bridge.snapshot()['current']['environments']),1)
        self.bridge.call('enter')
        event=self.bridge.call('input','raise SystemExit(9)')
        self.assertEqual((event['state'],event['exitcode']),('failed',9))

    def test_program_ctrlc_reaches_structured_prompt_again(self):
        self.open()
        self.bridge.call('enter')
        self.bridge.call('interrupt')
        end=self.wait(seconds=2)
        self.assertEqual(end['state'],'waiting_input')

    def test_leave_quit_borrowed_ownership_and_real_reuse(self):
        self.open('simulated')
        self.bridge.call('shell')
        self.assertEqual(len(self.bridge.snapshot()['current']['environments']),2)
        self.bridge.call('leave')
        self.assertEqual(len(self.bridge.snapshot()['current']['environments']),1)
        end=self.bridge.call('submit','quit()')
        self.assertEqual((end['state'],end['session_reuse']),('closed','confirmed'))
        self.assertFalse(end['owner_closed']);self.assertFalse(end['ancestor_closed'])
        self.assertEqual(end['open_fixture_layers'],0)
        self.assertEqual(end['connect_calls'],0)
        probe=self.bridge.call('reuse')
        self.assertEqual((probe['owner_reuse_stdout'],probe['owner_reuse_exitcode']),('OWNER_REUSED',0))
        self.bridge.stop()
        self.assertTrue(self.bridge.session.closed)
        self.assertEqual(self.bridge.session.owner_close_calls,1)

    def test_eof_and_host_exception_cleanup(self):
        self.open()
        end=self.bridge.call('eof')
        self.assertEqual((end['state'],end['session_reuse']),('closed','confirmed'))
        self.open()
        end=self.bridge.call('host_exception')
        self.assertEqual((end['state'],end['session_reuse']),('closed','confirmed'))
        self.assertEqual(self.bridge.call('reuse')['owner_reuse_exitcode'],0)

    def test_credentials_policy_observer_and_no_hidden_prompts(self):
        self.open('simulated')
        end=self.bridge.call('su','operator')
        self.assertEqual(end['environments'][-1]['effective_user'],'operator')
        self.assertEqual(end['environments'][-1]['connection_user'],'fixture-login')
        self.assertTrue(end['switches'][-1]['success'])
        self.bridge.call('leave')
        end=self.bridge.call('sudo','root')
        self.assertEqual(end['environments'][-1]['effective_user'],'root')
        self.bridge.call('leave')
        end=self.bridge.call('su','missing')
        self.assertEqual(end['error_type'],'CredentialsRequiredError')
        self.assertFalse(end['switches'][-1]['success'])
        end=self.bridge.call('su','not-declared')
        self.assertEqual(end['error_type'],'PermissionError')
        self.bridge.call('su','blocked')
        attempts=self.bridge.session.switch_attempts
        end=self.bridge.call('sudo','root')
        self.assertEqual(end['error_type'],'PermissionError')
        self.assertEqual(self.bridge.session.switch_attempts,attempts)
        text=json.dumps(self.bridge.snapshot())
        self.assertNotIn(self.bridge.session.synthetic_password,text)
        self.bridge.call('leave')
        self.assertEqual(self.bridge.call('submit','getpass()')['error_type'],'CredentialsRequiredError')

    def test_secret_bearing_auth_exception_is_not_serialized(self):
        self.open('simulated',fault='auth_failure')
        end=self.bridge.call('su','operator')
        self.assertEqual(end['error_type'],'PermissionError')
        self.assertFalse(end['switches'][-1]['success'])
        end=self.bridge.call('submit','$.su("operator")')
        self.assertEqual(end['state'],'failed')
        self.assertNotIn(self.bridge.session.synthetic_password,json.dumps(self.bridge.snapshot()))
        self.assertEqual(self.bridge.session.switch_attempts,2)
        self.assertEqual(self.bridge.call('close')['session_reuse'],'confirmed')

    def test_faults_initialization_disconnect_cleanup_restoration(self):
        for fault in ['initialization','disconnect','cleanup','restoration']:
            bridge=Bridge(EVIDENCE/('fault-'+fault+'.jsonl'))
            try:
                event=bridge.call('open','simulated',fault=fault)
                if fault=='initialization':
                    self.assertEqual(event['error_type'],'ConsoleInitializationError')
                    self.assertEqual(event['open_fixture_layers'],0)
                else:
                    self.assertEqual(event['state'],'ready')
                    if fault=='restoration':
                        bridge.call('su','operator')
                        event=bridge.call('leave')
                    else: event=bridge.call('close')
                    self.assertEqual(event['error_type'],'ConsoleCleanupError')
                self.assertEqual(event['session_reuse'],'unknown')
                self.assertEqual(event['state'],'failed')
                self.assertFalse(event['owner_closed'])
                self.assertFalse(event['ancestor_closed'])
                self.assertTrue(all(not x['identity_verified'] for x in event['environments']))
                before=bridge.session.switch_attempts
                refused=bridge.call('reuse')
                self.assertEqual(refused['error_type'],'RuntimeError')
                self.assertEqual(bridge.session.switch_attempts,before)
            finally: bridge.stop()

    def test_active_channel_loss_has_unknown_reuse(self):
        self.open('simulated',fault='channel_disconnect')
        self.bridge.call('start','sleep 10')
        end=self.wait()
        self.assertEqual((end['state'],end['session_reuse']),('failed','unknown'))
        self.assertTrue(all(not e['identity_verified'] for e in end['environments']))
        end=self.bridge.call('close')
        self.assertEqual(end['error_type'],'ConsoleCleanupError')
        self.assertFalse(end['owner_closed'])

    def test_creator_thread_and_synchronous_python_limit(self):
        self.open()
        creator=self.bridge.snapshot()['current']['worker_thread']
        import threading
        self.assertNotEqual(creator,threading.get_ident())
        with self.assertRaises(RuntimeError): self.bridge.console.poll()
        self.bridge.call('submit','for n in range(2):')
        self.assertEqual(self.bridge.call('interrupt')['state'],'ready')
        future=self.bridge.request('submit','import time; time.sleep(.4)')
        time.sleep(.1)
        self.assertFalse(future.done())
        self.assertIsInstance(self.bridge.snapshot(),dict)
        queued=self.bridge.request('interrupt')
        self.assertFalse(queued.done())
        future.result(3); queued.result(3)
        self.assertEqual({x['worker_thread'] for x in self.bridge.events},{creator})

if __name__=='__main__': unittest.main(verbosity=2)
