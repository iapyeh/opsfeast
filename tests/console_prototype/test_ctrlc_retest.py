"""Additional real-PTY consumer checks for the Ctrl-C candidate; no patches."""
import json
import os
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from adapter import Bridge

BASE = Path(os.environ.get('CONSOLE_RETEST_EVIDENCE', '/private/tmp/opsfeast-console-ctrlc-extra'))
BASE.mkdir(exist_ok=True)


class CtrlCConsumerRetest(unittest.TestCase):
    def bridge(self, suffix=''):
        bridge = Bridge(BASE / (self._testMethodName + suffix + '.jsonl'))
        self.addCleanup(bridge.stop)
        self.assertEqual(bridge.call('open', 'local')['state'], 'ready')
        self.assertEqual(bridge.call('enter')['state'], 'waiting_input')
        return bridge

    def ready(self, bridge, seconds=7):
        until = time.monotonic()+seconds
        while time.monotonic()<until:
            update = bridge.call('poll')
            if update['state'] != 'running':
                self.assertEqual(update['state'], 'waiting_input', update)
                return update
            time.sleep(.03)
        self.fail('No structured waiting_input within the bounded test deadline')

    def stable(self, bridge):
        # No extra program input is sent to provoke another prompt.
        for _ in range(4):
            self.assertEqual(bridge.call('poll')['state'], 'waiting_input')
            time.sleep(.03)

    def finish(self, bridge, ending):
        update = bridge.call('input', 'print("AFTER_INTERRUPT")')
        self.assertEqual(update['state'], 'waiting_input')
        self.assertIn('AFTER_INTERRUPT', update['stdout'])
        bridge.call(ending)
        if ending != 'close':
            self.assertEqual(len(bridge.snapshot()['current']['environments']), 1)
        update = bridge.call('close')
        self.assertEqual((update['state'], update['session_reuse']), ('closed', 'confirmed'))
        self.assertFalse(update['owner_closed'])
        probe = bridge.call('reuse')
        self.assertEqual((probe['owner_reuse_exitcode'], probe['owner_reuse_stdout']), (0, 'OWNER_REUSED'))
        bridge.stop()
        self.assertTrue(bridge.session.closed)

    def test_idle_interrupt_stable_poll_then_input_and_each_cleanup(self):
        for ending in ('eof', 'leave', 'close'):
            with self.subTest(ending=ending):
                bridge = self.bridge('-'+ending)
                update = bridge.call('interrupt')
                self.assertEqual(update['state'], 'waiting_input')
                self.assertEqual(update['error_type'], 'KeyboardInterrupt')
                self.stable(bridge)
                self.finish(bridge, ending)

    def test_running_program_interrupt_recovers_without_probe_input(self):
        bridge = self.bridge()
        update = bridge.call('input', 'import time; print("BUSY",flush=True); time.sleep(20)', timeout=.15)
        self.assertEqual(update['state'], 'running')
        # This fixture marker only proves execution started; readiness is still
        # decided exclusively by ConsoleUpdate.state after interrupt/poll.
        until = time.monotonic()+2
        while 'BUSY' not in ''.join(x['stdout'] for x in bridge.events) and time.monotonic()<until:
            bridge.call('poll')
            time.sleep(.03)
        self.assertIn('BUSY', ''.join(x['stdout'] for x in bridge.events))
        update = bridge.call('interrupt')
        self.assertEqual(update['state'], 'waiting_input')
        self.assertEqual(update['error_type'], 'KeyboardInterrupt')
        self.stable(bridge)
        self.finish(bridge, 'eof')

    def test_ignored_ctrlc_stays_running_until_program_returns_to_prompt(self):
        bridge = self.bridge()
        bridge.call('input', 'import signal,time; signal.signal(signal.SIGINT,signal.SIG_IGN)')
        update = bridge.call('input', 'print("IGNORING",flush=True); time.sleep(4.5)', timeout=.15)
        self.assertEqual(update['state'], 'running')
        update = bridge.call('interrupt')
        self.assertEqual((update['state'], update['error_type']), ('running', 'KeyboardInterrupt'))
        self.assertEqual(bridge.call('poll')['state'], 'running')
        self.ready(bridge)
        self.stable(bridge)
        self.finish(bridge, 'leave')

    def test_delayed_prompt_after_interrupt_recovers_through_poll(self):
        bridge = self.bridge()
        source = 'import time\ntry:\n print("DELAYING",flush=True); time.sleep(20)\nexcept KeyboardInterrupt:\n time.sleep(3.5)'
        update = bridge.call('input', 'exec('+repr(source)+')', timeout=.15)
        self.assertEqual(update['state'], 'running')
        update = bridge.call('interrupt')
        self.assertEqual((update['state'], update['error_type']), ('running', 'KeyboardInterrupt'))
        self.ready(bridge)
        self.stable(bridge)
        self.finish(bridge, 'close')

    def test_program_exit_on_interrupt_keeps_actual_nonzero_status(self):
        bridge = self.bridge()
        bridge.call('input', 'import signal; signal.signal(signal.SIGINT,signal.SIG_DFL)')
        update = bridge.call('interrupt')
        self.assertEqual((update['state'], update['exitcode']), ('failed', 130))
        self.assertEqual(len(update['environments']), 1)
        self.assertEqual(bridge.call('close')['session_reuse'], 'confirmed')
        self.assertEqual(bridge.call('reuse')['owner_reuse_exitcode'], 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
