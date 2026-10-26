"""Public cross-instance portability, import conflicts and archive recovery regressions."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import copy
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from opsfeast import Instance, ConfigError
from opsfeast import transfer
from opsfeast.data_contract import validate
from opsfeast.recipe_install import plan as recipe_plan, install, execution_snapshot, fingerprint
from opsfeast.backup_check import portable_files
from test_core_api import Actor
import recipe_runner
from recipe_catalog import choose, catalog
from recipe_packages import pack
from retention_store import Reader, records, archive_path

ROOT=Path(__file__).resolve().parents[1]
IDENTITY={'author':{'name':'Synthetic','contacts':['synthetic@example.invalid']},'license':'MIT'}
SCHEMA={'type':'object','required':['value'],'properties':{'value':{'type':'integer','minimum':0}},'additionalProperties':False}


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        for name in ('a','b'):(self.base/name).mkdir()
        with redirect_stdout(io.StringIO()):
            self.a=Instance.open(self.base/'a').init_profile()
            self.b=Instance.open(self.base/'b').init_profile()
        self.a.root.joinpath('hosts.yaml').write_text(json.dumps({'hosts':{'h':{'connection':{'local':True},'users':{'operator':{}}}}}))
        self.directory=self.a.root/'recipes/example';self.directory.mkdir(parents=True)
        self.meta={'descriptor_version':'0.3.0','id':'portable-example','version':'0.1.0',**IDENTITY,
            'runner':{'contract':'python-recipe','version':'0.1.0','entrypoint':'main.py'},'access_mode':'read',
            'retention':{'contract':'user-domain','version':'0.1.0','description':'Synthetic values','mode':'portable','data_schema':SCHEMA},
            'output':{'schema_version':'0.1.0'}}
        self.code="VERSION='0.1.0'\ndef execute(recipe):\n    return {'status':'success','reason_code':'sample','message':'Synthetic','data':{'value':7}}\n"
        self.write_recipe()

    def write_recipe(self):
        self.directory.joinpath('recipe.yaml').write_text(json.dumps(self.meta))
        self.directory.joinpath('main.py').write_text(self.code)
        self.directory.joinpath('README.md').write_text('# Synthetic recipe\n')
        self.directory.joinpath('LICENSE').write_text('Synthetic MIT fixture')

    def collect(self):
        with patch.object(recipe_runner,'REPOSITORY_ROOT',self.base/'a'):
            report,path=recipe_runner.run(self.a.root,'h',recipe=':example',session_class=Actor,runtime={'verification':'synthetic-transport'})
        self.assertEqual(report['status'],'success',report)
        self.assertEqual(report['retention']['status'],'stored',report)
        return report,path

    def package(self,name='data.zip',kinds=transfer.KINDS):
        path=self.base/name;transfer.export(self.a.root,path,kinds=kinds);return path

    def test_unregistered_recipe_retains_and_replays_data_without_candidate_import(self):
        raw,path=self.collect();record=Reader(self.a.root).query()['records'][0]
        self.assertEqual(record['data'],{'value':7})
        self.assertEqual(record['retention_definition']['mode'],'portable')
        self.directory.joinpath('main.py').write_text("raise RuntimeError('never import')")
        from retention_replay import ingest
        result=ingest(self.a.root,[path])
        self.assertEqual(result['status'],'success',result)

    def test_independent_observation_and_retention_packages_without_installed_recipe(self):
        self.collect()
        for kind in transfer.KINDS:
            package=self.package(kind+'.zip',(kind,))
            selected=transfer.import_plan(self.b.root,package)
            transfer.import_package(self.b.root,package,expected_plan=selected['sha256'])
            units=transfer.query(self.b.root,kind=kind)
            self.assertEqual(len(units),1)
            self.assertEqual(units[0]['kind'],kind)
        self.assertFalse((self.b.root/'services/objects.sqlite3').exists())
        self.assertEqual(len(transfer.imported(self.b.root)),2)
        self.assertEqual(transfer.catalog(self.a.root).keys(),transfer.catalog(self.b.root).keys())

    def test_merge_deduplicates_and_replace_only_matching_identities(self):
        self.collect();package=self.package();selected=transfer.import_plan(self.b.root,package)
        transfer.import_package(self.b.root,package,expected_plan=selected['sha256'])
        self.assertTrue(all(a['action']=='skip' for a in transfer.import_plan(self.b.root,package)['actions']))
        units=transfer.read_package(package)[1];unit=next(u for u in units if u['kind']=='retention');unit['payload']['data']['value']=8
        changed=self.base/'changed.zip';transfer.write_package(changed,[unit])
        conflict=transfer.import_plan(self.b.root,changed)
        self.assertEqual(conflict['actions'][0]['action'],'conflict')
        with self.assertRaises(ConfigError):transfer.import_package(self.b.root,changed,expected_plan=conflict['sha256'])
        replacement=transfer.import_plan(self.b.root,changed,'replace')
        transfer.import_package(self.b.root,changed,mode='replace',expected_plan=replacement['sha256'])
        self.assertEqual(transfer.query(self.b.root,kind='retention')[0]['payload']['data']['value'],8)
        self.assertEqual(len(transfer.query(self.b.root)),2)

    def test_stale_plan_and_missing_plan_never_import(self):
        self.collect();package=self.package();selected=transfer.import_plan(self.b.root,package)
        with self.assertRaises(ConfigError):transfer.import_package(self.b.root,package)
        transfer.import_package(self.b.root,package,expected_plan=selected['sha256'])
        with self.assertRaises(ConfigError):transfer.import_package(self.b.root,package,expected_plan=selected['sha256'])

    def test_schema_validation_and_identity_are_checked_before_any_write(self):
        self.collect();unit=transfer.query(self.a.root,kind='retention')[0]
        unit['payload']['data']['value']=-1
        with self.assertRaises(ConfigError):transfer.write_package(self.base/'bad.zip',[unit])
        unit['payload']['data']['value']=7;unit['origin']['host_id']='another-host'
        with self.assertRaises(ConfigError):transfer.write_package(self.base/'bad2.zip',[unit])
        self.assertFalse((self.b.root/'transfer/space.sqlite3').exists())

    def test_no_recipe_is_needed_to_export_imported_data_again(self):
        self.collect();original=self.package();p=transfer.import_plan(self.b.root,original)
        transfer.import_package(self.b.root,original,expected_plan=p['sha256'])
        repacked=self.base/'repacked.zip';transfer.export(self.b.root,repacked)
        self.assertEqual(transfer.read_package(original)[1],transfer.read_package(repacked)[1])

    def test_data_packages_preserve_saved_assessment_and_execution_identity(self):
        assessment={'label':'REVIEW NEEDED','severity':'warning','summary':'Synthetic finding.'}
        self.code=self.code.replace("'data':{'value':7}","'data':{'value':7},'assessment':"+repr(assessment))
        self.write_recipe()
        raw,_=self.collect()
        package=self.package()
        selected=transfer.import_plan(self.b.root,package)
        transfer.import_package(self.b.root,package,expected_plan=selected['sha256'])
        for unit in transfer.query(self.b.root):
            self.assertEqual(unit['payload']['assessment'],assessment)
            self.assertEqual(unit['payload']['execution_identity'],raw['execution_identity'])
        invalid=transfer.query(self.b.root,kind='retention')[0]
        invalid['payload']['assessment']['severity']='unknown'
        with self.assertRaises(ConfigError):transfer.write_package(self.base/'invalid-assessment.zip',[invalid])

    def test_archive_raw_only_preserves_retention_and_package_is_restorable(self):
        self.collect();destination=self.base/'raw-archive.zip'
        p=transfer.archive_plan(self.a.root,destination,kinds=('observation',),older_than=0)
        result=transfer.archive(self.a.root,destination,kinds=('observation',),older_than=None,before=p['cutoff'],expected_plan=p['sha256'])
        self.assertEqual(result['status'],'completed')
        self.assertGreater(result['bytes_reclaimed'],0)
        self.assertEqual(len(transfer.query(self.a.root,kind='observation')),0)
        self.assertEqual(len(Reader(self.a.root).query()['records']),1)
        selected=transfer.import_plan(self.b.root,destination);transfer.import_package(self.b.root,destination,expected_plan=selected['sha256'])
        self.assertEqual(len(transfer.query(self.b.root,kind='observation')),1)
        self.assertEqual(transfer.archive(self.a.root,resume=result['id'])['status'],'completed')

    def test_retention_archive_reclaims_sqlite_and_preserves_raw(self):
        self.collect();destination=self.base/'retention.zip'
        p=transfer.archive_plan(self.a.root,destination,kinds=('retention',),before='2099-01-01T00:00:00+00:00')
        result=transfer.archive(self.a.root,destination,kinds=('retention',),before=p['cutoff'],expected_plan=p['sha256'])
        self.assertEqual(result['status'],'completed')
        self.assertEqual(len(records(self.a.root)),0)
        self.assertEqual(len(transfer.query(self.a.root,kind='observation')),1)
        self.assertEqual(result['compaction'],'completed')
        self.assertEqual(transfer.read_package(destination)[1][0]['payload']['data'],{'value':7})

    def test_archive_failure_keeps_verified_package_and_resumes(self):
        self.collect();destination=self.base/'resume.zip'
        p=transfer.archive_plan(self.a.root,destination,before='2099-01-01T00:00:00+00:00')
        with patch('opsfeast.transfer._remove',side_effect=OSError('synthetic disk failure')):
            with self.assertRaisesRegex(ConfigError,'resume'):transfer.archive(self.a.root,destination,before=p['cutoff'],expected_plan=p['sha256'])
        receipt=transfer.receipts(self.a.root)[0]
        self.assertEqual(receipt['status'],'recoverable')
        self.assertEqual(len(transfer.read_package(destination)[1]),2)
        self.assertEqual(len(transfer.query(self.a.root)),2)
        self.assertEqual(transfer.archive(self.a.root,resume=receipt['id'])['status'],'completed')

    def test_archive_refuses_changed_package_on_resume(self):
        self.collect();destination=self.base/'broken.zip';p=transfer.archive_plan(self.a.root,destination,before='2099-01-01T00:00:00+00:00')
        with patch('opsfeast.transfer._remove',side_effect=OSError()):
            with self.assertRaises(ConfigError):transfer.archive(self.a.root,destination,before=p['cutoff'],expected_plan=p['sha256'])
        receipt=transfer.receipts(self.a.root)[0];destination.write_bytes(b'not an archive')
        with self.assertRaises(ConfigError):transfer.archive(self.a.root,resume=receipt['id'])
        self.assertEqual(len(transfer.query(self.a.root)),2)

    def test_exclusive_cutoff_and_recipe_scope(self):
        self.collect();units=transfer.query(self.a.root);time=units[0]['observed_at']
        selected=transfer.select(self.a.root,kinds=('observation',),before=time)
        self.assertEqual(selected['selected'],[])
        self.assertEqual(transfer.select(self.a.root,recipe=':other')['selected'],[])
        with self.assertRaises(ConfigError):transfer.select(self.a.root,older_than=-1)
        with self.assertRaises(ConfigError):transfer.archive_plan(self.a.root,self.a.root/'not-freeing-space.zip')

    def test_zip_traversal_and_digest_corruption_rejected(self):
        self.collect();package=self.package();manifest,units=transfer.read_package(package)
        malicious=self.base/'traversal.zip'
        with zipfile.ZipFile(malicious,'w') as z:
            z.writestr('../outside','data');z.writestr('MANIFEST.json','{}')
        with self.assertRaises(ConfigError):transfer.read_package(malicious)
        corrupted=self.base/'corrupt.zip'
        with zipfile.ZipFile(package) as src,zipfile.ZipFile(corrupted,'w') as dst:
            for name in src.namelist():dst.writestr(name,src.read(name) if name=='MANIFEST.json' else b'{}')
        with self.assertRaises(ConfigError):transfer.read_package(corrupted)
        self.assertFalse((self.base/'outside').exists())

    def recipe_package(self,name='recipe.zip'):
        package=self.base/name
        return Path(pack(choose(self.a.root,':example'),['recipe.yaml','main.py','README.md','LICENSE'],package)['path'])

    def test_recipe_install_conflict_replace_and_saved_before_image(self):
        package=self.recipe_package();p=recipe_plan(self.b.root,package,'example');install(self.b.root,package,'example',expected_plan=p['sha256'])
        same=recipe_plan(self.b.root,package,'example');self.assertEqual(same['action'],'skip')
        original=fingerprint(self.b.root/'recipes/example')
        self.code=self.code.replace("'value':7","'value':8");self.write_recipe();new=self.recipe_package('new.zip')
        conflict=recipe_plan(self.b.root,new,'example');self.assertEqual(conflict['action'],'conflict')
        with self.assertRaises(ConfigError):install(self.b.root,new,'example',expected_plan=conflict['sha256'])
        update=recipe_plan(self.b.root,new,'example',resolution='replace')
        result=install(self.b.root,new,'example',resolution='replace',expected_plan=update['sha256'])
        self.assertEqual(fingerprint(result['rollback_copy']),original)
        self.assertNotEqual(fingerprint(self.b.root/'recipes/example'),original)

    def test_recipe_same_id_different_paths_use_explicit_references(self):
        package=self.recipe_package()
        for name in ('first','second'):
            p=recipe_plan(self.b.root,package,name);install(self.b.root,package,name,expected_plan=p['sha256'])
            self.assertTrue(choose(self.b.root,':'+name)['runnable'])
        with self.assertRaisesRegex(ConfigError,'ambiguous'):choose(self.b.root,'portable-example')

    def test_recipe_pinned_tree_survives_update_and_never_imports_candidate(self):
        package=self.recipe_package();p=recipe_plan(self.b.root,package,'example');install(self.b.root,package,'example',expected_plan=p['sha256'])
        with execution_snapshot(self.b.root,self.b.root/'recipes/example') as pinned:
            before=(pinned/'main.py').read_bytes()
            (self.b.root/'recipes/example/main.py').write_text("raise RuntimeError('candidate side effect')")
            self.assertEqual((pinned/'main.py').read_bytes(),before)
        self.assertFalse(pinned.exists())

    def test_complete_backup_recipe_transfers_without_domain_module_import(self):
        portable=self.a.root/'recipes/portable-backup';portable.mkdir()
        for name,data in portable_files(IDENTITY).items():
            p=portable/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        package=self.base/'backup.zip';pack(choose(self.a.root,':portable-backup'),[p.relative_to(portable).as_posix() for p in portable.rglob('*') if p.is_file()],package)
        selected=recipe_plan(self.b.root,package,'backup/check');install(self.b.root,package,'backup/check',expected_plan=selected['sha256'])
        self.assertNotIn('from opsfeast.backup_check', (self.b.root/'recipes/backup/check/main.py').read_text())
        self.assertTrue((self.b.root/'recipes/backup/check/validate.py').is_file())
        self.assertFalse((self.b.root/'services/objects.sqlite3').exists())

    def test_data_only_schema_rejects_remote_refs_and_unsupported_rules(self):
        for schema in ({'$ref':'https://example.invalid/schema'},{'unevaluatedProperties':False},{'type':'integer','minimum':3}):
            with self.assertRaises(ConfigError):validate(2,schema)
        validate({'value':4},SCHEMA)
        with self.assertRaises(ConfigError):validate({'value':True},SCHEMA)
        with self.assertRaises(ConfigError):validate(float('nan'),{'type':'number'})

    def test_native_replace_is_explicit_and_recoverable(self):
        self.collect();unit=transfer.query(self.a.root,kind='retention')[0]
        unit['payload']['data']['value']=12
        package=self.base/'native-replace.zip';transfer.write_package(package,[unit])
        selected=transfer.import_plan(self.a.root,package,'replace')
        result=transfer.import_package(self.a.root,package,mode='replace',expected_plan=selected['sha256'])
        self.assertEqual(Reader(self.a.root).query()['records'][0]['data']['value'],12)
        from retention_store import database as native_db
        record=records(self.a.root)[0]
        with native_db(archive_path(self.a.root,record)) as db:
            self.assertTrue(all(row[0]==0 for row in db.execute('SELECT permitted FROM consumer_effects')))
        recovery=transfer.import_recovery_plan(self.a.root,result['receipt_id'])
        transfer.recover_import(self.a.root,result['receipt_id'],expected_plan=recovery['sha256'])
        self.assertEqual(Reader(self.a.root).query()['records'][0]['data']['value'],7)

    def test_import_failure_has_durable_before_images_for_recovery(self):
        self.collect();unit=transfer.query(self.a.root,kind='retention')[0];unit['payload']['data']['value']=12
        package=self.base/'interrupted.zip';transfer.write_package(package,[unit])
        selected=transfer.import_plan(self.a.root,package,'replace')
        with patch('opsfeast.transfer._write_native',side_effect=OSError('synthetic')):
            with self.assertRaisesRegex(ConfigError,'recovery'):transfer.import_package(self.a.root,package,mode='replace',expected_plan=selected['sha256'])
        journals=list((self.a.root/'transfer/imports').glob('*.json'));self.assertEqual(len(journals),1)
        receipt=transfer.document(journals[0].read_bytes());self.assertEqual(receipt['status'],'recoverable')
        recovery=transfer.import_recovery_plan(self.a.root,receipt['id'])
        transfer.recover_import(self.a.root,receipt['id'],expected_plan=recovery['sha256'])
        self.assertEqual(Reader(self.a.root).query()['records'][0]['data']['value'],7)

    def test_recipe_rollback_restores_original_and_preserves_displaced_version(self):
        from opsfeast.recipe_install import rollback_plan,rollback
        package=self.recipe_package();p=recipe_plan(self.b.root,package,'example');install(self.b.root,package,'example',expected_plan=p['sha256'])
        original=fingerprint(self.b.root/'recipes/example')
        self.code=self.code.replace("'value':7","'value':11");self.write_recipe();package2=self.recipe_package('v2.zip')
        p=recipe_plan(self.b.root,package2,'example',resolution='replace')
        updated=install(self.b.root,package2,'example',resolution='replace',expected_plan=p['sha256'])
        receipt_id=Path(updated['receipt']).stem;r=rollback_plan(self.b.root,receipt_id)
        result=rollback(self.b.root,receipt_id,expected_plan=r['sha256'])
        self.assertEqual(fingerprint(self.b.root/'recipes/example'),original)
        self.assertTrue(Path(result['receipt']['displaced']).is_dir())

    def test_interrupted_recipe_exchange_is_recoverable(self):
        from opsfeast.recipe_install import rollback_plan,rollback
        package=self.recipe_package();p=recipe_plan(self.b.root,package,'example');install(self.b.root,package,'example',expected_plan=p['sha256'])
        original=fingerprint(self.b.root/'recipes/example')
        self.code=self.code.replace("'value':7","'value':13");self.write_recipe();package2=self.recipe_package('v2.zip')
        p=recipe_plan(self.b.root,package2,'example',resolution='replace')
        real_rename=__import__('os').rename
        def interrupt(src,dst):
            if '.recipe-stage-' in str(src):raise OSError('crash after atomic exchange')
            return real_rename(src,dst)
        with patch('opsfeast.recipe_install.os.rename',side_effect=interrupt):
            with self.assertRaises(OSError):install(self.b.root,package2,'example',resolution='replace',expected_plan=p['sha256'])
        receipts=[transfer.document(path.read_bytes()) for path in (self.b.root/'transfer/recipe-installs').glob('*.json')]
        failed=next(r for r in receipts if r['status']=='recoverable')
        r=rollback_plan(self.b.root,failed['id']);self.assertTrue(r['allowed'])
        rollback(self.b.root,failed['id'],expected_plan=r['sha256'])
        self.assertEqual(fingerprint(self.b.root/'recipes/example'),original)

    def test_archive_frozen_days_plan_survives_later_clock(self):
        self.collect();destination=self.base/'frozen.zip'
        p=transfer.archive_plan(self.a.root,destination,older_than=0)
        from time import sleep
        sleep(.01)
        result=transfer.archive(self.a.root,destination,older_than=0,expected_plan=p['sha256'])
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['plan']['cutoff'],p['cutoff'])

    def test_failed_raw_is_portable_and_operation_evidence_is_protected(self):
        raw,path=self.collect();raw['status']='failed';raw['execution_access_mode']='unknown'
        path.write_text(json.dumps(raw))
        units=transfer.query(self.a.root,kind='observation');self.assertEqual(units[0]['payload']['status'],'failed')
        package=self.package('failed.zip',('observation',));self.assertTrue(package.exists())
        destination=self.base/'protected.zip';selected=transfer.archive_plan(self.a.root,destination,kinds=('observation',),older_than=0)
        self.assertEqual(selected['selected'][0]['source']['blocked'],'protected_operation_evidence')
        with self.assertRaises(ConfigError):transfer.archive(self.a.root,destination,expected_plan=selected['sha256'])
        self.assertTrue(path.exists());self.assertFalse(destination.exists())

    def test_shared_attachment_refuses_partial_archive_and_preserves_contents(self):
        raw,path=self.collect();attachment=self.a.root/'observations/evidence.txt';attachment.write_bytes(b'synthetic attachment')
        raw['artifacts']=[{'path':'evidence.txt','sha256':transfer.digest(b'synthetic attachment'),'size_bytes':20}]
        path.write_text(json.dumps(raw))
        other=copy.deepcopy(raw);other['source_observation_id']=str(uuid4())
        self.a.root.joinpath('observations/another.json').write_text(json.dumps(other))
        unit=next(u for u in transfer.query(self.a.root,kind='observation') if u['context'].get('result_id','').endswith(path.name))
        selected=transfer.archive_plan(self.a.root,self.base/'partial.zip',kinds=('observation',),ids=[unit['id']])
        self.assertEqual(selected['selected'][0]['source']['blocked'],'shared_attachment')
        with self.assertRaises(ConfigError):transfer.archive(self.a.root,self.base/'partial.zip',expected_plan=selected['sha256'])
        self.assertEqual(attachment.read_bytes(),b'synthetic attachment')

    def test_imported_retention_uses_source_qualified_hosts_in_normal_reader(self):
        self.collect();package=self.package(kinds=('retention',));p=transfer.import_plan(self.b.root,package)
        transfer.import_package(self.b.root,package,expected_plan=p['sha256'])
        record=Reader(self.b.root).query()['records'][0]
        self.assertTrue(record['host_id'].startswith('import-'))
        self.assertEqual(record['origin']['host_id'],'h')
        self.assertEqual(Reader(self.b.root).show(record['record_id']),record)
        self.assertTrue((self.b.root/'vault/Transfers/SUMMARY.md').is_file())

    def test_recipe_executable_assets_survive_package_install_and_execution_snapshot(self):
        helper=self.directory/'helper.sh';helper.write_text('#!/bin/sh\nexit 0\n');helper.chmod(0o755)
        package=self.base/'assets.zip';pack(choose(self.a.root,':example'),['recipe.yaml','main.py','README.md','LICENSE','helper.sh'],package)
        p=recipe_plan(self.b.root,package,'assets');install(self.b.root,package,'assets',expected_plan=p['sha256'])
        self.assertTrue((self.b.root/'recipes/assets/helper.sh').stat().st_mode&0o111)
        with execution_snapshot(self.b.root,self.b.root/'recipes/assets') as pinned:self.assertTrue((pinned/'helper.sh').stat().st_mode&0o111)

    def test_public_data_unit_and_manifest_schemas_match_real_package(self):
        self.collect();package=self.package();manifest,units=transfer.read_package(package)
        validate(manifest,json.loads((ROOT/'schemas/data-package.schema.json').read_text()))
        for unit in units:validate(unit,json.loads((ROOT/'schemas/portable-data-unit.schema.json').read_text()))

    def test_portable_backup_executes_and_retains_without_registered_domain_support(self):
        from test_backup_check import LocalScanActor
        import retention_contracts
        portable=self.b.root/'recipes/backup';portable.mkdir(parents=True)
        for name,data in portable_files(IDENTITY).items():
            path=portable/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        backup=self.base/'actual-files';backup.mkdir()
        from zoneinfo import ZoneInfo
        today=datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
        (backup/(today+'.sql')).write_bytes(b'')
        self.b.root.joinpath('hosts.yaml').write_text(json.dumps({'hosts':{'h':{'connection':{'local':True},'users':{'operator':{}},
            'recipes':{':backup':{'vars':{'target_python':sys.executable,'backups':[{'name':'db','directory':str(backup),'patterns':['{date}.sql']}]}}}}}}))
        with patch.object(recipe_runner,'REPOSITORY_ROOT',self.base/'b'),patch.object(retention_contracts,'STRUCTURED',{}):
            report,path=recipe_runner.run(self.b.root,'h',recipe=':backup',session_class=LocalScanActor,runtime={'verification':'synthetic-transport'})
            self.assertEqual(report['status'],'success',report)
            self.assertEqual(report['retention']['status'],'stored',report)
            self.assertEqual(Reader(self.b.root).query()['records'][0]['data']['backups'][0]['health'],'healthy')
            package=self.base/'backup-data.zip';transfer.export(self.b.root,package,kinds=('retention',))
            self.assertEqual(len(transfer.read_package(package)[1]),1)

    def test_first_failed_write_leaves_readable_empty_space(self):
        with self.assertRaises(OSError):
            with transfer.database(self.b.root,True) as db:
                raise OSError('simulated first insert failure')
        self.assertEqual(transfer.imported(self.b.root),[])
        self.assertEqual((self.b.root/'transfer/space.sqlite3').stat().st_mode&0o777,0o600)

    def test_ninety_day_boundary_is_strict_and_uses_source_time(self):
        self.collect();unit=transfer.query(self.a.root,kind='retention')[0]
        boundary=datetime.fromisoformat(unit['observed_at'])+timedelta(days=90)
        self.assertEqual(transfer.select(self.a.root,kinds=('retention',),older_than=90,now=boundary)['selected'],[])
        selected=transfer.select(self.a.root,kinds=('retention',),older_than=90,now=boundary+timedelta(microseconds=1))
        self.assertEqual([s['id'] for s in selected['selected']],[unit['id']])

    def test_archive_returns_database_pages_to_filesystem(self):
        self.meta['retention']['data_schema']={'type':'object','required':['value','blob'],'properties':{'value':{'type':'integer'},'blob':{'type':'string'}}}
        self.code=self.code.replace("'value':7","'value':7,'blob':'x'*300000")
        self.write_recipe();self.collect()
        record=records(self.a.root)[0];path=archive_path(self.a.root,record);before=path.stat().st_size
        selected=transfer.archive_plan(self.a.root,self.base/'large.zip',kinds=('retention',),older_than=0)
        receipt=transfer.archive(self.a.root,self.base/'large.zip',expected_plan=selected['sha256'])
        self.assertLess(path.stat().st_size,before)
        self.assertGreater(receipt['bytes_reclaimed'],100000)
        self.assertEqual(len(transfer.query(self.a.root,kind='observation')),1)

    def test_cli_preview_apply_and_json_errors_have_no_remote_effects(self):
        from transfer_cli import main
        self.collect();package=self.package();output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['import-plan','--root',str(self.b.root),'--package',str(package),'--json']),0)
        plan=json.loads(output.getvalue());output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['import','--root',str(self.b.root),'--package',str(package),'--plan',plan['sha256'],'--json']),0)
        self.assertEqual(json.loads(output.getvalue())['status'],'success')
        self.assertEqual(len(self.b.transfer.query()),2)
        self.assertFalse((self.b.root/'services/objects.sqlite3').exists())

    def test_transfer_rejects_sqlite_sidecar_symlinks(self):
        self.b.root.joinpath('transfer').mkdir()
        target=self.base/'unrelated';target.write_bytes(b'preserve')
        self.b.root.joinpath('transfer/space.sqlite3-journal').symlink_to(target)
        with self.assertRaises(ConfigError):transfer.imported(self.b.root)
        self.assertEqual(target.read_bytes(),b'preserve')
