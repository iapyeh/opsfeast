"""PID-marker and shell-launcher tests; isolated storage, no managed hosts."""
import contextlib
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from opsfeast.web.process import claim, FILENAME, ProcessMarkerError

ROOT=Path(__file__).resolve().parents[1]


class WebProcessTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.marker=self.root/FILENAME

    def test_actual_pid_permissions_and_normal_cleanup(self):
        with claim(self.root) as path:
            self.assertEqual(path,self.marker)
            self.assertEqual(path.read_text(),str(os.getpid())+'\n')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
        self.assertFalse(self.marker.exists())

    def test_exception_cleanup_preserves_replacement_file(self):
        with self.assertRaises(RuntimeError),claim(self.root):raise RuntimeError('synthetic startup failure')
        self.assertFalse(self.marker.exists())
        with claim(self.root):
            replacement=self.root/'replacement';replacement.write_text('replacement\n');os.replace(replacement,self.marker)
        self.assertEqual(self.marker.read_text(),'replacement\n')

    def test_live_pid_warns_without_start_or_file_change(self):
        self.marker.write_text(str(os.getpid())+'\n');before=self.marker.read_bytes()
        with self.assertRaises(ProcessMarkerError) as error:
            with claim(self.root):self.fail('must not start')
        self.assertEqual(error.exception.exit_code,2);self.assertIn('still running',str(error.exception))
        self.assertEqual(self.marker.read_bytes(),before)

    def test_dead_pid_stays_for_agent_recovery(self):
        self.marker.write_text('12345\n')
        with patch('opsfeast.web.process.os.kill',side_effect=ProcessLookupError),self.assertRaisesRegex(ProcessMarkerError,'Stale'):
            with claim(self.root):self.fail('must not start')
        self.assertEqual(self.marker.read_text(),'12345\n')

    def test_inaccessible_pid_refuses_start(self):
        self.marker.write_text('12345\n')
        with patch('opsfeast.web.process.os.kill',side_effect=PermissionError),self.assertRaisesRegex(ProcessMarkerError,'cannot be inspected'):
            with claim(self.root):self.fail('must not start')
        self.assertTrue(self.marker.exists())

    def test_invalid_and_symlink_markers_are_not_repaired(self):
        for value in ('','0','-1','not-pid','9'*100):
            with self.subTest(value=value):
                self.marker.write_text(value)
                with self.assertRaises(ProcessMarkerError):
                    with claim(self.root):self.fail('must not start')
                self.assertEqual(self.marker.read_text(),value)
        self.marker.unlink();target=self.root/'target';target.write_text('keep');self.marker.symlink_to(target)
        with self.assertRaises(ProcessMarkerError):
            with claim(self.root):self.fail('must not start')
        self.assertTrue(self.marker.is_symlink());self.assertEqual(target.read_text(),'keep')

    def child(self,body):
        code='import sys,time,signal\nfrom pathlib import Path\nfrom opsfeast.web.process import claim\nwith claim(Path(sys.argv[1])):\n '+body.replace('\n','\n ')
        process=subprocess.Popen([sys.executable,'-B','-u','-c',code,str(self.root)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda:process.poll() is None and process.kill())
        deadline=time.monotonic()+5
        while not self.marker.exists() or not self.marker.read_text().strip():
            if process.poll() is not None:self.fail(process.communicate()[1])
            if time.monotonic()>deadline:self.fail('marker startup deadline')
            time.sleep(.01)
        return process

    def test_signals_remove_actual_child_pid_and_duplicate_is_blocked(self):
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):
            with self.subTest(signal=sig):
                process=self.child('time.sleep(30)')
                self.assertEqual(int(self.marker.read_text()),process.pid)
                with self.assertRaises(ProcessMarkerError):
                    with claim(self.root):self.fail('concurrent launch')
                process.send_signal(sig);process.communicate(timeout=5)
                self.assertFalse(self.marker.exists())

    def test_forced_kill_leaves_stale_marker_for_agent(self):
        process=self.child('time.sleep(30)');process.kill();process.communicate(timeout=5)
        with self.assertRaisesRegex(ProcessMarkerError,'Stale'):
            with claim(self.root):self.fail('must not repair')
        self.assertEqual(int(self.marker.read_text()),process.pid)

    def test_shell_works_from_other_directory_with_quoted_arguments(self):
        fake=self.root/'fake python';fake.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@"\n');fake.chmod(0o700)
        response=subprocess.run([str(ROOT/'tools/start_web.sh'),'--data-root','/synthetic/path with spaces','--port','18741'],cwd=self.root,env={**os.environ,'OPSFEAST_PYTHON':str(fake)},text=True,capture_output=True,timeout=5)
        self.assertEqual(response.returncode,0,response.stderr)
        self.assertEqual(response.stdout.splitlines(),[str(ROOT),'-B','-u','-m','opsfeast.web','--data-root','/synthetic/path with spaces','--port','18741'])
        response=subprocess.run([str(ROOT/'tools/start_web.sh')],cwd=self.root,env={**os.environ,'OPSFEAST_PYTHON':str(self.root/'missing')},text=True,capture_output=True,timeout=5)
        self.assertNotEqual(response.returncode,0);self.assertIn('not executable',response.stderr)

    def test_cli_bind_failure_removes_marker_and_preserves_port(self):
        import argparse
        from opsfeast.web import __main__ as web
        from opsfeast.storage import initialize_data_root
        product=self.root/'product';product.mkdir();data=self.root/'data';initialize_data_root(product,data)
        parser=argparse.ArgumentParser()
        with claim(data),patch('opsfeast.web_settings.bind_server',side_effect=OSError('synthetic occupied port')):
            with self.assertRaises(SystemExit):web.serve(type('Args',(),{'port':None})(),data,parser,None,None,product/'web')
        self.assertFalse((data/FILENAME).exists())

    def test_real_http_server_marker_duplicate_shell_and_sigterm_cleanup(self):
        from opsfeast.core import Instance
        from opsfeast.storage import initialize_data_root
        import io,json
        from urllib.request import urlopen
        from urllib.error import URLError
        product=self.root/'isolated-product';product.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):Instance.open(product).init_profile()
        data=self.root/'isolated-data';initialize_data_root(product,data)
        code="""import sys
from pathlib import Path
import opsfeast.web.app as app
factory=app.create_app
product=Path(sys.argv[1])
app.create_app=lambda **kwargs:factory(product,**kwargs)
from opsfeast.web.__main__ import main
sys.argv=['opsfeast.web','--data-root',sys.argv[2]]
main()
"""
        process=subprocess.Popen([sys.executable,'-B','-u','-c',code,str(product),str(data)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda:process.poll() is None and process.kill())
        marker=data/FILENAME;endpoint=data/'web-server.json';deadline=time.monotonic()+10
        try:
            while True:
                if process.poll() is not None:self.fail(process.communicate()[1])
                if time.monotonic()>deadline:self.fail('HTTP startup deadline')
                if endpoint.exists():
                    port=json.loads(endpoint.read_text())['port']
                    try:
                        with urlopen('http://127.0.0.1:'+str(port)+'/',timeout=.5) as response:
                            if response.status==200:break
                    except (URLError,TimeoutError):pass
                time.sleep(.02)
            self.assertEqual(int(marker.read_text()),process.pid)
            duplicate=subprocess.run([str(ROOT/'tools/start_web.sh'),'--data-root',str(data)],cwd=self.root,text=True,capture_output=True,timeout=5)
            self.assertEqual(duplicate.returncode,2,duplicate.stderr);self.assertIn('still running',duplicate.stderr)
            self.assertEqual(int(marker.read_text()),process.pid)
            process.terminate();process.communicate(timeout=10)
            self.assertFalse(marker.exists());self.assertTrue(endpoint.exists())
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=5)

    def test_nohup_ignore_is_preserved(self):
        previous=signal.signal(signal.SIGHUP,signal.SIG_IGN)
        try:
            with claim(self.root):self.assertEqual(signal.getsignal(signal.SIGHUP),signal.SIG_IGN)
        finally:signal.signal(signal.SIGHUP,previous)
        self.assertFalse(self.marker.exists())
