"""Original bounded streams, retained evidence and collapsed current-page output."""
import copy
import html
import json
from pathlib import Path
import runpy
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import host_vault
import inventory_jobs
import retention_store
import vault_content
from opsfeast import ConfigError
import test_inventory_jobs as fixtures

CAPTURE=runpy.run_path(str(ROOT/'recipes/system/inventory/overview/capture.py'))


class LocalShell:
    def exec_command(self,argv,**options):
        result=subprocess.run(argv,capture_output=True,text=True,timeout=options['command_timeout'])
        return SimpleNamespace(stdout=result.stdout,stderr=result.stderr,exitcode=result.returncode)


class StreamCaptureTests(unittest.TestCase):
    def capture(self,command):
        evidence={}
        output,reason=CAPTURE['capture'](LocalShell(),command,5,evidence)
        return output,reason,evidence

    def test_separate_streams_preserve_whitespace_exit_and_marker_like_text(self):
        output,reason,evidence=self.capture("printf ' df output\\n\\n__OPSFEAST_EXIT_77\\n'; printf 'diagnostic\\n\\n' >&2; false")
        self.assertIsNone(reason)
        self.assertEqual(output,' df output\n\n__OPSFEAST_EXIT_77\n')
        self.assertEqual(evidence['stdout'],output)
        self.assertEqual(evidence['stderr'],'diagnostic\n\n')
        self.assertEqual(evidence['exitcode'],1)
        self.assertFalse(evidence['stdout_truncated'])

    def test_stdout_and_stderr_are_individually_bounded(self):
        for redirect,stream in (('', 'stdout'),(' >&2','stderr')):
            with self.subTest(stream=stream):
                _,reason,evidence=self.capture("head -c 262145 /dev/zero | tr '\\000' x"+redirect)
                self.assertEqual(reason,'output_limit')
                self.assertTrue(evidence[stream+'_truncated'])
                self.assertEqual(len(evidence[stream].encode()),262144)

    def test_empty_streams_are_recorded_and_unicode_is_preserved(self):
        _,reason,evidence=self.capture("printf '測試\\n'")
        self.assertIsNone(reason)
        self.assertEqual(evidence['stdout'],'測試\n')
        self.assertEqual(evidence['stderr'],'')

    def test_schema_regeneration_preserves_command_output_contract(self):
        import build_inventory_catalog
        from contextlib import redirect_stdout
        import io
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)
            recipe=temporary/'recipes/system/inventory/overview'
            recipe.mkdir(parents=True)
            shutil.copyfile(ROOT/'recipes/system/inventory/overview/properties.py',recipe/'properties.py')
            with patch.object(build_inventory_catalog,'__file__',str(temporary/'tools/build_inventory_catalog.py')),redirect_stdout(io.StringIO()):
                build_inventory_catalog.main()
            generated=json.loads((recipe/'job-retention.schema.json').read_text())
        expected=json.loads((ROOT/'recipes/system/inventory/overview/job-retention.schema.json').read_text())
        generated.pop('$comment');expected.pop('$comment')
        self.assertEqual(generated,expected)

    def test_partial_timeout_evidence_is_kept_without_inventing_stderr(self):
        exc=TimeoutError('synthetic timeout')
        exc.result=SimpleNamespace(stdout='partial stdout',exitcode=None)
        actor=SimpleNamespace(exec_command=lambda *a,**k: (_ for _ in ()).throw(exc))
        evidence={}
        with self.assertRaises(TimeoutError):CAPTURE['capture'](actor,'synthetic',1,evidence)
        self.assertEqual(evidence['stdout'],'partial stdout')
        self.assertIsNone(evidence['stderr'])


