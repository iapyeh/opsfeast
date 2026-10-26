"""Shared recipe account selection and recipe-owned assessment, with public synthetic fixtures."""
from contextlib import redirect_stdout, closing
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from opsfeast import ConfigError, CoreError, Instance
from opsfeast.recipe_execution import normalize, console_command
from opsfeast.recipe_assessment import validate as validate_assessment
from console_output import execution_result, execution_identities
from recipe_contract import validate_result
import recipe_runner
import recipe_settings
import test_core_delivery as fixture
from test_core_api import Actor
from test_backup_check import LocalScanActor
from retention_store import Reader
from observation_runs import start,record_result,finish
from observation_cli import query as batch_query,execution_row
from attribution_fixture import copy_recipe

ROOT=Path(__file__).resolve().parents[1]
CODE="""VERSION = '0.1.0'
def execute(recipe):
    value = recipe.session.exec_command(['id', '-un'], check=True)
    return {'status': 'success', 'reason_code': 'observed', 'message': 'Synthetic account observed.',
            'data': {'account': value.stdout.strip()},
            'assessment': {'label': 'REVIEW NEEDED', 'severity': 'warning', 'summary': 'The check completed; review the saved finding.'}}
"""


class AccountAssessmentTests(unittest.TestCase):
    write = fixture.CoreDeliveryTests.write

    def setUp(self):
        fixture.CoreDeliveryTests.setUp(self)
        self.meta['access_mode']='read'
        self.meta['inputs']={'variables':{}}
        self.meta['retention']={'contract':'synthetic-account','version':'0.1.0','mode':'portable',
            'description':'Synthetic observed account.', 'data_schema':{'type':'object','required':['account'],
            'properties':{'account':{'type':'string'}},'additionalProperties':False}}
        self.write(CODE)
        self.actor=Actor()

    def configure(self,execution=None,*,users=None,defaults=None,groups=None):
        host={'connection':{'local':True},'users':users or {'operator':{'password':'private-login'},'app':{'password':'private-app'}}}
        if execution is not None:host['recipes']={':example':{'execution':execution}}
        value={'hosts':{'h':host}}
        if defaults:value['default']=defaults
        if groups:value['groups']=groups;host['group']=list(groups)
        self.profile.root.joinpath('hosts.yaml').write_text(json.dumps(value))
        return value

    def execute(self):
        with patch.object(recipe_runner,'REPOSITORY_ROOT',self.root):
            return recipe_runner.run(self.profile.root,'h',recipe=':example',session_class=lambda:self.actor,
                                     runtime={'verification':'synthetic-transport'})

    def test_login_default_records_identity_without_escalation(self):
        self.configure();report,path=self.execute()
        self.assertEqual(report['status'],'success',report)
        self.assertEqual(report['data']['account'],'operator')
        self.assertEqual(self.actor.transitions,[])
        self.assertTrue(report['execution_identity']['verified'])
        self.assertTrue(report['execution_identity']['restoration_verified'])
        self.assertEqual(report['execution_identity']['actual'],{'username':'operator','effective_uid':1000})
        self.assertEqual(report['assessment']['label'],'REVIEW NEEDED')
        record=Reader(self.profile.root).query()['records'][0]
        self.assertEqual(record['assessment'],report['assessment'])
        self.assertEqual(record['execution_identity'],report['execution_identity'])
        self.assertIn('WARNING · REVIEW NEEDED',execution_result(report)['text'])
        self.assertEqual(execution_identities(report)[0]['username'],'operator')

    def test_configured_sudo_root_requires_no_recipe_code_change(self):
        self.configure({'via':'sudo','user':'root'})
        report,path=self.execute()
        self.assertEqual(report['status'],'success',report)
        self.assertEqual(report['data']['account'],'root')
        self.assertEqual(self.actor.transitions,[('sudo','root','private-login')])
        self.assertEqual(report['execution_identity']['actual']['effective_uid'],0)
        self.assertTrue(report['execution_identity']['restoration_verified'])
        self.assertEqual(self.actor.uid,1000)

    def test_configured_su_uses_declared_target_credentials(self):
        self.configure({'via':'su','user':'app'})
        report,path=self.execute()
        self.assertEqual(report['status'],'success',report)
        self.assertEqual(report['data']['account'],'app')
        self.assertEqual(self.actor.transitions,[('su','app','private-app')])

    def test_acquisition_failure_never_calls_recipe_and_never_falls_back(self):
        self.configure({'via':'sudo','user':'root'});self.actor.entry_failure=True
        self.write(CODE.replace("    value =", "    raise RuntimeError('body must never run')\n    value ="))
        report,path=self.execute()
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['reason_code'],'execution_identity_failed')
        self.assertFalse(report['execution_identity']['verified'])
        self.assertNotIn('assessment',report)
        self.assertEqual(len(self.actor.transitions),1)
        self.assertNotIn('private-login',path.read_text())

    def test_wrong_effective_uid_and_sudo_disabled_are_failures(self):
        self.configure({'via':'sudo','user':'root'});self.actor.wrong_identity=True
        report,path=self.execute();self.assertEqual(report['reason_code'],'execution_identity_failed')
        self.assertEqual(report['data'],{})
        self.actor=Actor();self.configure({'via':'sudo','user':'root'},users={'operator':{'sudo':False}})
        report,path=self.execute();self.assertEqual(report['reason_code'],'execution_identity_failed')
        self.assertEqual(self.actor.transitions,[])

    def test_restoration_failure_overrides_custom_success_label(self):
        self.configure({'via':'sudo','user':'root'});self.actor.restore_failure=True
        report,path=self.execute()
        self.assertEqual(report['status'],'failed')
        self.assertFalse(report['execution_identity']['restoration_verified'])
        self.assertIn('FAIL',execution_result(report)['text'])

    def test_recipe_body_failure_preserves_successful_account_restoration_evidence(self):
        self.configure({'via':'sudo','user':'root'})
        self.write("VERSION = '0.1.0'\ndef execute(recipe):\n    raise RuntimeError('synthetic body failure')\n")
        report,path=self.execute()
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['reason_code'],'execution_failed')
        self.assertTrue(report['execution_identity']['verified'])
        self.assertTrue(report['execution_identity']['restoration_verified'])
        self.assertEqual(self.actor.uid,1000)

    def test_group_inheritance_is_per_leaf_and_host_override_wins(self):
        self.configure(defaults={'recipes':{':example':{'execution':{'via':'sudo','user':'root'}}}},
            groups={'first':{'recipes':{':example':{'execution':{'user':'app'}}}},
                    'second':{'recipes':{':example':{'execution':{'user':'root'}}}}})
        report,path=self.execute()
        self.assertEqual(report['data']['account'],'app',report)
        self.assertEqual(self.actor.transitions,[('sudo','app','private-login')])

    def test_explicit_login_target_mismatch_stops_before_body(self):
        self.configure({'via':'login','user':'root'})
        report,path=self.execute()
        self.assertEqual(report['reason_code'],'execution_identity_failed')
        self.assertEqual(report['data'],{})
        self.assertEqual(self.actor.transitions,[])

    def test_null_execution_resets_inherited_sudo_policy(self):
        for reset in (None, {'via':'login','user':None}):
            with self.subTest(reset=reset):
                value=self.configure(defaults={'recipes':{':example':{'execution':{'via':'sudo','user':'root'}}}})
                value['hosts']['h']['recipes']={':example':{'execution':reset}}
                self.profile.root.joinpath('hosts.yaml').write_text(json.dumps(value))
                self.actor=Actor()
                report,_=self.execute()
                self.assertEqual(report['status'],'success',report)
                self.assertEqual(report['data']['account'],'operator')
                self.assertEqual(self.actor.transitions,[])

    def test_invalid_policy_and_unsupported_runner_fail_before_connection(self):
        for policy in ({'via':'sudo'}, {'via':'unknown','user':'root'}, {'via':'sudo','user':'root; id'}, {'via':'sudo','password':'secret'}):
            with self.subTest(policy=policy),self.assertRaises(ConfigError):
                self.configure(policy);self.execute()
        self.configure({'via':'sudo','user':'root'})
        self.meta['runner']['contract']='python-session'
        self.write(CODE.replace('def execute(recipe):','def execute(session, *, context, timeout):'))
        with self.assertRaisesRegex(ConfigError,'python-recipe'):self.execute()
        self.assertEqual(self.actor.transitions,[])

    def test_completed_batch_uses_saved_recipe_assessment(self):
        self.configure();report,path=self.execute()
        batch_id=start(self.profile.root,[{'host_id':'h'}],':example')
        report['observation_run_id']=batch_id;path.write_text(json.dumps(report))
        record_result(self.profile.root,batch_id,'h',report);finish(self.profile.root,batch_id)
        view=batch_query(self.profile.root,batch_id)
        host=view['hosts'][0]
        self.assertEqual(host['assessment'],report['assessment'])
        self.assertEqual(execution_result(execution_row(host))['text'],execution_result(report)['text'])
        path.unlink()
        archived_view=batch_query(self.profile.root,batch_id)
        self.assertEqual(archived_view['hosts'][0]['assessment'],report['assessment'])
        self.assertEqual(archived_view['hosts'][0]['execution_identity'],report['execution_identity'])

    def test_existing_root_helper_remains_usable_when_already_selected_root(self):
        self.configure({'via':'sudo','user':'root'})
        self.write(CODE.replace("    value = recipe.session.exec_command(['id', '-un'], check=True)","    with recipe.root() as root:\n        value = root('id -un', check=True)"))
        report,path=self.execute()
        self.assertEqual(report['status'],'success',report)
        self.assertEqual(report['data']['account'],'root')
        self.assertEqual(len(self.actor.transitions),1)


