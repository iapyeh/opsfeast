"""Unified execution entrypoint regressions; synthetic actors only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import recipe_runner as runner
import inventory_jobs as service
import recipe_cli
import test_inventory_jobs as jobs
from attribution_fixture import copy_recipe
from opsfeast import ConfigError
from recipe_test_support import recipe_main


class UnifiedRunnerTests(unittest.TestCase):
    setUp=jobs.InventoryJobTests.setUp
    enable=jobs.InventoryJobTests.enable

    def test_no_standalone_entrypoint_or_internal_cli(self):
        self.assertFalse((ROOT/'tools/run_recipe.py').exists())
        self.assertFalse(hasattr(runner,'main'))
        with self.assertRaises(TypeError):
            runner.run(self.root,'node')

    def test_public_inventory_run_routes_to_same_job_service(self):
        self.enable()
        actor=jobs.Actor()
        @contextlib.contextmanager
        def connected(*args,**kwargs):
            yield actor
        @contextlib.contextmanager
        def selected(session,config,host,timeout,evidence,**kwargs):
            evidence.update(actual_identity={'username':'synthetic','effective_uid':1000},mode='user')
            yield actor
        with patch.object(service,'connected',connected), patch.object(service,'collection_actor',selected):
            report,path=runner.run(self.root,'node',recipe='system/inventory/overview',session_class=jobs.Actor)
        self.assertIn(report['status'],('success','partial'))
        self.assertEqual(len(report['groups']),10)
        self.assertNotIn('observations',report)
        self.assertNotIn('inventory',report)
        self.assertEqual(report['retention']['status'],'stored')
        self.assertEqual(report['retention_snapshot']['retention']['contract'],'inventory-job-observations')
        self.assertEqual(json.loads(path.read_text()),report)
        self.assertFalse((self.root/'host-facts').exists())

    def test_public_batch_delegates_inventory_without_an_access_gate(self):
        report={'status':'success','reason_code':'synthetic','result_path':None}
        with patch.object(service,'collect_host',return_value=report) as collect, \
                patch('access_check.check_many',side_effect=AssertionError('no separate access gate')), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code=recipe_main(['system/inventory/overview','--host','node','--root',str(self.root),'--json'])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out.getvalue())['status'],'success')
        self.assertTrue(collect.call_args.kwargs['save'])
        self.assertEqual(collect.call_args.kwargs['reference'],'system/inventory/overview')

    def candidate(self):
        candidate=self.root/'recipes/candidate'
        copy_recipe(service.BUNDLE,candidate)
        return candidate

    def test_snapshot_descriptor_is_rejected_before_runtime(self):
        candidate=self.candidate()
        metadata=yaml.safe_load((candidate/'recipe.yaml').read_text())
        metadata['descriptor_version']='0.2.0'
        metadata.pop('collection')
        (candidate/'recipe.yaml').write_text(yaml.safe_dump(metadata))
        with patch.object(runner,'load_runtime') as runtime, self.assertRaises(ConfigError):
            runner.run(self.root,'node',recipe=':candidate')
        runtime.assert_not_called()
        self.assertFalse((self.root/'observations').exists())

    def test_inventory_write_declaration_is_rejected_before_connection(self):
        candidate=self.candidate()
        metadata=yaml.safe_load((candidate/'recipe.yaml').read_text())
        metadata['access_mode']='write'
        (candidate/'recipe.yaml').write_text(yaml.safe_dump(metadata))
        with patch.object(service,'connected') as connect:
            with self.assertRaises(ConfigError):
                runner.run(self.root,'node',recipe=':candidate')
            with self.assertRaises(ConfigError):
                service.collect_host(self.root,'node',reference=':candidate',save=False)
        connect.assert_not_called()

    def test_removed_flags_are_usage_errors_without_runtime(self):
        for flags in (['--dryrun'],['--force'],['--recipe','system/inventory/overview']):
            with self.subTest(flags=flags), patch.object(runner,'run') as run, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                recipe_main(['system/inventory/overview','--host','node',*flags])
            run.assert_not_called()

    def test_registered_relative_and_absolute_paths_use_current_collector(self):
        self.candidate()
        for reference in (':candidate','./recipes/candidate',str(self.root/'recipes/candidate')):
            with self.subTest(reference=reference), \
                    patch.object(service,'collect_host',return_value={'status':'success','reason_code':'synthetic','result_path':None}) as collect, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(recipe_main([reference,'--host','node','--root',str(self.root),'--json']),0)
            self.assertTrue(collect.call_args.kwargs['save'])

    def test_inventory_storage_names_preserve_time_order_and_uniqueness(self):
        first=runner.inventory_result_filename('2026-10-14T08:00:00.1+08:00')
        second=runner.inventory_result_filename('2026-10-14T00:00:00.9Z')
        later=runner.inventory_result_filename('2026-10-14T00:00:01Z')
        self.assertTrue(first.startswith('20261014T000000Z-inventory-system-'))
        self.assertNotEqual(first,second)
        self.assertLess(first,later)
        with self.assertRaises(ValueError):
            runner.inventory_result_filename('2026-10-14T00:00:00')

    def test_failed_receipt_replacement_preserves_raw_and_path(self):
        path=self.root/'raw.json'
        runner.save_report(path,{'status':'success'})
        report={'status':'success','result_path':str(path)}
        with patch.object(runner,'save_report',side_effect=OSError('private path')):
            runner.save_receipt(path,report)
        self.assertEqual(json.loads(path.read_text()),{'status':'success'})
        self.assertEqual(report['retention']['reason_code'],'receipt_save_failed')
        self.assertNotIn('private path',json.dumps(report))
        self.assertEqual(report['result_path'],str(path))
