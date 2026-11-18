"""Workflow rivers use existing Console records; only temporary stores/fake jobs."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from opsfeast import ConfigError
from opsfeast.console_records import Records
from opsfeast.workflow_river import WorkflowRiver


class WorkflowRiverTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.records=Records(self.root/'records')
        self.river=WorkflowRiver(self.records,profile='synthetic',host_id='fake-host',title='Synthetic workflow',
            reference=':synthetic/workflow',run_id='synthetic-run',origin='http://localhost:59000')

    def contents(self):
        return [(b,self.records.content(self.river.session_id,b['id'])['text']) for b in self.records.snapshot(self.river.session_id)['blocks']]

    def job(self,exitcode=0):
        result=SimpleNamespace(exitcode=exitcode,stdout='first\nsecond\n',stderr='warning\n',
            stop_reason='completed',termination_status='confirmed',stdout_truncated=False,stderr_truncated=False)
        river=self.river
        class Job:
            stage=0
            stopped=False
            @property
            def done(self):
                # Command is recorded before start; output arrives before command completion.
                if self.stage==1:
                    blocks=river.records.snapshot(river.session_id)['blocks']
                    assert next(b for b in blocks if b['kind']=='stdout')['size']>0
                    assert next(b for b in blocks if b['kind']=='command')['status']=='streaming'
                return self.stage>=2
            @property
            def stdout(self):return 'first\n' if self.stage<2 else result.stdout
            @property
            def stderr(self):return '' if self.stage<2 else result.stderr
            def wait(self):return result
            def stop(self):self.stopped=True;return result
        return Job(),result

    def test_streamed_command_outputs_results_and_host_history_are_one_river(self):
        job,receipt=self.job();session=Mock();session.start.return_value=job
        with patch('opsfeast.workflow_river.time.sleep',side_effect=lambda _:setattr(job,'stage',job.stage+1)):
            result=self.river.execute(session,['/opt/reviewed','--value','31.25'],timeout=60)
        self.assertIs(result,receipt);self.assertTrue(job.stopped)
        session.start.assert_called_once_with(['/opt/reviewed','--value','31.25'],timeout=60,check=False)
        texts=self.contents()
        self.assertEqual(next(text for b,text in texts if b['kind']=='stdout'),'first\nsecond\n')
        self.assertEqual(next(text for b,text in texts if b['kind']=='stderr'),'warning\n')
        self.assertTrue(all(b['status']=='completed' for b,text in texts))
        history=self.records.list_sessions('synthetic / fake-host')['sessions']
        self.assertEqual(history[0]['session_id'],self.river.session_id)
        self.assertEqual(self.records.list_sessions('other / fake-host')['sessions'],[])

    def test_failed_start_or_timeout_closes_blocks_without_retry(self):
        for error in (RuntimeError('synthetic'),TimeoutError('synthetic')):
            with self.subTest(error=type(error).__name__):
                session=Mock();session.start.side_effect=error
                with self.assertRaises(type(error)):self.river.execute(session,['synthetic'],timeout=1)
                session.start.assert_called_once()
        self.assertFalse(any(b['status']=='streaming' for b,text in self.contents()))

    def test_nonzero_result_remains_failed_but_output_capture_completes(self):
        job,result=self.job(exitcode=7);job.stage=2
        session=Mock();session.start.return_value=job
        self.assertEqual(self.river.execute(session,['synthetic'],timeout=1).exitcode,7)
        self.assertEqual(next(b['status'] for b,text in self.contents() if b['kind']=='command'),'failed')

    def test_truncated_output_is_never_marked_complete(self):
        job,result=self.job();job.stage=2;result.stdout_truncated=True
        session=Mock();session.start.return_value=job
        self.river.execute(session,['synthetic'],timeout=1)
        self.assertEqual(next(b['status'] for b,text in self.contents() if b['kind']=='stdout'),'failed')

    def test_progress_and_completion_keep_partial_business_outcome(self):
        self.river.progress('waiting for browser');self.river.progress('validated quote')
        self.river.complete({'status':'partial','reason_code':'business_unverified','connected':True,
            'data':{'business_outcome':'unverified','mail_delivery':'unknown'}},Path('/synthetic/result.json'))
        text=self.contents()[-1][1]
        self.assertIn('business_unverified',text);self.assertIn('unknown',text)
        self.assertFalse(any(b['status']=='streaming' for b,text in self.contents()))

    def test_record_failure_before_dispatch_never_starts_job(self):
        session=Mock()
        with patch.object(self.records,'add_block',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):self.river.execute(session,['synthetic'],timeout=1)
        session.start.assert_not_called()

    def test_utf8_append_offsets_are_byte_counts(self):
        block=self.river.text('stdout','UTF8','臺灣銀行\n'*5000)
        full='';offset=0
        while True:
            result=self.records.content(self.river.session_id,block,offset)
            full+=result['text'];offset=result['next_offset']
            if offset==result['total_bytes']:break
        self.assertEqual(full,'臺灣銀行\n'*5000)

    def test_web_unavailable_stops_before_record_store_creation(self):
        from opsfeast.workflow_river import create
        opener=Mock();opener.open.side_effect=OSError('synthetic offline')
        with patch('opsfeast.core.Instance.open',return_value=SimpleNamespace(root=self.root)), \
             patch('opsfeast.core.Profile._from_config',return_value=SimpleNamespace(name='synthetic')), \
             patch('opsfeast.storage.resolve_data_root',return_value=self.root/'data'), \
             patch('opsfeast.web_settings.read_port',return_value=59000), \
             patch('opsfeast.workflow_river.build_opener',return_value=opener), \
             patch('opsfeast.workflow_river.Records') as records:
            with self.assertRaisesRegex(ConfigError,'Web unavailable'):
                create(self.root,object(),host_id='fake-host',title='Synthetic',reference=':fake',run_id='synthetic')
            records.assert_not_called()

    def test_keyboard_interrupt_keeps_interrupt_and_stops_owned_job(self):
        job,result=self.job();job.stage=2
        job.wait=Mock(side_effect=KeyboardInterrupt())
        session=Mock();session.start.return_value=job
        with self.assertRaises(KeyboardInterrupt):self.river.execute(session,['synthetic'],timeout=1)
        self.assertTrue(job.stopped)
        self.assertEqual(next(b['status'] for b,text in self.contents() if b['kind']=='command'),'interrupted')

    def test_released_sshscript_local_job_streams_without_ssh(self):
        import importlib.util
        if importlib.util.find_spec('sshscript') is None:self.skipTest('optional SSHScript absent')
        import contextlib,sys
        from sshscript import Session
        with contextlib.closing(Session()) as session:
            result=self.river.execute(session,[sys.executable,'-u','-c',
                "import sys,time;print('synthetic first');time.sleep(.12);print('synthetic second');print('synthetic warning',file=sys.stderr)"],timeout=5)
        self.assertEqual(result.exitcode,0)
        texts=self.contents()
        self.assertEqual(next(text for b,text in texts if b['kind']=='stdout'),'synthetic first\nsynthetic second\n')
        self.assertEqual(next(text for b,text in texts if b['kind']=='stderr'),'synthetic warning\n')
