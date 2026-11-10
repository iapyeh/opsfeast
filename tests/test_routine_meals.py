"""Public routine/meal regressions: synthetic transports, no managed hosts."""
from contextlib import contextmanager,redirect_stdout
import io,json,tempfile,unittest,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from opsfeast import Instance,ConfigError,RootUnavailableError
from opsfeast.routine_execution import plan,describe,run_host
from opsfeast.routine_contract import RoutineSpec,order,validate
from test_inventory_jobs import Actor

class Transport(Actor):
    opened=0;closed=0;actors=[]
    def __init__(self):
        super().__init__();type(self).opened+=1;self.uid=1000;self.user='synthetic';type(self).actors.append(self)
    def exec_command(self,argv,**kwargs):
        if argv==['id','-un']:return SimpleNamespace(stdout=self.user+'\n',stderr='',exitcode=0)
        if argv[:2]==['id','-u']:return SimpleNamespace(stdout=str(self.uid)+'\n',stderr='',exitcode=0)
        if argv==['uname','-s']:return SimpleNamespace(stdout='Linux\n',stderr='',exitcode=0)
        return super().exec_command(argv,**kwargs)
    def close(self,**kwargs):type(self).closed+=1

class RoutineMealTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.product=Path(self.temp.name)
        with redirect_stdout(io.StringIO()):self.profile=Instance.open(self.product).init_profile()
        self.root=self.profile.root;(self.root/'hosts.yaml').write_text('hosts: {node: {connection: {local: true}}}\n')
        Transport.opened=Transport.closed=0;Transport.actors=[]
    def choice(self,reference='system/inventory/overview',properties=None):
        return [{'reference':reference,'vars':{},'inventory_selection':{'properties':properties} if properties else None}]
    def test_catalog_and_static_plan_never_connect_or_import_candidates(self):
        with patch('subprocess.Popen',side_effect=AssertionError('not during inspection')):
            description=describe(self.root,'node',self.choice())
        self.assertEqual(len(description['members']),10)
        self.assertEqual(sum(len(m['properties']) for m in description['members']),70)
        self.assertEqual(Transport.opened,0)
    def test_one_connection_per_host_with_independent_retained_children(self):
        selected=['system.hostname','storage.filesystems.used_percent']
        result=run_host(self.root,'node',self.choice(properties=selected),session_class=Transport,runtime={'verification':'synthetic'},save=True)
        self.assertEqual(Transport.opened,1);self.assertEqual(Transport.closed,1)
        self.assertEqual(len(result['children']),2,result)
        for child in result['children']:self.assertEqual(child['retention']['status'],'stored',child)
        records=self.profile.retention.query()['records']
        self.assertEqual(len(records),2)
        capacity=next(r for r in records if r['recipe_reference'].endswith('/storage-capacity'))
        self.assertEqual(capacity['data']['groups'][0]['samples'][0]['value'],82)
        self.assertEqual({r['recipe_reference'] for r in records},{'system/inventory/system','system/inventory/storage-capacity'})
        self.assertTrue(all(r['data']['routine_evidence'][0]['actor']['effective_uid']==1000 for r in records))
        self.assertTrue(result['restoration_verified']);self.assertTrue(result['cleanup_verified'])
    def test_login_before_one_root_phase_and_no_cross_scope_leak(self):
        @contextmanager
        def root(session,config,host,timeout,evidence,**kwargs):
            evidence['calls']=1;session.uid=0;session.user='root'
            try:yield session
            finally:session.uid=1000;session.user='synthetic';evidence['restoration_verified']=True
        with patch('root_access.root_actor',root):
            result=run_host(self.root,'node',self.choice(properties=['system.hostname','hardware.vendor','hardware.serial']),session_class=Transport,save=True)
        self.assertEqual(result['root_access']['calls'],1,result)
        self.assertEqual(result['execution_order'][-1],['system/inventory/hardware','identity-linux'])
        self.assertEqual(result['execution_order'][0][1],'baseline')
        records=self.profile.retention.query()['records']
        hardware=next(r for r in records if r['recipe_reference'].endswith('/hardware'))
        self.assertEqual([r['actor']['effective_uid'] for r in hardware['data']['routine_evidence']],[1000,0])
    def test_root_unavailable_preserves_login_observations(self):
        @contextmanager
        def root(*args,**kwargs):
            raise RootUnavailableError({'reason_code':'sudo_disabled'})
            yield
        with patch('root_access.root_actor',root):result=run_host(self.root,'node',self.choice(properties=['system.architecture','hardware.serial']),session_class=Transport,save=True)
        record=self.profile.retention.query()['records'][0]
        states={s['property']:s['status'] for g in record['data']['groups'] for s in g['samples']}
        self.assertEqual(states['hardware.serial'],'unavailable')
        self.assertEqual(record['data']['routine_evidence'][-1]['reason_code'],'root_unavailable')
        self.assertTrue(result['restoration_verified'])
    def test_dependency_cycles_and_login_after_root_rejected(self):
        a=RoutineSpec('a','a','login',('b',),(),());b=RoutineSpec('b','b','root',(),(),())
        with self.assertRaises(ConfigError):order([a,b])
        b=RoutineSpec('b','b','login',('a',),(),())
        with self.assertRaises(ConfigError):order([a,b])

    def test_unsaved_query_has_no_profile_writes_and_shared_capture_keeps_time(self):
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result=run_host(self.root,'node',self.choice(properties=['metrics.memory_available_bytes','storage.swap.used_bytes']),session_class=Transport,save=False)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(Transport.opened,1)
        self.assertEqual(sum('/proc/meminfo' in c for c in Transport.actors[0].commands),1)
        values={s['property']:s['value'] for g in result['groups'] for s in g['samples']}
        self.assertEqual(values['metrics.memory_available_bytes'],500*1024)
        self.assertEqual(values['storage.swap.used_bytes'],75*1024)

    def test_checkpoint_survives_abort_and_cannot_be_ingested_as_complete(self):
        @contextmanager
        def abort(*args,**kwargs):
            raise SystemExit(7)
            yield
        with patch('root_access.root_actor',abort),self.assertRaises(SystemExit):
            run_host(self.root,'node',self.choice(properties=['hardware.vendor','hardware.serial']),session_class=Transport,save=True)
        paths=list((self.root/'observations').glob('recipe-run-*.json'))
        self.assertEqual(len(paths),1)
        raw=json.loads(paths[0].read_text())
        self.assertEqual(raw['routine_execution_state'],'incomplete')
        self.assertTrue(raw['routine_checkpoints'][0]['result']['data']['groups'])
        from retention_replay import ingest
        self.assertEqual(ingest(self.root,paths)['files'][0]['reason_code'],'routine_execution_incomplete')
        self.assertEqual(self.profile.retention.query()['records'],[])

    def test_stop_after_login_withholds_root_and_preserves_retention(self):
        import threading
        from opsfeast.inventory import service
        stop=threading.Event();original=service.collect
        def collect(*args):
            value=original(*args);stop.set();return value
        with patch.object(service,'collect',collect),patch('root_access.root_actor',side_effect=AssertionError('no root after stop')):
            result=run_host(self.root,'node',self.choice(properties=['hardware.vendor','hardware.serial']),session_class=Transport,save=True,stop=stop)
        rows=self.profile.retention.query()['records'][0]['data']['routine_evidence']
        self.assertEqual(rows[-1]['reason_code'],'stop_requested')
        self.assertEqual(result['execution_order'],[['system/inventory/hardware','baseline']])

    def test_wrong_root_identity_never_runs_root_body_and_retains_login_evidence(self):
        @contextmanager
        def wrong(session,*args,**kwargs):yield session
        with patch('root_access.root_actor',wrong):
            result=run_host(self.root,'node',self.choice(properties=['system.hostname','hardware.serial']),session_class=Transport,save=True)
        self.assertFalse(result['restoration_verified'])
        self.assertFalse(any(name=='identity-linux' for _,name in result['execution_order']))
        records=self.profile.retention.query()['records']
        platform=next(r for r in records if r['recipe_reference'].endswith('/system'))
        self.assertEqual(platform['data']['groups'][0]['samples'][0]['value'],'synthetic-node')
        self.assertFalse(platform['data']['connection_evidence']['restoration_verified'])

    def test_all_inputs_validated_before_opening_any_connection(self):
        choices=self.choice('system/inventory/system')+self.choice('system/inventory/storage-capacity')
        choices[-1]['vars']={'command_timeout_seconds':'wrong'}
        with self.assertRaises(ConfigError):run_host(self.root,'node',choices,session_class=Transport)
        self.assertEqual(Transport.opened,0)
        self.assertFalse(list((self.root/'observations').glob('*.json')))

    def test_child_scope_copies_vars_expires_and_cannot_acquire_privilege(self):
        from opsfeast import Recipe,CoreError
        parent=Recipe._create(self.profile,SimpleNamespace(),'node',Transport(),30,{'parent':True},vars={'list':[1]})
        child_report={};options={'list':[2]}
        with parent.child(vars=options,report=child_report) as child:
            child.vars['list'].append(3)
            self.assertEqual(options,{'list':[2]})
            with self.assertRaises(CoreError):parent.session.exec_command(['hostname'])
            for method in (child.root,child.sudo,lambda:child.su('root')):
                with self.assertRaises(CoreError):
                    with method():pass
            view=child.session
        self.assertEqual(parent.vars,{'list':[1]})
        with self.assertRaises(CoreError):view.exec_command(['hostname'])
        with parent.child(vars={'list':[4]}) as next_child:self.assertEqual(next_child.vars,{'list':[4]})
        parent._active=False;parent._state.active=False

    def test_worker_batch_revalidates_and_retains_each_member_on_one_transport(self):
        from opsfeast.recipe_runs import prepare_pair
        from opsfeast.recipe_run_worker import main
        import opsfeast.routine_execution as engine
        choices=self.choice('system/inventory/system',['system.hostname'])+self.choice('system/inventory/storage-capacity',['storage.filesystems.used_percent'])
        batch=[]
        for choice in choices:
            pair,_=prepare_pair(self.root,choice['reference'],'node',{},[],choice['inventory_selection'])
            batch.append({**choice,'inputs':[],'fingerprint':pair['fingerprint']})
        spec={'root':str(self.root),'host':'node','batch':batch,'timeout':30}
        output=io.StringIO();calls=[]
        def factory():calls.append(True);return Transport
        with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(spec).encode()))),patch.object(engine,'runtime_class',factory),redirect_stdout(output):
            self.assertEqual(main(),0)
        result=json.loads(output.getvalue())
        self.assertEqual(len(calls),1)
        self.assertEqual(len(result['children']),2)
        self.assertTrue(result['observation_run_id'])
        self.assertTrue(all(c['retention']['status']=='stored' for c in result['children']))
        self.assertEqual(len(self.profile.retention.query()['records']),2)
        # A changed member is rejected before any transport is created.
        spec['batch'][1]['fingerprint']='0'*64
        with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(spec).encode()))),patch.object(engine,'runtime_class',side_effect=AssertionError('no connection')):
            with self.assertRaises(ConfigError):main()
