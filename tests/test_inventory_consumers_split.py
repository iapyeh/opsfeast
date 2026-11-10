"""Consumers/reports read independent inventory children without rewriting history."""
import copy,json,io,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from opsfeast import read_yaml,Validator
from opsfeast.routine_execution import run_host
import test_routine_meals as fixtures
import retention_store as store
import retention_consumers as consumers
import recipe_reports as reports
import vault_content as vault
from recipe_catalog import choose
from test_result_data import raw as historical_raw

SYSTEM='system/inventory/system'
CAPACITY='system/inventory/storage-capacity'
OVERVIEW='system/inventory/overview'

class SplitConsumerTests(unittest.TestCase):
    setUp=fixtures.RoutineMealTests.setUp
    choice=fixtures.RoutineMealTests.choice

    def collect(self,fields,variables=None,actor=fixtures.Transport):
        choices=self.choice(properties=fields)
        choices[0]['vars']=variables or {}
        return run_host(self.root,'node',choices,session_class=actor,save=True)

    def history(self):
        raw=historical_raw();raw['recipe']['reference']=OVERVIEW
        raw['observations']['system_name']['value']='Historical OS'
        path=self.root/'observations/historical.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(raw))
        receipt=store.retain(self.root,raw)
        self.assertEqual(receipt['status'],'stored',receipt)
        return path

    def test_vault_index_reads_child_and_new_failure_does_not_restore_historical_success(self):
        history=self.history();history_bytes=history.read_bytes()
        self.collect(['system.system_name'])
        records=store.query(self.root)['records'];before=copy.deepcopy(records)
        config=Validator(self.root);config.load(self.root/'hosts.yaml')
        entries,index,_=vault.build(self.root,config)
        self.assertIn('[Synthetic Distribution](', '\n'.join(index))
        source=vault.system_observation(records)['record']
        self.assertEqual(source['recipe_reference'],SYSTEM)
        self.assertIn(vault.historical_names(records,config)[source['record_id']],'\n'.join(index))
        self.assertTrue(any('Historical OS' in text for text in entries.values()))
        class Denied(fixtures.Transport):
            def __init__(self):super().__init__();self.fail={'/etc/os-release'}
        self.collect(['system.system_name'],actor=Denied)
        _,index,_=vault.build(self.root,config)
        self.assertIn('[unknown](', '\n'.join(index))
        self.assertEqual(history_bytes,history.read_bytes())
        after={r['record_id']:r for r in store.query(self.root)['records']}
        for record in before:self.assertEqual(after[record['record_id']],record)

    def test_retention_report_filters_are_exact_and_do_not_alias_overview(self):
        history=self.history();self.collect(['system.system_name','storage.filesystems.used_percent'])
        before=copy.deepcopy(store.query(self.root)['records']);item=choose(self.root,'feast/report/retention-summary')
        for refs,expected in (([],3),([SYSTEM,CAPACITY],2),([OVERVIEW],1),(['company:'+SYSTEM],0)):
            with patch('opsfeast.load_session_class',side_effect=AssertionError('offline only')):
                report,path=reports.run_report(self.root,item,[],values={'recipes':refs,'hosts':['node']})
            self.assertEqual(report['data']['rows'],expected,report)
            selected={r['record_id'] for r in before if not refs or r['recipe_reference'] in refs}
            self.assertEqual(set(report['data']['record_ids']),selected)
            html=(path.parent/'artifacts/retention.html').read_text()
            self.assertNotIn('<script>',html)
        self.assertEqual(before,store.query(self.root)['records'])
        self.assertEqual(json.loads(history.read_text())['recipe']['reference'],OVERVIEW)

    def test_execution_report_keeps_meal_children_and_routine_identity_receipts(self):
        result=self.collect(['system.system_name','storage.filesystems.used_percent'])
        child=Path(result['children'][0]['result_path']);meal=Path(result['result_path'])
        original={p:p.read_bytes() for p in (child,meal)}
        item=choose(self.root,'feast/report/execution-summary')
        report,path=reports.run_report(self.root,item,[meal,child])
        self.assertEqual(report['data']['rows'],2,report)
        rows=json.loads((path.parent/'artifacts/summary.json').read_text())['rows']
        self.assertEqual({c['recipe']['reference'] for c in rows[0]['children']},{SYSTEM,CAPACITY})
        self.assertEqual(rows[0]['observed_to'],json.loads(original[meal])['observed_at'])
        self.assertEqual(rows[0]['retention'],json.loads(original[meal])['retention'])
        self.assertEqual(rows[0]['content_update'],json.loads(original[meal])['content_update'])
        self.assertTrue(rows[0]['meal_scope']['cleanup_verified'])
        self.assertTrue(rows[1]['routine_evidence'])
        self.assertTrue(rows[1]['connection_evidence']['cleanup_verified'])
        self.assertEqual(rows[1]['recipe_reference'],json.loads(original[child])['recipe']['reference'])
        html=(path.parent/'artifacts/summary.html').read_text()
        self.assertIn('Child recipe outcomes (2)',html)
        self.assertIn(CAPACITY,html)
        for p in original:self.assertEqual(p.read_bytes(),original[p])

    def test_consumer_exact_children_and_historical_subscriptions_stay_independent(self):
        config=read_yaml(self.root/'feast.yaml');config['consumers']={}
        for identifier,reference,contract in (('current-os',SYSTEM,'inventory-routine-observations'),('historical-os',OVERVIEW,'inventory-observations')):
            directory=self.root/'consumers'/identifier;directory.mkdir(parents=True)
            descriptor={'schema_version':'0.1.0','id':identifier,'description':'Synthetic exact subscription','entrypoint':'main.py','subscriptions':[{'event':'retention.observation.created','selector':{'recipe_reference':reference,'contract':contract,'version':'0.1.0'}}]}
            (directory/'consumer.yaml').write_text(json.dumps(descriptor))
            (directory/'main.py').write_text("import json\ndef execute(context):\n path=context.root / '"+identifier+".json'\n rows=json.loads(path.read_text()) if path.exists() else []\n rows.append(context.event)\n path.write_text(json.dumps(rows))\n return {'status':'success'}\n")
            config['consumers'][identifier]={'source':'local:consumers/'+identifier,'enabled':True}
        (self.root/'feast.yaml').write_text(json.dumps(config));original=(self.root/'feast.yaml').read_bytes()
        self.history();self.collect(['system.system_name','storage.filesystems.used_percent'])
        consumers.dispatch(self.root)
        current=json.loads((self.root/'current-os.json').read_text());historical=json.loads((self.root/'historical-os.json').read_text())
        self.assertEqual([r['recipe_reference'] for r in current],[SYSTEM])
        self.assertEqual([r['recipe_reference'] for r in historical],[OVERVIEW])
        self.assertEqual((self.root/'feast.yaml').read_bytes(),original)
        self.assertEqual(len(store.query(self.root)['records']),3)
        self.assertIn('current-os',{c['id'] for c in choose(self.root,SYSTEM)['consumers']})
        self.assertNotIn('historical-os',{c['id'] for c in choose(self.root,SYSTEM)['consumers']})

    def test_current_attention_uses_child_baseline_and_saved_meal_policy_without_relabeling(self):
        result=self.collect(['hardware.memory_total_bytes','metrics.memory_available_bytes'],{'attention':{'thresholds':{'memory_available_percent':{'warning':60,'critical':40}}}})
        before=copy.deepcopy(store.query(self.root)['records'])
        config=Validator(self.root);config.load(self.root/'hosts.yaml')
        entries,_,_=vault.build(self.root,config)
        current=next(body for name,body in entries.items() if name.endswith('records/current-inventory-resource-metrics.md'))
        self.assertIn('Available memory reported 50%',current)
        self.assertIn('Attention source records',current)
        self.assertIn('system/inventory/hardware',current)
        self.assertIn('system/inventory/resource-metrics',current)
        self.assertEqual(before,store.query(self.root)['records'])
        from observation_runs import attention_context
        metric=next(r for r in before if r['recipe_reference'].endswith('/resource-metrics'))
        unrelated=copy.deepcopy(before[0]);unrelated['host_id']='another-host';unrelated['record_id']='unrelated'
        foreign=copy.deepcopy(before[0]);foreign['origin']['namespace']='another-origin';foreign['record_id']='foreign'
        with patch('retention_store.query',side_effect=AssertionError('reuse supplied records')):
            _,ids=attention_context(self.root,metric,records=before+[unrelated,foreign])
        self.assertNotIn('unrelated',ids);self.assertNotIn('foreign',ids)

    def test_result_actor_summary_is_unknown_for_mixed_or_unverified_routines(self):
        raw={'recipe':{'runner_contract':'python-routines'},'routine_evidence':[{'status':'success','required_permission':'login','actor':{'username':'user','effective_uid':1000,'mode':'user'}}]}
        self.assertEqual(reports.collection_user(raw),'user')
        rows=raw['routine_evidence'];root={'status':'success','required_permission':'root','actor':{'username':'root','effective_uid':0,'mode':'root'}}
        rows.append(root);self.assertIsNone(reports.collection_user(raw))
        rows.pop();rows[0]['actor']['effective_uid']=True;self.assertIsNone(reports.collection_user(raw))
        rows[0]['actor']['effective_uid']=1000;rows[0]['required_permission']='root';self.assertIsNone(reports.collection_user(raw))
        rows[0]['required_permission']='login';rows[0]['status']='failed';self.assertIsNone(reports.collection_user(raw))

    def test_execution_report_does_not_follow_child_paths_and_rejects_malformed_children(self):
        source=self.root/'selected-meal.json'
        raw={'recipe':{'id':'recipe-meal','reference':OVERVIEW},'host_id':'node','status':'partial','children':[{'recipe':{'reference':SYSTEM},'status':'failed','result_path':'/never-read/<script>source</script>','retention':{'status':'failed'}}]}
        source.write_text(json.dumps(raw));before=source.read_bytes()
        item=choose(self.root,'feast/report/execution-summary')
        report,path=reports.run_report(self.root,item,[source])
        self.assertEqual(report['status'],'success',report)
        html=(path.parent/'artifacts/summary.html').read_text()
        self.assertNotIn('<script>source</script>',html)
        self.assertIn('&lt;script&gt;source&lt;/script&gt;',html)
        self.assertIn('failed',html)
        self.assertEqual(source.read_bytes(),before)
        raw['children']=[{'recipe':'not a mapping'}];source.write_text(json.dumps(raw))
        report,_=reports.run_report(self.root,item,[source])
        self.assertEqual(report['reason_code'],'unsupported_input')
        self.assertEqual(report['artifacts'],[])