class CommandOutputDeliveryTests(unittest.TestCase):
    setUp=fixtures.InventoryJobTests.setUp
    enable=fixtures.InventoryJobTests.enable
    acquire=fixtures.InventoryJobTests.acquire

    def test_raw_retention_current_and_offline_rebuild_preserve_df_output(self):
        self.enable()
        result=self.acquire(fixtures.Actor(),save=True,properties=['storage.filesystems.used_percent'])
        raw=json.loads(Path(result['result_path']).read_text())
        probe=next(p for p in raw['probes'] if p['command']=='LC_ALL=C df -Pk')
        self.assertIn('/dev/example 100 82 18 82% /',probe['stdout'])
        self.assertEqual(probe['stderr'],'')
        record=retention_store.show(self.root,result['retention']['record_id'])
        self.assertEqual(next(p for p in record['data']['probes'] if p['id']==probe['id']),probe)
        path=next((self.root/'vault').rglob('current-system-inventory.md'))
        page=path.read_text()
        self.assertIn('## Command output',page)
        self.assertIn('<summary>LC_ALL=C df -Pk</summary>',page)
        self.assertIn(html.escape(probe['stdout']),page)
        self.assertNotIn('<details open',page)
        with patch.object(inventory_jobs,'collect_host',side_effect=AssertionError('no collection')):
            host_vault.rebuild(self.root)
        self.assertIn(probe['stdout'],path.read_text())

    def test_parser_failure_still_saves_original_stdout_and_stderr(self):
        from inventory_output_fixture import framed
        class InvalidJSONActor(fixtures.Actor):
            def exec_command(self,argv,**options):
                if 'ip -j address' in argv[-1]:
                    return SimpleNamespace(stdout=framed(argv[-1],'invalid-json\n__OPSFEAST_EXIT_0\n','diagnostic\n'),stderr='',exitcode=0)
                return super().exec_command(argv,**options)
        self.enable()
        result=self.acquire(InvalidJSONActor(),save=True,properties=['network.ipv4.address'])
        self.assertEqual(result['retention']['status'],'stored')
        data=retention_store.show(self.root,result['retention']['record_id'])['data']
        probe=next(p for p in data['probes'] if 'ip -j address' in p['command'])
        self.assertEqual(probe['stdout'],'invalid-json')
        self.assertEqual(probe['stderr'],'diagnostic\n')
        self.assertEqual(probe['status'],'failed')

    def test_mixed_age_view_uses_matching_source_outputs_and_deduplicates_shared_probes(self):
        self.enable()
        first=self.acquire(fixtures.Actor(),save=True,properties=['storage.filesystems.used_percent','storage.filesystems.available_bytes'])
        actor=fixtures.Actor();actor.percent=40
        self.acquire(actor,save=True,properties=['storage.filesystems.used_percent'])
        record=retention_store.query(self.root)['records'][-1]
        record=copy.deepcopy(record)
        record['data']['groups']=inventory_jobs.latest_groups(retention_store.query(self.root)['records'])
        page=vault_content.render_current(record)
        self.assertEqual(page.count('<summary>LC_ALL=C df -Pk</summary>'),2)
        self.assertIn('82% /',page)
        self.assertIn('40% /',page)
        self.assertIn(first['retention']['record_id'],page)

    def test_html_and_markdown_in_outputs_remain_literal_code(self):
        self.enable()
        result=self.acquire(fixtures.Actor(),save=True,properties=['storage.filesystems.used_percent'])
        record=retention_store.show(self.root,result['retention']['record_id'])
        probe=record['data']['probes'][0]
        probe['stdout']='</code></pre></details>\n## Injected\n```\n'
        probe['stderr']='problem <script> & detail\n'
        probe['stderr_truncated']=True
        page=vault_content.render_current(record)
        self.assertIn(html.escape(probe['stdout']),page)
        self.assertIn('problem &lt;script&gt; &amp; detail',page)
        self.assertIn('stderr: truncated',page)
        self.assertNotIn('[Injected]',page)

    def test_unrecorded_old_output_is_not_reconstructed_and_validation_rejects_bad_streams(self):
        self.enable()
        result=self.acquire(fixtures.Actor(),save=True,properties=['storage.filesystems.used_percent'])
        record=retention_store.show(self.root,result['retention']['record_id'])
        for probe in record['data']['probes']:
            for key in ('stdout','stderr','stdout_truncated','stderr_truncated'):probe.pop(key,None)
        page=vault_content.render_current(record)
        self.assertIn('Not recorded.',page)
        validator=runpy.run_path(str(ROOT/'recipes/system/inventory/overview/job_retention.py'))['validate']
        for bad in (1,'x'*262145):
            changed=copy.deepcopy(record['data']);changed['probes'][0]['stdout']=bad
            with self.assertRaises(ConfigError):validator(changed)