class ResultContractTests(unittest.TestCase):
    def test_installation_checks_required_product_features_without_candidate_code(self):
        from opsfeast.recipe_install import requirements
        for name in ('recipe-assessment','recipe-execution','portable-retention'):
            for version,status in (('0.1.0','available'),('9.0.0','missing')):
                rows=requirements({'portability':{'features':{name:version}}})
                row=next(row for row in rows if row.get('dependency')=='feature:'+name)
                self.assertEqual(row['status'],status)
        rows=requirements({'portability':{'features':{'unknown':'0.1.0'}}})
        self.assertTrue(any(row['status']=='missing' for row in rows))

    def test_default_pass_and_custom_findings_are_independent_of_exit_status(self):
        base={'status':'success','reason_code':'observed','message':'Observed.','data':{}}
        self.assertEqual(execution_result(base)['text'],'PASS')
        value=dict(base,assessment={'label':'需要清理','severity':'warning','summary':'存在過期檔案。'})
        validate_result(value)
        self.assertEqual(execution_result(value)['status'],'success')
        self.assertIn('需要清理',execution_result(value)['text'])
        for field in ('retention','content_update'):
            failed=dict(value,**{field:{'status':'failed'}})
            self.assertEqual(execution_result(failed)['status'],'failed')
            self.assertTrue(execution_result(failed)['text'].startswith('❌ FAIL'))
        value['status']='failed';self.assertTrue(execution_result(value)['text'].startswith('❌ FAIL'))

    def test_assessment_is_bounded_plain_data(self):
        valid={'label':'HEALTHY','severity':'info','summary':'A saved finding.'}
        for invalid in ({**valid,'label':'x\nPASS'}, {**valid,'label':'PASS\u2028FAIL'}, {**valid,'label':'\x1b[2J'}, {**valid,'severity':'healthy'},
                        {**valid,'summary':''},{**valid,'label':'x'*81},{**valid,'extra':True}):
            with self.subTest(value=invalid),self.assertRaises(ConfigError):validate_assessment(invalid)

    def test_exact_bytes_stdin_and_argv_are_preserved_in_posix_console_adapter(self):
        for payload in ('a\nb\n', b'a\x00b\xff\n', b'', '中文'):
            command,options=console_command([sys.executable,'-c','import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())'],{'input':payload})
            result=subprocess.run(['bash','-c',command],capture_output=True,check=True)
            self.assertEqual(result.stdout,payload.encode() if isinstance(payload,str) else payload)
            self.assertNotIn('input',options)
        marker="a'; echo injected; #"
        command,_=console_command(['printf','%s',marker],{})
        self.assertEqual(subprocess.run(['bash','-c',command],capture_output=True,check=True).stdout.decode(),marker)

    def test_native_sshscript_borrowed_console_keeps_json_input_and_stderr(self):
        from sshscript import Session
        with closing(Session()) as session:
            with session.shell('bash', get_pty=False) as console:
                command,options=console_command([sys.executable,'-c',
                    'import json,sys;v=json.load(sys.stdin);print(v["value"]);sys.stderr.write("diagnostic\\n")'],
                    {'input':json.dumps({'value':'native input preserved'}),'command_timeout':5,'check':True})
                result=console(command,**options)
                self.assertEqual(result.stdout.strip(),'native input preserved')
                self.assertEqual(result.stderr.strip(),'diagnostic')

    def test_native_scoped_facade_supports_stdin_capture_flags_and_managed_jobs(self):
        from sshscript import Session
        from opsfeast import Recipe
        from hashlib import sha256
        fake_profile=SimpleNamespace(instance=SimpleNamespace(identity={'id':'synthetic-transport'}))
        with closing(Session()) as session:
            with session.shell('bash',get_pty=False) as console:
                recipe=Recipe._create(fake_profile,None,'local',console,5,{},console=True)
                payload=b'\x00\xffexact\n'
                argv=[sys.executable,'-c','import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())']
                empty=recipe.session.exec_command([sys.executable,'-c','import sys;print(len(sys.stdin.buffer.read()))'],check=True)
                self.assertEqual(empty.stdout.strip(),'0')
                result=recipe.session.exec_command(argv,input=payload,check=True)
                self.assertEqual(result.stdout.strip(),sha256(payload).hexdigest())
                self.assertFalse(result.stdout_truncated)
                self.assertEqual(result.command,tuple(argv))
                with recipe.session.start(argv,input=payload,timeout=5,check=True) as job:
                    self.assertEqual(job.command,tuple(argv))
                    self.assertEqual(job.wait().stdout.strip(),sha256(payload).hexdigest())
                result=recipe.session.exec_command([sys.executable,'-c','print("x"*1000)'],capture_limit=32)
                self.assertTrue(result.stdout_truncated)
                recipe._state.active=False

    def test_native_backup_scanner_works_through_pipe_console_without_recipe_changes(self):
        from sshscript import Session
        from opsfeast import Recipe
        from opsfeast.backup_check import execute
        from datetime import datetime
        from zoneinfo import ZoneInfo
        with tempfile.TemporaryDirectory() as temp:
            today=datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
            Path(temp,today+'.sql').write_bytes(b'')
            fake_profile=SimpleNamespace(instance=SimpleNamespace(identity={'id':'synthetic-transport'}))
            with closing(Session()) as session:
                with session.shell('bash',get_pty=False) as console:
                    recipe=Recipe._create(fake_profile,None,'local',console,10,{},console=True,
                        vars={'target_python':sys.executable,'backups':[{'name':'db','directory':temp,'patterns':['{date}.sql']}]})
                    result=execute(recipe)
                    self.assertEqual(result['status'],'success',result)
                    self.assertEqual(result['assessment']['label'],'BACKUPS OK')
                    self.assertEqual(result['data']['backups'][0]['health'],'healthy')
                    recipe._state.active=False


class StandalonePolicyTests(unittest.TestCase):
    setUp = AccountAssessmentTests.setUp
    write = AccountAssessmentTests.write
    configure = AccountAssessmentTests.configure

    def test_public_profile_recipe_selects_account_and_cleans_up(self):
        self.configure({'via':'su','user':'app'})
        self.profile.hosts.reload()
        with patch('host_runtime.runtime_class',return_value=lambda:self.actor):
            with self.profile.recipe('h',execution={'via':'su','user':'app'}) as recipe:
                self.assertEqual(recipe.session.exec_command(['id','-un']).stdout.strip(),'app')
        self.assertEqual(self.actor.transitions,[('su','app','private-app')])
        self.assertEqual(self.actor.closed,1)

    def test_bad_standalone_policy_fails_before_connecting(self):
        with patch('host_runtime.runtime_class',side_effect=AssertionError('must not load/connect')):
            with self.assertRaises(ConfigError):
                with self.profile.recipe('h',execution={'via':'sudo'}):
                    self.fail('must not run')
