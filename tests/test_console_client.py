import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from opsfeast.console_client import main

class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.token=Path(self.tmp.name)/'token';self.token.write_text('fixture-token')
        self.args=['console_client','--token-file',str(self.token)]
    def test_create_preserves_json_body_and_does_not_print_credential(self):
        body={'session_id':'11af0ac8-f21c-49ec-a5de-8f99d8116aac','title':'測試','host_id':'synthetic','work_id':None}
        output=io.StringIO()
        with patch('sys.argv',self.args+['create']),patch('sys.stdin',io.StringIO(json.dumps(body))),patch('opsfeast.console_client.urlopen',return_value=io.BytesIO(b'{"seq":0}')) as send,contextlib.redirect_stdout(output):
            self.assertEqual(main(),0)
        req=send.call_args.args[0]
        self.assertEqual(json.loads(req.data),body)
        self.assertNotIn('fixture-token',output.getvalue())
        self.assertEqual(send.call_count,1)
    def test_reader_interrupt_exits_cleanly_without_retry(self):
        with patch('sys.argv',self.args+['stream','--session','11af0ac8-f21c-49ec-a5de-8f99d8116aac']),patch('opsfeast.console_client.urlopen',side_effect=KeyboardInterrupt) as send:
            self.assertEqual(main(),130)
            self.assertEqual(send.call_count,1)
    def test_remote_origin_rejected_before_network(self):
        with patch('sys.argv',self.args+['--url','http://example.invalid','create']),patch('opsfeast.console_client.urlopen') as send,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main()
            send.assert_not_called()
    def test_wait_delivers_saved_response_and_cursor(self):
        data={'seq':7,'responses':[{'type':'response.created','response':{'choice':'approve'}}]}
        output=io.StringIO()
        with patch('sys.argv',self.args+['wait','--session','11af0ac8-f21c-49ec-a5de-8f99d8116aac','--after','3']),patch('opsfeast.console_client.urlopen',return_value=io.BytesIO(json.dumps(data).encode())) as send,contextlib.redirect_stdout(output):
            self.assertEqual(main(),0)
        self.assertEqual(json.loads(output.getvalue()),data)
        self.assertIn('/responses?after=3&wait=',send.call_args.args[0].full_url)
    def test_wait_timeout_is_not_a_decision(self):
        output=io.StringIO()
        with patch('sys.argv',self.args+['wait','--session','11af0ac8-f21c-49ec-a5de-8f99d8116aac','--timeout','1']),patch('opsfeast.console_client.time.monotonic',side_effect=[0,0,2]),patch('opsfeast.console_client.urlopen',return_value=io.BytesIO(b'{"seq":5,"responses":[]}')),contextlib.redirect_stdout(output):
            self.assertEqual(main(),0)
        self.assertEqual(json.loads(output.getvalue()),{'seq':5,'responses':[],'timed_out':True})
